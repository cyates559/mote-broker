import asyncio
import dataclasses
from asyncio import StreamReader, StreamWriter, Queue, CancelledError, ensure_future, Task
from functools import cached_property

from mqtt_handler import MQTTHandler
from mqtt_server import MQTTServer
from persistence.manager import PersistenceManager
from websocket_handler import WebsocketHandler
from websocket_server import WebsocketServer


@dataclasses.dataclass
class MoteBroker:
    host: str = "0.0.0.0"
    mqtt_host: str = None
    ws_host: str = None
    mqtt_port: int = 1993
    ws_port: int = 53535
    broadcast_task: Task = None

    @cached_property
    def ssl_context(self):
        return None

    @cached_property
    def persistence_manager(self):
        return PersistenceManager()

    @cached_property
    def event_loop(self):
        return asyncio.get_event_loop()

    @cached_property
    def broadcast_queue(self):
        return Queue(loop=self.event_loop)

    @staticmethod
    async def mqtt_handler(reader: StreamReader, writer: StreamWriter):
        return MQTTHandler(reader, writer)

    @staticmethod
    async def ws_handler(websocket, uri):
        return WebsocketHandler(websocket, uri)

    @cached_property
    def ws_server(self):
        return WebsocketServer(
            host=self.ws_host or self.host,
            port=self.ws_port,
            ssl_context=self.ssl_context,
            event_loop=self.event_loop,
        )

    @cached_property
    def mqtt_server(self):
        return MQTTServer(
            host=self.mqtt_host or self.host,
            port=self.mqtt_port,
            ssl_context=self.ssl_context,
            event_loop=self.event_loop,
        )

    @staticmethod
    def start(*args, **kwargs):
        broker = MoteBroker(*args, **kwargs)
        broker.run()

    def run(self):
        try:
            self.event_loop.run_until_complete(self.arun())
            self.event_loop.run_forever()
        except (KeyboardInterrupt, InterruptedError):
            print(end="\r")
            print("INTERRUPTED")
            self.event_loop.run_until_complete(self.shutdown())

    async def arun(self):
        try:
            self.broadcast_task = ensure_future(
                self.broadcast_loop(),
                loop=self.event_loop,
            )
        except CancelledError:
            pass

    async def shutdown(self):
        self.broadcast_task.cancel()

    async def broadcast_loop(self):
        with self.persistence_manager:
            async with self.ws_server, self.mqtt_server:
                await self.broadcast_queue.get()
