import dataclasses
from asyncio import StreamReader, StreamWriter

from handlers.handler import Handler

# noinspection SpellCheckingInspection
PEER_NAME = "peername"


@dataclasses.dataclass
class MQTTHandler(Handler):
    reader: StreamReader
    writer: StreamWriter
    is_closed: bool = False

    def get_host_port_tuple(self):
        extra_info = self.writer.get_extra_info(PEER_NAME)
        return extra_info[0], extra_info[1]

    def write(self, data):
        if not self.is_closed:
            self.writer.write(data)

    async def read(self, size=-1) -> bytes:
        if size == -1:
            return await self.reader.read(size)
        return await self.reader.readexactly(size)

    async def drain(self):
        if not self.is_closed:
            await self.writer.drain()

    async def close(self):
        if not self.is_closed:
            self.is_closed = True
            await self.writer.drain()
            if self.writer.can_write_eof():
                self.writer.write_eof()
            self.writer.close()
            await self.writer.wait_closed()
