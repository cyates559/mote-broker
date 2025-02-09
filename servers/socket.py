import dataclasses
from functools import cached_property
from socket import socket, AF_INET, SOCK_STREAM, SHUT_RDWR, SOL_SOCKET, SO_REUSEADDR
from ssl import SSLError
from threading import Lock
from typing import Type

from logger import log
from servers.handler import Handler
from servers.server import Server
from utils.stop_socket import stop_socket


@dataclasses.dataclass
class SocketHandler(Handler):
    sock: socket

    @cached_property
    def outgoing_lock(self):
        return Lock()

    def write(self, data):
        try:
            with self.outgoing_lock:
                self.send_bytes(data)
        except (OSError, BrokenPipeError, ConnectionResetError):
            raise ConnectionError

    def send_bytes(self, data: bytes):
        self.sock.send(data)

    def read(self, size):
        try:
            cached_bytes = bytearray()
            byte_count = 0
            while byte_count < size:
                buf = self.sock.recv(size)
                if not buf:
                    raise ConnectionError
                cached_bytes.extend(buf)
                byte_count += len(buf)
            return bytes(cached_bytes)
        except OSError:
            raise ConnectionError from OSError

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
        try:
            self.sock.shutdown(SHUT_RDWR)
        except OSError as e:
            if e.errno not in [9, 107]:
                raise
        self.sock.close()


@dataclasses.dataclass
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
        try:
            self.server.shutdown(SHUT_RDWR)
        except OSError as e:
            if e.errno not in [9, 57, 107]:
                raise
        self.server.close()

    @cached_property
    def clients(self):
        return []

    def handle_client(self, client_socket: socket):
        client = self.handler_class.new_connection(client_socket)
        self.clients.append(client)

    def loop(self):
        self.alive = True
        self.server.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        try:
            self.server.bind((self.host, self.port))
        except OSError:
            log.error("Unable to bind", self.host, self.port)
            log.traceback()
            return
        self.server.listen()
        while self.alive:
            try:
                client_socket, address = self.server.accept()
            except:
                if not self.alive:
                    break
                else:
                    log.traceback()
                    continue
            if not self.alive:
                break
            self.handle_client(client_socket)
