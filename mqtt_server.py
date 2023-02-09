import asyncio
from asyncio import StreamReader, StreamWriter

from mqtt_handler import MQTTHandler
from server import Server


class MQTTServer(Server):
    async def start_instance(self):
        return await asyncio.start_server(
            client_connected_cb=self.create_handler,
            host=self.host,
            port=self.port,
            reuse_address=True,
            reuse_port=True,
            ssl=self.ssl_context,
            loop=self.event_loop,
        )

    @staticmethod
    def create_handler(reader: StreamReader, writer: StreamWriter):
        MQTTHandler(reader, writer)

    async def close(self):
        self.instance.close()
        await self.instance.wait_closed()
