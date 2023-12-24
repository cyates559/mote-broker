import dataclasses

from servers.socket import SocketServer
from servers.websocket.handler import WebsocketHandler


@dataclasses.dataclass
class WebsocketServer(SocketServer):
    handler_class = WebsocketHandler
