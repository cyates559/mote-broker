import dataclasses
import hashlib
from base64 import b64encode
from functools import cached_property
from io import BytesIO
from socket import socket
from typing import Optional

from logger import log
from servers.socket import SocketHandler
from servers.websocket.frame import (
    OP_CLOSE,
    OP_PING,
    OP_PONG,
    OP_BYTES,
    Frame,
    OP_CONTINUATION,
)
from utils.field import default_factory
from utils.recv_until import recv_until


OUT_SIZE = 2040


@dataclasses.dataclass
class WebsocketHandler(SocketHandler):
    sock: socket
    alive: bool = True
    buf: BytesIO = default_factory(BytesIO, b"")

    def get_host_port_tuple(self):
        return self.sock.getsockname()

    def send(self, *args, **kwargs):
        self.sock.send(Frame(*args, **kwargs).bytes)

    def read(self, n) -> bytes:
        buffer = bytearray(self.buf.read())
        while len(buffer) < n:
            buffer = self.read_frames(buffer)
        self.buf = BytesIO(buffer)
        return self.buf.read(n)

    def send_bytes(self, payload: bytes):
        buffer = BytesIO(payload)
        fin = False
        n = buffer.read(OUT_SIZE)
        opcode = OP_BYTES
        while not fin:
            data = n
            n = buffer.read(OUT_SIZE)
            fin = not n
            self.send(
                opcode=opcode,
                fin=fin,
                masked=False,
                payload=data,
            )
            opcode = OP_CONTINUATION

    def start_connection(self):
        upgrade_request = recv_until(self.sock, delimiter="\r\n\r\n")
        handshake = self.get_handshake_response(upgrade_request)
        if not handshake:
            raise ConnectionError("Invalid Handshake")
        self.sock.send(handshake.encode())

    def read_frames(self, buf: bytearray) -> bytearray:
        while self.alive:
            frame = Frame.recv(self.sock)
            if frame.opcode in [OP_BYTES, OP_CONTINUATION]:
                buf.extend(frame.payload)
                if frame.fin:
                    return buf
            elif frame.opcode == OP_CLOSE:
                if frame.fin:
                    self.send_close()
                self.end_connection()
            elif frame.opcode == OP_PING:
                self.send_pong(frame.payload)
            elif frame.opcode == OP_PONG:
                pass
            else:
                log.warn(f"{self} sent invalid frame: {frame}")
                self.end_connection()

    def send_pong(self, payload):
        self.send(
            opcode=OP_PONG,
            fin=True,
            masked=False,
            payload=payload,
        )

    def send_close(self, status_code=None, app_data=None):
        buf = []
        if status_code is not None:
            status_bytes = bytearray([status_code & 255, (status_code >> 8) & 255])
            buf.append(bytes(status_bytes))

        if app_data is not None:
            buf.append(app_data.encode())

        payload = b"".join(buf) if len(buf) > 0 else None
        self.send(opcode=OP_CLOSE, payload=payload)

    def end_connection(self):
        self.alive = False
        self.sock.close()
        raise ConnectionError

    def close(self):
        if self.alive:
            try:
                self.send_close()
            except:
                pass
        self.alive = False
        self.sock.close()

    def get_handshake_response(self, request: str) -> Optional[str]:
        tokens = request.split("\r\n")

        upgrade_set = ["Upgrade: WebSocket", "Upgrade: websocket", "upgrade: websocket"]
        label_set = ["Sec-WebSocket-Key", "sec-websocket-key"]
        if not bool(set(upgrade_set).intersection(tokens)):
            return None
        for token in tokens[1:]:
            label, value = token.split(": ", 1)
            if label in label_set:
                return (
                    "HTTP/1.1 101 Switching Protocols\r\n"
                    "Upgrade: websocket\r\n"
                    "Connection: Upgrade\r\n"
                    f"Sec-WebSocket-Accept: {self.digest(value)}\r\n"
                    "Sec-WebSocket-Protocol: mqtt\r\n"
                    "Sec-WebSocket-Version: 13\r\n\r\n"
                )
        return None

    def digest(self, client_secret_key):
        raw = client_secret_key + self.secret_key
        return b64encode(hashlib.sha1(raw.encode("ascii")).digest()).decode("utf-8")

    @cached_property
    def secret_key(self):
        return "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        #return str(uuid4())
