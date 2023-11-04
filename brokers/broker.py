import dataclasses
from collections import deque
from functools import cached_property, partial
from asyncio import (
    Queue,
    get_event_loop,
    ensure_future,
    CancelledError,
    Lock,
    wait,
)

from asgiref.sync import sync_to_async

from brokers.context import BrokerContext
from models.client import Client
from logger import log
from models.messages import IncomingMessage, OutgoingMessage
from models.topic import Topic
from persistence.manager import PersistenceManager
from protocols.create_messages_for_subscriptions import (
    create_messages_for_subscriptions,
)
from protocols.filter_tree import filter_tree_with_topic
from servers.mqtt_server import MQTTServer
from servers.websocket_server import WebsocketServer
from utils.stdout_log import print_in_yellow, print_in_green, print_in_red


@dataclasses.dataclass
class Broker(BrokerContext):
    host: str = "0.0.0.0"
    mqtt_host: str = None
    ws_host: str = None
    mqtt_port: int = 1993
    ws_port: int = 53535
    log_info: callable = print
    log_debug: callable = partial(print_in_green, "[DEBUG]")
    log_warn: callable = partial(print_in_yellow, "[WARN]")
    log_error: callable = partial(print_in_red, "[ERROR]")

    @cached_property
    def ssl_context(self):
        return None

    @cached_property
    def persistence_manager(self):
        return PersistenceManager()

    @staticmethod
    async def load_tree():
        return await sync_to_async(
            PersistenceManager.load_tree,
        )()

    @cached_property
    def ws_server(self):
        return WebsocketServer(
            host=self.ws_host or self.host,
            port=self.ws_port,
            ssl_context=self.ssl_context,
        )

    @cached_property
    def mqtt_server(self):
        return MQTTServer(
            host=self.mqtt_host or self.host,
            port=self.mqtt_port,
            ssl_context=self.ssl_context,
        )

    async def create_context(self, main: callable):
        with self.persistence_manager:
            async with self.ws_server, self.mqtt_server:
                await main()

    def retain_rows(self, rows: list):
        self.persistence_manager.retain(*rows)
        for topic_nodes, data, _ in rows:
            branch = self.tree / topic_nodes
            if branch is not None:
                branch.leaf = data

    async def add_client(self, client: Client):
        prev_client = self.clients.get(client.id)
        if prev_client:
            await prev_client.override_connection()
        self.clients[client.id] = client

    def remove_client(self, client: Client):
        self.clients.pop(client.id)

    async def shutdown(self):
        self.main_task.cancel()

    @cached_property
    def event_loop(self):
        return get_event_loop()

    @cached_property
    def broadcast_queue(self) -> Queue:
        return Queue(loop=self.event_loop)

    @cached_property
    def subscription_lock(self) -> Lock:
        return Lock(loop=self.event_loop)

    @cached_property
    def futures(self) -> deque:
        return deque()

    @classmethod
    def start(cls, *args, **kwargs):
        # noinspection PyArgumentList
        broker = cls(*args, **kwargs)
        broker.run()

    def run(self):
        try:
            self.start_main_task()
            self.event_loop.run_forever()
        except (KeyboardInterrupt, InterruptedError):
            log.info(end="\r")
            log.info("Interrupted!")
            self.event_loop.run_until_complete(self.shutdown())

    def start_main_task(self):
        self.main_task = ensure_future(
            self.run_main_loop(),
            loop=self.event_loop,
        )
        return self.main_task

    async def run_main_loop(self):
        try:
            log.info("Loading message tree...", end="")
            self.tree = await self.load_tree()
            log.info("Done")
            await self.create_context(self.main_loop)
        except CancelledError:
            raise
        except:
            log.traceback()
            raise

    async def main_loop(self):
        while self.running:
            try:
                await self.run_tasks()
                rows = await self.broadcast_queue.get()
                if rows:
                    async with self.subscription_lock:
                        future = ensure_future(
                            self.process_rows(rows),
                            loop=self.event_loop,
                        )
                        self.futures.append(future)
            except CancelledError:
                if self.futures:
                    await wait(self.futures, loop=self.event_loop)
                raise
            except Exception:
                if self.running:
                    log.traceback()

    async def run_tasks(self):
        while self.futures and self.futures[0].done():
            future = self.futures.popleft()
            try:
                future.result()
            except CancelledError:
                raise
            except:
                log.traceback()

    async def process_rows(self, rows: list):
        messages = create_messages_for_subscriptions(
            self.subscriptions,
            rows,
        )
        for client_list, topic_nodes, data in messages:
            topic = str(Topic.from_nodes(topic_nodes))
            for client_id, qos in client_list.items():
                client = self.clients.get(client_id)
                if client is None:
                    continue
                message = OutgoingMessage(
                    topic=topic,
                    qos=qos,
                    data=data,
                )
                await client.handle_message(message)

    async def publish(self, message: IncomingMessage):
        if message.retain:
            if message.tree:
                rows = message.flatten_into_rows(self.tree)
            else:
                rows = message.get_applicable_rows(self.tree)
            self.retain_rows(rows)
        else:
            rows = [message.as_single_row()]
        await self.broadcast_queue.put(rows)

    async def subscribe(self, client: Client, topic_str: str, qos: int, sync: bool):
        topic = Topic.from_str(topic_str)
        if sync:
            tree_item = filter_tree_with_topic(
                topic=topic.node_list,
                tree=self.tree,
            )
            message = OutgoingMessage.from_tree_item(
                topic=topic_str,
                qos=qos,
                tree_item=tree_item,
            )
            await client.handle_message(message)

        await self.subscription_lock.acquire()
        try:
            client_set = self.subscriptions << topic.node_list
            client_set[client.id] = qos
        finally:
            self.subscription_lock.release()
        return True

    async def unsubscribe(self, client: Client, *topics: str):
        async with self.subscription_lock:
            for topic_str in topics:
                topic = Topic.from_str(topic_str)
                client_set = self.subscriptions << topic.node_list
                got_id = client_set.pop(client.id, False)
                if not got_id:
                    log.warn(f"Subscription {topic_str} not found for {client}")
                if not client_set:
                    self.subscriptions.cascade_delete(topic.node_list)
        return True
