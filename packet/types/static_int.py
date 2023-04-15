import dataclasses
from struct import pack

from packet.types.type import PacketType


@dataclasses.dataclass
class PacketStaticInt(PacketType):
    size: int

    async def read(self, handler, kwargs):
        return await handler.read_int(self.size), self.size

    def to_bytes(self, value: int):
        if self.size == 1:
            fmt = "!B"
        elif self.size == 2:
            fmt = "!H"
        else:
            raise TypeError("Int too big")
        data = pack(fmt, value)
        return data


static_int = PacketStaticInt
