import dataclasses
from io import BytesIO

from websockets.exceptions import ConnectionClosed
from websockets.legacy.server import WebSocketServerProtocol

from exceptions.disconnected import Disconnected
from handlers.handler import Handler


def init_stream():
    return BytesIO(b"")


@dataclasses.dataclass
class WebsocketHandler(Handler):
    protocol: WebSocketServerProtocol
    input: BytesIO = dataclasses.field(default_factory=init_stream)
    output: BytesIO = dataclasses.field(default_factory=init_stream)

    def get_host_port_tuple(self):
        return self.protocol.remote_address

    def write(self, data):
        self.output.write(data)

    async def read(self, n=-1) -> bytes:
        await self.feed_buffer(n)
        data = self.input.read(n)
        return data

    async def drain(self):
        data = self.output.getvalue()
        if len(data):
            await self.protocol.send(data)
        self.output = init_stream()

    async def close(self):
        await self.protocol.close()

    async def feed_buffer(self, n=1):
        buffer = bytearray(self.input.read())
        while len(buffer) < n:
            try:
                message = await self.protocol.recv()
            except ConnectionClosed:
                raise Disconnected
            if message is None:
                break
            if not isinstance(message, bytes):
                raise TypeError("message must be bytes")
            buffer.extend(message)
        self.input = BytesIO(buffer)
