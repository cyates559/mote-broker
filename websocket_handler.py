import dataclasses
from io import BytesIO

from websockets.exceptions import ConnectionClosed
from websockets.legacy.protocol import WebSocketCommonProtocol

from handler import Handler


@dataclasses.dataclass
class WebsocketHandler(Handler):
    @staticmethod
    def init_stream():
        return BytesIO(b"")

    protocol: WebSocketCommonProtocol
    uri: str
    stream: BytesIO = dataclasses.field(default_factory=init_stream)

    def get_host_port_tuple(self):
        return self.protocol.remote_address

    def write(self, data):
        self.stream.write(data)

    async def read(self, n=-1) -> bytes:
        await self.feed_buffer(n)
        data = self.stream.read(n)
        return data

    async def drain(self):
        data = self.stream.getvalue()
        if len(data):
            await self.protocol.send(data)
        self.stream = self.init_stream()

    async def close(self):
        await self.protocol.close()

    async def feed_buffer(self, n=1):
        buffer = bytearray(self.stream.read())
        while len(buffer) < n:
            try:
                message = await self.protocol.recv()
            except ConnectionClosed:
                message = None
            if message is None:
                break
            if not isinstance(message, bytes):
                raise TypeError("message must be bytes")
            buffer.extend(message)
        self.stream = self.init_stream()
