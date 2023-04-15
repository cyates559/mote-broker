import websockets

from brokers.broker import Broker
from servers.server import Server
from handlers.websocket_handler import WebsocketHandler


class WebsocketServer(Server):
    async def start_instance(self):
        return await websockets.serve(
            ws_handler=self.create_handler,
            host=self.host,
            port=self.port,
            ssl=self.ssl_context,
            loop=Broker.instance.event_loop,
            subprotocols=["mqtt"],
        )

    @staticmethod
    async def create_handler(protocol):
        await WebsocketHandler.new_connection(protocol)
