from abc import abstractmethod
from functools import cached_property
from asyncio import Queue, get_event_loop, ensure_future, Task
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

    async def handle_subscribe(
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
        client_set = self.subscriptions << topic.node_list
        client_set[client.id] = qos
        return True

    def handle_unsubscribe(self, client: Client, topic_str: str):
        topic = Topic.from_str(topic_str)
        client_set = self.subscriptions << topic.node_list
        client_set.pop(client.id)
        if not client_set:
            self.subscriptions.cascade_delete(topic.node_list)
        return True

    @abstractmethod
    def retain_rows(self, rows: list):
        pass

    @abstractmethod
    async def load_tree(self) -> RecursiveDefaultDict:
        pass

    async def handle_publish(self, message: IncomingMessage):
        if message.retain:
            if message.tree:
                if message.update:
                    rows = message.flatten_into_rows()
                else:
                    # create objects
                    rows = NotImplemented
                    raise rows
            else:
                rows = message.get_applicable_rows(self.tree)
            self.retain_rows(rows)
        else:
            rows = [message.as_single_row()]
        await self.broadcast_queue.put(rows)

    async def main_loop(self):
        self.tree = await self.load_tree()
        while True:
            rows = await self.broadcast_queue.get()
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

    def add_client(self, client: Client):
        self.clients[client.id] = client

    def remove_client(self, client: Client):
        self.clients.pop(client.id)

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
            await self.main_loop()
        except:
            log.traceback()
            raise

    async def shutdown(self):
        self.main_task.cancel()

    @cached_property
    def event_loop(self):
        return get_event_loop()

    @cached_property
    def broadcast_queue(self) -> Queue:
        return Queue(loop=self.event_loop)

    @classmethod
    def start(cls, *args, **kwargs):
        # noinspection PyArgumentList
        broker = cls(*args, **kwargs)
        broker.run()
