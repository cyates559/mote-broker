import dataclasses
import errno
from socket import socket, timeout
from functools import cached_property

from logger import log

OP_CONTINUATION = 0
OP_TEXT = 1
OP_BYTES = 2
OP_CLOSE = 8
OP_PING = 9
OP_PONG = 10

FIN_OFFSET = 7
FIN_MASK = 128

"""
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-------+-+-------------+-------------------------------+
    |F|R|R|R| opcode|M| Payload len |    Extended payload length    |
    |I|S|S|S|  (4)  |A|     (7)     |             (16/64)           |
    |N|V|V|V|       |S|             |   (if payload len==126/127)   |
    | |1|2|3|       |K|             |                               |
    +-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
    |     Extended payload length continued, if payload len == 127  |
    + - - - - - - - - - - - - - - - +-------------------------------+
    |                               |Masking-key, if MASK set to 1  |
    +-------------------------------+-------------------------------+
    | Masking-key (continued)       |          Payload Data         |
    +-------------------------------- - - - - - - - - - - - - - - - +
    :                     Payload Data continued ...                :
    + - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
    |                     Payload Data continued ...                |
    +---------------------------------------------------------------+
"""

@dataclasses.dataclass
class Frame:
    opcode: int
    fin: bool = True
    masked: bool = False
    rsv1: bool = False
    rsv2: bool = False
    rsv3: bool = False
    payload: bytes = None
    encoded: bytes = None

    @property
    def text(self):
        return self.payload.decode()

    @cached_property
    def bytes(self):
        if self.encoded is not None:
            return self.encoded
        mask = 0
        result = bytearray()
        result.append((self.fin << FIN_OFFSET) ^ self.opcode)
        payload_len = len(self.payload) if self.payload else 0
        if payload_len < 126:
            result.append((mask << 7) ^ payload_len)
        elif payload_len < 65535:
            result.append((mask << 7) ^ 126)
            for i in [1, 0]:
                result.append((payload_len >> (i * 8)) & 255)
        else:
            result.append((mask << 7) ^ 127)
            for i in range(6, -1, -1):
                result.append((payload_len >> (i * 8)) & 255)
        if payload_len > 0:
            result.extend(self.payload)
        return bytes(result)

    @staticmethod
    def unmask(key: bytes, data: bytes) -> bytes:
        result = bytearray(data[i] ^ key[i % 4] for i in range(len(data)))
        return bytes(result)

    @classmethod
    def recv(cls, sock: socket):
        try:
            header = sock.recv(2)
            fin = (header[0] & 128) == 128
            opcode = (header[0] & 15)
            masked = (header[1] & 128) == 128
            payload_len = (header[1] & 127)
            if payload_len == 126:
                payload_len = int.from_bytes(sock.recv(2), 'big')
            elif payload_len == 127:
                payload_len = int.from_bytes(sock.recv(8), 'big')
            if payload_len == 0:
                payload = b""
                if masked:
                    sock.recv(4)
            elif masked:
                data = sock.recv(payload_len + 4)
                payload = cls.unmask(data[:4], data[4:])
            else:
                payload = sock.recv(payload_len)
        except IndexError:
            sock.close()
            raise ConnectionError("Unable to read")
        except timeout:
            sock.close()
            raise ConnectionError("Unable to read")
        except ConnectionError:
            sock.close()
            raise
        except OSError as exc:
            if exc.errno == errno.ENOTCONN:
                sock.close()
            raise ConnectionError from exc
        result = cls(
            fin=fin,
            opcode=opcode,
            masked=masked,
            payload=payload,
        )
        return result


HardClose = Frame(opcode=OP_CLOSE, fin=False)
