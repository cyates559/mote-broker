import dataclasses
from abc import abstractmethod
from functools import cached_property
from threading import Condition, Thread
from typing import Type, Union

from broker.context import BrokerContext as Broker
from logger import log
from models.client import Client
from models.constants import TOPIC_SEP
from models.messages import IncomingMessage, OutgoingMessage
from exceptions.unexpected_packet import UnexpectedPacketType
from servers.streams import ReaderWriter
from packet.base_packet import PacketWithId
from packet.packets import infer_packet_class
from packet.connack import ConnectAcknowledgePacket
from packet.connect import ConnectPacket
from packet.pingreq import PingRequestPacket
from packet.pingresp import PingResponsePacket
from packet.publish import PublishPacket
from packet.puback import PublishAcknowledgePacket
from packet.pubcomp import PublishCompletePacket
from packet.pubrec import PublishReceivedPacket
from packet.pubrel import PublishReleasedPacket
from packet.suback import SubscribeAcknowledgePacket
from packet.subscribe import SubscribePacket
from packet.unsub import UnsubscribePacket
from packet.unsuback import UnsubscribeAcknowledgePacket
from utils.field import default_factory


class TooManyPacketIds(Exception):
    pass


@dataclasses.dataclass
class PacketCondition:
    type_code: int
    id: int
    result: PacketWithId = None
    condition: Condition = default_factory(Condition)

    @cached_property
    def hash(self):
        return hash((self.type_code, self.id))

    def __hash__(self):
        return self.hash

    def meet(self, packet: PacketWithId):
        with self.condition:
            self.result = packet
            self.condition.notifyAll()

    def wait(self, **kwargs) -> PacketWithId:
        with self.condition:
            while self.result is None:
                self.condition.wait(**kwargs)
            # noinspection PyTypeChecker
            return self.result


class Handler(Client, ReaderWriter):
    last_will: IncomingMessage
    alive: bool = True
    linked: bool = False
    connection_override: bool = False

    @cached_property
    def packet_conditions(self):
        return set()

    @cached_property
    def used_ids(self):
        return set()

    @cached_property
    def host(self):
        return self.host_port_tuple[0]

    @cached_property
    def port(self):
        return self.host_port_tuple[1]

    @cached_property
    def host_port_tuple(self):
        return self.get_host_port_tuple()

    @cached_property
    def packet_map(self):
        return {
            PingRequestPacket: self.handle_ping_request,
            SubscribePacket: self.handle_subscribe,
            UnsubscribePacket: self.handle_unsubscribe,
            PublishPacket: self.handle_publish,
        }

    @cached_property
    def publish_map(self):
        return [
            self.publish,
            self.handle_publish_qos_1,
            self.handle_publish_qos_2,
        ]

    @property
    def next_packet_id(self):
        i = 0
        while i in self.used_ids:
            i += 1
            if i == 65535:
                raise TooManyPacketIds
        return i

    def flush(self):
        pass

    @abstractmethod
    def get_host_port_tuple(self) -> (str, int):
        pass

    @abstractmethod
    def close(self):
        pass

    @classmethod
    def new_connection(cls, *args, **kwargs):
        # noinspection PyArgumentList
        handler = cls(*args, **kwargs)
        handler.id = None
        handler.last_will = None
        handler.start_threads()
        return handler

    @staticmethod
    def infer_packet_class(msg_type):
        """
        To avoid a circular import from class Packet
        """
        return infer_packet_class(msg_type)

    def send_message(self, message: OutgoingMessage):
        """
        Mote has no reason to downgrade qos
        """
        if message.qos == 0:
            PublishPacket(
                flags={"qos": message.qos, "retain": False},
                topic=message.topic,
                data=message.data,
            ).write(self)
        else:
            packet_id = self.next_packet_id
            self.used_ids.add(packet_id)
            try:
                if message.qos == 0:
                    condition = False
                elif message.qos == 1:
                    condition = self.create_packet_condition(PublishAcknowledgePacket, packet_id)
                else:
                    condition = self.create_packet_condition(PublishReceivedPacket, packet_id)
                publish = PublishPacket(
                    flags={"qos": message.qos, "retain": False},
                    topic=message.topic,
                    data=message.data,
                    id=packet_id,
                )
                publish.write(self)
                if not condition:
                    return
                self.wait_for_packet(condition)
                if message.qos == 2:
                    release = PublishReleasedPacket(id=packet_id)
                    condition = self.create_packet_condition(PublishCompletePacket, packet_id)
                    release.write(self)
                    self.wait_for_packet(condition)
            finally:
                self.used_ids.remove(packet_id)

    def create_packet_condition(self, packet_class: Type[PacketWithId], packet_id: int):
        packet_condition = PacketCondition(
            type_code=packet_class.type_code,
            id=packet_id,
        )
        if packet_condition in self.packet_conditions:
            raise KeyError(
                f"Already waiting for this packet {packet_class} {packet_id}"
            )
        self.packet_conditions.add(packet_condition)
        return packet_condition

    def wait_for_packet(self, packet_condition: PacketCondition) -> PacketWithId:
        try:
            result = packet_condition.wait()
        finally:
            self.packet_conditions.remove(packet_condition)
        return result

    def packet_notify(self, packet: PacketWithId) -> bool:
        for packet_condition in self.packet_conditions:
            if (
                packet_condition.type_code == packet.type_code
                and packet_condition.id == packet.id
            ):
                packet_condition.meet(packet)
                return True
        return False

    def disconnect(self):
        self.linked = False
        self.close()
        self.handle_disconnected()

    def override_connection(self):
        self.connection_override = True
        self.disconnect()

    @staticmethod
    def get_last_will(packet: ConnectPacket):
        if packet.connect_flags.enable_last_will:
            return IncomingMessage.last_will(packet)
        else:
            return None

    def handle_ping_request(self, _: PingRequestPacket):
        PingResponsePacket().write(self)

    @staticmethod
    def publish(packet: PublishPacket):
        message = IncomingMessage.from_packet(packet)
        Broker.instance.publish(message)

    def handle_publish_qos_1(self, packet: PublishPacket):
        acknowledge = PublishAcknowledgePacket(id=packet.id)
        self.publish(packet)
        acknowledge.write(self)

    def handle_publish_qos_2(self, packet: PublishPacket):
        received = PublishReceivedPacket(id=packet.id)
        condition = self.create_packet_condition(PublishReleasedPacket, packet.id)
        received.write(self)
        self.wait_for_packet(condition)
        self.publish(packet)
        complete = PublishCompletePacket(id=packet.id)
        complete.write(self)

    def handle_publish(self, packet: PublishPacket):
        return self.publish_map[packet.flags.qos](packet)

    def using_packet_id(self, func, packet: PacketWithId):
        self.used_ids.add(packet.id)
        try:
            return func(packet)
        finally:
            self.used_ids.remove(packet.id)

    def handle_subscribe(self, packet: SubscribePacket):
        response_codes = []
        for request in packet.requests:
            if request.topic[0] == TOPIC_SEP:
                tree = True
                topic_str = request.topic[1:]
            else:
                tree = False
                topic_str = request.topic
            if Broker.instance.subscribe(
                client=self,
                topic_str=topic_str,
                qos=request.qos,
                tree=tree,
            ):
                response_codes.append(request.qos)
                self.subscriptions.add(topic_str)
            else:
                response_codes.append(0x80)
        response = SubscribeAcknowledgePacket(
            id=packet.id,
            response_codes=response_codes,
        )
        response.write(self)

    def handle_unsubscribe(self, packet: UnsubscribePacket):
        for topic in packet.topics:
            if Broker.instance.unsubscribe(self, topic):
                try:
                    self.subscriptions.remove(topic)
                except KeyError:
                    pass
                response = UnsubscribeAcknowledgePacket(id=packet.id)
                response.write(self)

    def handle_disconnected(self):
        Broker.instance.unsubscribe(self, *self.subscriptions)
        if self.connection_override:
            return
        Broker.instance.remove_client(self)
        if self.last_will is not None:
            Broker.instance.publish(self.last_will)

    def handle_packet(self, packet):
        handler = self.packet_map.get(packet.__class__)
        if handler:
            Thread(target=handler, args=[packet], daemon=True).start()
        elif isinstance(packet, PacketWithId) and self.packet_notify(packet):
            return
        else:
            raise UnexpectedPacketType(packet)

    def start_connection(self):
        pass

    def write_loop(self):
        try:
            while self.alive:
                message = self.message_queue.get(block=True)
                self.send_message(message)
        except ConnectionError:
            self.close()
            if self.linked:
                self.handle_disconnected()

    def read_loop(self):
        try:
            self.start_connection()
            connect_packet = ConnectPacket.read(self)
            self.id = connect_packet.client_id
            acknowledge_packet = ConnectAcknowledgePacket(
                session_parent=0,
                return_code=ConnectAcknowledgePacket.ReturnCode.ACCEPTED,
            )
            self.last_will = self.get_last_will(connect_packet)
            acknowledge_packet.write(self)
            Broker.instance.add_client(self)
            self.linked = True
            self.set_keep_alive(connect_packet.keep_alive + 1)
            while self.alive:
                packet = self.read_next_packet()
                self.handle_packet(packet)
        except: #(ConnectionError, UnexpectedPacketType) as x:
            ## if not isinstance(x, ConnectionError):
            log.traceback()
            ##
            self.close()
            if self.linked:
                self.handle_disconnected()

    @abstractmethod
    def set_keep_alive(self, keep_alive: int):
        pass

    def read_next_packet(self):
        msg_type, flags = self.decode_header()
        clazz = self.infer_packet_class(msg_type)
        packet = clazz.read(self, flags)
        return packet
