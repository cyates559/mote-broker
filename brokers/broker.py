import dataclasses
from queue import Queue
from functools import partial, cached_property
from threading import Lock

from logger import log
from persistence.manager import PersistenceManager
from protocols.create_messages_for_subscriptions import create_messages_for_subscriptions
from protocols.filter_tree import filter_tree_with_topic
from brokers.context import BrokerContext
from models.client import Client
from models.messages import IncomingMessage, OutgoingMessage
from models.topic import Topic
from servers.socket import SocketServer
from servers.websocket.handler import WebsocketHandler
from utils.field import default_factory
from utils.recursive_default_dict import RecursiveDefaultDict
from utils.stdout_log import print_in_yellow, print_in_green, print_in_red, print_in_magenta


@dataclasses.dataclass
class Broker(BrokerContext):
    host: str = "0.0.0.0"
    tcp_host: str = None
    ws_host: str = None
    tcp_port: int = 1993
    ws_port: int = 53535

    log_info: callable = print_in_green
    log_debug: callable = partial(print_in_magenta, "[DEBUG]")
    log_warn: callable = partial(print_in_yellow, "[WARN]")
    log_error: callable = partial(print_in_red, "[ERROR]")

    persistence_manager: PersistenceManager = default_factory(PersistenceManager)
    subscription_lock: Lock = default_factory(Lock)
    broadcast_queue: Queue = default_factory(Queue)
    tree: RecursiveDefaultDict = None

    @cached_property
    def websocket_server(self):
        return SocketServer(
            name="WebSocket Server",
            host=self.ws_host or self.host,
            port=self.ws_port,
            handler_class=WebsocketHandler,
        )

    @cached_property
    def tcp_server(self):
        return SocketServer(
            name="TCP Server",
            host=self.tcp_host or self.host,
            port=self.tcp_port,
        )

    @classmethod
    def start(cls, *args, **kwargs):
        try:
            # noinspection PyArgumentList
            broker = cls(*args, **kwargs)
            broker.main_loop()
        except (KeyboardInterrupt, InterruptedError):
            log.info(end="\r")
            log.info("Interrupted!")

    def main_loop(self):
        log.info("Loading message tree...", end="")
        self.tree = PersistenceManager.load_tree()
        log.info("Done")
        with self.persistence_manager, self.tcp_server, self.websocket_server:
            while self.running:
                rows = self.broadcast_queue.get(block=True)
                if rows:
                    with self.subscription_lock:
                        with log.dont_fail():
                            self.process_rows(rows)

    def add_client(self, client: Client):
        prev_client = self.clients.get(client.id)
        if prev_client:
            prev_client.override_connection()
        self.clients[client.id] = client

    def remove_client(self, client: Client):
        if client.id:
            self.clients.pop(client.id)

    def process_rows(self, rows: list):
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
                client.queue_message(message)

    def publish(self, message: IncomingMessage):
        if message.retain:
            if message.tree:
                rows = message.flatten_into_rows(self.tree)
            else:
                rows = message.get_applicable_rows(self.tree)
            self.retain_rows(rows)
        else:
            rows = [message.as_single_row()]
        self.broadcast_queue.put(rows)

    def subscribe(self, client: Client, topic_str: str, qos: int, sync: bool):
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
            client.queue_message(message)

        with self.subscription_lock:
            client_set = self.subscriptions << topic.node_list
            client_set[client.id] = qos
        return True

    def unsubscribe(self, client: Client, *topics: str):
        with self.subscription_lock:
            for topic_str in topics:
                topic = Topic.from_str(topic_str)
                client_set = self.subscriptions << topic.node_list
                got_id = client_set.pop(client.id, False)
                if not got_id:
                    log.warn(f"Subscription {topic_str} not found for {client}")
                if not client_set:
                    self.subscriptions.cascade_delete(topic.node_list)
        return True

    def retain_rows(self, rows: list):
        self.persistence_manager.retain(*rows)
        for topic_nodes, data, _ in rows:
            branch = self.tree / topic_nodes
            if branch is not None:
                branch.leaf = data
