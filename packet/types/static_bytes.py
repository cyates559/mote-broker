import dataclasses

from packet.types.type import PacketType


@dataclasses.dataclass
class PacketStaticBytes(PacketType):
    size: int

    def read(self, handler, kwargs):
        return handler.try_read(self.size)


static_bytes = PacketStaticBytes
