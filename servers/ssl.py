import dataclasses
from socket import SHUT_RDWR, IPPROTO_TCP, TCP_NODELAY
from functools import cached_property
from ssl import SSLContext, SSLSocket

from logger import log
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
                # self.base_socket,
                # server_side=True,
                # do_handshake_on_connect=True,
            # )
        return self.base_socket


    # def handle_client(self, sock: SSLSocket):
    #     log.debug("CLIENT", sock)
    #     sock.setsockopt(IPPROTO_TCP, TCP_NODELAY, True)
    #     sock.settimeout(1000)
    #     sock.do_handshake()
    #     # sock.settimeout(None)
    #     super().handle_client(sock)

    def stop(self):
        self.alive = False
        while self.clients:
            self.clients.pop().disconnect()
        stop_socket(self.host, 443)
        try:
            self.server.shutdown(SHUT_RDWR)
        except OSError as e:
            if e.errno not in [9, 57, 107]:
                raise
        self.server.close()
