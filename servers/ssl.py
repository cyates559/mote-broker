import dataclasses
import ssl
from socket import SHUT_RDWR, IPPROTO_TCP, TCP_NODELAY
from functools import cached_property
from ssl import SSLContext, SSLSocket
from threading import Thread

from broker.context import BrokerContext
from logger import log
from servers.socket import SocketServer
from servers.websocket.handler import WebsocketHandler
from utils.stop_socket import stop_socket


class SecureWebsocketHandler(WebsocketHandler):
    sock: SSLSocket

    def handshake(self):
        log.debug("CLIENT", self.sock)
        self.sock.setsockopt(IPPROTO_TCP, TCP_NODELAY, True)
        self.sock.settimeout(5)
        self.sock.do_handshake()
        super().start_threads()

    def start_threads(self):
        Thread(target=self.handshake, daemon=True).start()

@dataclasses.dataclass
class SecureSocketServer(SocketServer):
    ssl_context: SSLContext = None
    handler_class = SecureWebsocketHandler

    @cached_property
    def base_socket(self):
        return super().server

    @cached_property
    def server(self):
        if self.ssl_context:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(BrokerContext.instance.ssl_cert, keyfile=BrokerContext.instance.ssl_key)
            return ctx.wrap_socket(
                self.base_socket,
                server_side=True,
                do_handshake_on_connect=False,
            )
        return self.base_socket

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
