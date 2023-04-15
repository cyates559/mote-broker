import dataclasses

from packet.types.static_int import static_int
from packet.types.type import PacketType


str_size = static_int(2)


@dataclasses.dataclass
class PacketDynamicStr(PacketType):
    optional: bool = False

    async def read(self, handler, kwargs):
        r = await handler.decode_str(optional=self.optional)
        return r

    @classmethod
    def to_bytes(cls, value):
        data = value.encode(encoding="utf-8")
        data_length = len(data)
        return str_size.to_bytes(data_length) + data


dynamic_str = PacketDynamicStr
