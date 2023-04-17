from abc import abstractmethod
from functools import cached_property
from asyncio import Queue, get_event_loop, ensure_future, Task, CancelledError, Lock
from typing import Any

from models.client import Client
from logger import log
from models.messages import IncomingMessage, OutgoingMessage
from models.topic import Topic
from protocols.create_messages_for_subscriptions import create_messages_for_subscriptions
from protocols.filter_tree import filter_tree_with_topic
from utils.recursive_default_dict import RecursiveDefaultDict


class Broker:
    instance: Any
    tree: RecursiveDefaultDict
    log: callable
    log_error: callable
    main_task: Task

    def __new__(cls, *args, **kwargs):
        self = Broker.instance = super().__new__(cls, *args, **kwargs)
        self.main_task = None
        self.subscriptions = RecursiveDefaultDict(default_type=dict)
        self.clients = {}
        return self

    @abstractmethod
    def retain_rows(self, rows: list):
        pass

    @abstractmethod
    async def load_tree(self) -> RecursiveDefaultDict:
        pass

    def add_client(self, client: Client):
        self.clients[client.id] = client

    def remove_client(self, client: Client):
        self.clients.pop(client.id)

    @abstractmethod
    async def create_context(self, main: callable):
        pass

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

    @classmethod
    def start(cls, *args, **kwargs):
        # noinspection PyArgumentList
        broker = cls(*args, **kwargs)
        broker.run()

    def run(self):
        try:
            self.main_task = ensure_future(
                self.main(),
                loop=self.event_loop,
            )
            self.event_loop.run_forever()
        except (KeyboardInterrupt, InterruptedError):
            log.info(end="\r")
            log.info("Interrupted!")
            self.event_loop.run_until_complete(self.shutdown())

    async def main(self):
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
        while True:
            rows = await self.broadcast_queue.get()
            if rows:
                await self.subscription_lock.acquire()
                try:
                    await self.process_rows(rows)
                finally:
                    self.subscription_lock.release()

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

    async def subscribe(
        self, client: Client, topic_str: str, qos: int, sync: bool
    ):
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
        await self.subscription_lock.acquire()
        try:
            for topic_str in topics:
                topic = Topic.from_str(topic_str)
                client_set = self.subscriptions << topic.node_list
                got_id = client_set.pop(client.id, False)
                if not got_id:
                    log.error(f"Subscription {topic_str} not found for {client}")
                if not client_set:
                    self.subscriptions.cascade_delete(topic.node_list)
        finally:
            self.subscription_lock.release()
        return True