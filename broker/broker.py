import dataclasses
import ssl
from queue import Queue
from functools import cached_property
from threading import Lock

from logger import log
from servers.ssl import SecureSocketServer
from tables.manager import TableManager
from tree.manager import TreeManager
from protocols.create_messages_for_subscriptions import create_messages_for_subscriptions
from broker.context import BrokerContext
from models.client import Client
from models.messages import IncomingMessage, OutgoingMessage
from models.topic import Topic
from servers.socket import SocketServer
from servers.websocket.handler import WebsocketHandler
from utils.field import default_factory


@dataclasses.dataclass
class Broker(BrokerContext):
    host: str = "0.0.0.0"
    tcp_host: str = None
    ws_host: str = None
    tcp_port: int = 1993
    ws_port: int = 53535
    ssl_cert: str = None
    ssl_key: str = None

    tree_manager: TreeManager = default_factory(TreeManager.setup)
    table_manager: TableManager = default_factory(TableManager.setup)
    subscription_lock: Lock = default_factory(Lock)
    broadcast_queue: Queue = default_factory(Queue)

    @cached_property
    def websocket_server(self):
        return SecureSocketServer(
            name="WebSocket Server",
            host=self.ws_host or self.host,
            port=self.ws_port,
            handler_class=WebsocketHandler,
            ssl_context=self.ssl_context,
        )

    @cached_property
    def tcp_server(self):
        return SocketServer(
            name="TCP Server",
            host=self.tcp_host or self.host,
            port=self.tcp_port,
        )

    @cached_property
    def ssl_context(self):
        if not (self.ssl_cert and self.ssl_key):
            return None
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(self.ssl_cert, keyfile=self.ssl_key)
        return ssl_context

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
        with self.tree_manager, self.tcp_server, self.websocket_server: #table_manager
            while self.running:
                rows = self.broadcast_queue.get(block=True)
                if rows:
                    with self.subscription_lock:
                        try:
                            self.process_outgoing_rows(rows)
                        except:
                            log.traceback()

    def add_client(self, client: Client):
        prev_client = self.clients.get(client.id)
        if prev_client:
            prev_client.override_connection()
        self.clients[client.id] = client

    def remove_client(self, client: Client):
        if client.id:
            try:
                self.clients.pop(client.id)
            except KeyError:
                log.warn(f"Client {client} is not in client list")

    def process_outgoing_rows(self, rows: list):
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
        if message.table:
            self.table_manager.add_tasks((message.topic, message.data, message.qos))
        else:
            if message.retain:
                rows = self.tree_manager.process_message(message)
            else:
                rows = [message.as_single_row()]
            self.broadcast_queue.put(rows)

    def subscribe(self, client: Client, topic_str: str, qos: int, tree: bool):
        topic = Topic.from_str(topic_str)
        if tree:
            message = self.tree_manager.get_message(topic, qos=qos)
            client.queue_message(message)
        elif topic.for_table:
            message = self.table_manager.get_message(topic, qos=qos)
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
