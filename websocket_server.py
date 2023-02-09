import websockets

from server import Server
from websocket_handler import WebsocketHandler


class WebsocketServer(Server):
    async def start_instance(self):
        return await websockets.serve(
            ws_handler=WebsocketHandler,
            host=self.host,
            port=self.port,
            ssl=self.ssl_context,
            loop=self.event_loop,
            subprotocols=["mqtt"],
        )
