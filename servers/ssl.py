import dataclasses
from _socket import SOCK_STREAM, SHUT_RDWR
from functools import cached_property
from socket import socket, AF_INET
from ssl import SSLContext

from servers.socket import SocketServer
from utils.stop_socket import stop_socket


@dataclasses.dataclass
class SecureSocketServer(SocketServer):
    ssl_context: SSLContext = None

    @cached_property
    def base_socket(self):
        return super().server

    @cached_property
    def server(self):
        if self.ssl_context:
            return self.ssl_context.wrap_socket(self.base_socket)
        return self.base_socket


    def stop(self):
        # self.alive = False
        # while self.clients:
        #     self.clients.pop().disconnect()
        super().stop()
        try:
            self.base_socket.shutdown(SHUT_RDWR)
        except OSError as e:
            if e.errno not in [9, 57, 107]:
                raise
        self.server.close()
        self.base_socket.close()
