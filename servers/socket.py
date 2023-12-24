import dataclasses
from functools import cached_property
from socket import socket, AF_INET, SOCK_STREAM
from threading import Thread
from typing import Type

from logger import log
from servers.handler import Handler
from servers.server import Server
from utils.stop_socket import stop_socket


@dataclasses.dataclass
class SocketHandler(Handler):
    sock: socket

    def write(self, data):
        self.sock.send(data)

    def read(self, size):
        return self.sock.recv(size)

    def get_host_port_tuple(self):
        return self.sock.getsockname()

    def set_keep_alive(self, seconds):
        self.sock.settimeout(seconds)

    def close(self):
        # if self.alive:
        #     try:
        #         self.send_close()
        #     except:
        #         pass
        self.alive = False
        self.sock.close()


class SocketServer(Server):
    handler_class: Type[Handler] = SocketHandler

    @cached_property
    def server(self):
        return socket(AF_INET, SOCK_STREAM)

    def stop(self):
        self.alive = False
        while self.clients:
            self.clients.pop().disconnect()
        stop_socket(self.host, self.port)
        self.server.close()

    @cached_property
    def clients(self):
        return []

    def handle_client(self, client_socket: socket):
        client = self.handler_class.new_connection(client_socket)
        self.clients.append(client)

    def loop(self):
        self.alive = True
        self.server.bind((self.host, self.port))
        self.server.listen()
        while self.alive:
            client_socket, address = self.server.accept()
            if not self.alive:
                break
            log.info(f"{self.name} New Connection: {client_socket.getsockname()}")
            Thread(target=self.handle_client, args=[client_socket]).start()
