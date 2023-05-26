import dataclasses
from abc import abstractmethod
from asyncio import ensure_future, Future, wait_for
from collections import deque
from functools import cached_property
from typing import Type
from asyncio.exceptions import TimeoutError as SyncTimeoutError

from models.client import Client
from models.constants import TOPIC_SEP
from exceptions.disconnected import Disconnected
from handlers.exceptions import UnexpectedPacketType
from handlers.streams import ReaderWriter
from logger import log
from packet.base_packet import PacketWithId
from packet.connack import ConnectAcknowledgePacket
from packet.connect import ConnectPacket
from packet.packets import infer_packet_class
from packet.pingreq import PingRequestPacket
from packet.pingresp import PingResponsePacket
from packet.puback import PublishAcknowledgePacket
from packet.pubcomp import PublishCompletePacket
from packet.publish import PublishPacket
from packet.pubrec import PublishReceivedPacket
from packet.pubrel import PublishReleasedPacket
from packet.suback import SubscribeAcknowledgePacket
from packet.subscribe import SubscribePacket
from brokers.broker import Broker
from models.messages import IncomingMessage, OutgoingMessage
from packet.unsub import UnsubscribePacket
from packet.unsuback import UnsubscribeAcknowledgePacket


class TooManyPacketIds(Exception):
    pass


@dataclasses.dataclass
class PacketFuture:
    type_code: int
    id: int
    result: Future

    @cached_property
    def hash(self):
        return hash((self.type_code, self.id))

    def __hash__(self):
        return self.hash


class Handler(Client, ReaderWriter):
    reader_timeout: float
    last_will: IncomingMessage
    active: bool = True

    def get_packet_id(self):
        i = 0
        while i in self.used_ids:
            i += 1
            if i == 65535:
                raise TooManyPacketIds
        return i

    async def handle_message(self, message: OutgoingMessage):
        """
        Mote has no reason to downgrade qos
        """
        if message.qos == 0:
            publish_packet = PublishPacket(
                flags={"qos": message.qos, "retain": False},
                topic=message.topic,
                data=message.data,
            )
            await publish_packet.write(self)
        else:
            packet_id = self.get_packet_id()
            self.used_ids.add(packet_id)
            try:
                publish_packet = PublishPacket(
                    flags={"qos": message.qos, "retain": False},
                    topic=message.topic,
                    data=message.data,
                    id=packet_id,
                )
                await publish_packet.write(self)
                if message.qos == 1:
                    await self.wait_for_packet(PublishAcknowledgePacket, packet_id)
                else:
                    await self.wait_for_packet(PublishReceivedPacket, packet_id)
                    release = PublishReleasedPacket(id=packet_id)
                    await release.write(self)
                    await self.wait_for_packet(PublishCompletePacket, packet_id)
            finally:
                self.used_ids.remove(packet_id)

    @cached_property
    def packet_futures(self):
        return set()

    async def wait_for_packet(
        self, packet_class: Type[PacketWithId], packet_id: int
    ) -> PacketWithId:
        packet_future = PacketFuture(
            type_code=packet_class.type_code,
            id=packet_id,
            result=Future(loop=Broker.instance.event_loop),
        )
        if packet_future in self.packet_futures:
            raise KeyError(
                f"Already waiting for this packet {packet_class} {packet_id}"
            )
        self.packet_futures.add(packet_future)
        try:
            result = await packet_future.result
        finally:
            self.packet_futures.remove(packet_future)
        return result

    def packet_notify(self, packet: PacketWithId) -> bool:
        for packet_future in self.packet_futures:
            if (
                packet_future.type_code == packet.type_code
                and packet_future.id == packet.id
            ):
                packet_future.result.set_result(packet)
                return True
        return False

    @cached_property
    def used_ids(self):
        return set()

    @cached_property
    def publish_map(self):
        return [
            self.publish,
            self.handle_publish_qos_1,
            self.handle_publish_qos_2,
        ]

    @staticmethod
    def infer_packet_class(msg_type):
        """
        To avoid a circular import from class Packet
        """
        return infer_packet_class(msg_type)

    @classmethod
    async def new_connection(cls, *args, **kwargs):
        # noinspection PyArgumentList
        handler = cls(*args, **kwargs)
        await handler.handle_connect()
        return handler

    async def handle_connect(self):
        try:
            connect_packet = await ConnectPacket.read(self)
            self.id = connect_packet.client_id
            self.reader_timeout = connect_packet.keep_alive + 1
            acknowledge_packet = ConnectAcknowledgePacket(
                session_parent=0,
                return_code=ConnectAcknowledgePacket.ReturnCode.ACCEPTED,
            )
            self.last_will = self.get_last_will(connect_packet)
            await acknowledge_packet.write(self)
            log.info(self, "connected")
            Broker.instance.add_client(self)
            await self.reader_loop()
        except SyncTimeoutError:
            log.info(f"Connection timed out for {self}")
        except Disconnected as x:
            log.info(x, "from", self)
        except:
            log.traceback()
        finally:
            await self.handle_disconnected()

    @staticmethod
    def get_last_will(packet: ConnectPacket):
        if packet.connect_flags.enable_last_will:
            return IncomingMessage.last_will(packet)
        else:
            return None

    async def handle_ping_request(self, _: PingRequestPacket):
        await PingResponsePacket().write(self)

    @staticmethod
    async def publish(packet: PublishPacket):
        message = IncomingMessage.from_packet(packet)
        await Broker.instance.publish(message)

    async def handle_publish_qos_1(self, packet: PublishPacket):
        acknowledge = PublishAcknowledgePacket(id=packet.id)
        await self.publish(packet)
        await acknowledge.write(self)

    async def handle_publish_qos_2(self, packet: PublishPacket):
        received = PublishReceivedPacket(id=packet.id)
        await received.write(self)
        await self.wait_for_packet(PublishReleasedPacket, packet.id)
        await self.publish(packet)
        complete = PublishCompletePacket(id=packet.id)
        await complete.write(self)

    async def handle_publish(self, packet: PublishPacket):
        return await self.publish_map[packet.flags.qos](packet)

    async def using_packet_id(self, func, packet: PacketWithId):
        self.used_ids.add(packet.id)
        try:
            return await func(packet)
        finally:
            self.used_ids.remove(packet.id)

    async def handle_subscribe(self, packet: SubscribePacket):
        response_codes = []
        for request in packet.requests:
            if request.topic[0] == TOPIC_SEP:
                sync = True
                topic_str = request.topic[1:]
            else:
                sync = False
                topic_str = request.topic
            if await Broker.instance.subscribe(
                client=self,
                topic_str=topic_str,
                qos=request.qos,
                sync=sync,
            ):
                response_codes.append(request.qos)
                self.subscriptions.add(topic_str)
            else:
                response_codes.append(0x80)
        response = SubscribeAcknowledgePacket(
            id=packet.id,
            response_codes=response_codes,
        )
        await response.write(self)

    async def handle_unsubscribe(self, packet: UnsubscribePacket):
        for topic in packet.topics:
            if await Broker.instance.unsubscribe(self, topic):
                try:
                    self.subscriptions.remove(topic)
                except KeyError:
                    pass
                response = UnsubscribeAcknowledgePacket(id=packet.id)
                await response.write(self)

    async def handle_disconnected(self):
        while self.tasks:
            task = await self.tasks.pop()
            if task is None or task.done():
                continue
            await task.cancel()
        await Broker.instance.unsubscribe(self, *self.subscriptions)
        Broker.instance.remove_client(self)
        if self.last_will is not None:
            await Broker.instance.publish(self.last_will)

    @cached_property
    def packet_map(self):
        return {
            PingRequestPacket: self.handle_ping_request,
            SubscribePacket: self.handle_subscribe,
            UnsubscribePacket: self.handle_unsubscribe,
            PublishPacket: self.handle_publish,
        }

    @cached_property
    def tasks(self):
        return deque()

    async def check_running_tasks(self):
        while self.tasks and self.tasks[0].done():
            await self.tasks.popleft()

    async def handle_packet(self, packet):
        handler = self.packet_map.get(packet.__class__)
        if handler:
            # noinspection PyArgumentList
            coro = handler(packet)
            task = ensure_future(coro, loop=Broker.instance.event_loop)
            self.tasks.append(task)
        elif isinstance(packet, PacketWithId) and self.packet_notify(packet):
            return
        else:
            raise UnexpectedPacketType(packet)

    async def reader_loop(self):
        while self.active:
            await self.check_running_tasks()
            packet = await wait_for(
                self.read_next_packet(),
                loop=Broker.instance.event_loop,
                timeout=self.reader_timeout,
            )
            await self.handle_packet(packet)

    async def read_next_packet(self):
        msg_type, flags = await self.decode_header()
        clazz = self.infer_packet_class(msg_type)
        packet = await clazz.read(self, flags)
        return packet

    @cached_property
    def host(self):
        return self.host_port_tuple[0]

    @cached_property
    def port(self):
        return self.host_port_tuple[1]

    @cached_property
    def host_port_tuple(self):
        return self.get_host_port_tuple()

    @abstractmethod
    def get_host_port_tuple(self) -> (str, int):
        pass

    @abstractmethod
    async def drain(self):
        pass

    @abstractmethod
    def close(self):
        pass
