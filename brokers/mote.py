import dataclasses
from functools import cached_property

from asgiref.sync import sync_to_async

from brokers.broker import Broker
from persistence.manager import PersistenceManager
from servers.mqtt_server import MQTTServer
from servers.websocket_server import WebsocketServer
from utils.stdout_log import print_in_green, print_in_yellow, print_in_red


@dataclasses.dataclass
class MoteBroker(Broker):
    host: str = "0.0.0.0"
    mqtt_host: str = None
    ws_host: str = None
    mqtt_port: int = 1993
    ws_port: int = 53535
    log_info: callable = print
    log_debug: callable = print_in_green
    log_warn: callable = print_in_yellow
    log_error: callable = print_in_red

    @cached_property
    def ssl_context(self):
        return None

    @cached_property
    def persistence_manager(self):
        return PersistenceManager()

    async def load_tree(self):
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
            branch.leaf = data
