import dataclasses
from struct import unpack

from packet.types.static_int import PacketStaticInt


@dataclasses.dataclass
class PacketIdType(PacketStaticInt):
    size: int = 2

    async def read(self, handler, kwargs):
        raw_data = await handler.try_read(self.size)
        data = unpack("!H", raw_data)
        return data[0], self.size


packet_id = PacketIdType
