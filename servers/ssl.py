import dataclasses
from _socket import SOCK_STREAM
from functools import cached_property
from socket import socket, AF_INET
from ssl import SSLContext

from servers.socket import SocketServer


@dataclasses.dataclass
class SecureSocketServer(SocketServer):
    ssl_context: SSLContext = None

    @cached_property
    def server(self):
        if self.ssl_context:
            return self.ssl_context.wrap_socket(socket(AF_INET, SOCK_STREAM))
        return socket(AF_INET, SOCK_STREAM)
