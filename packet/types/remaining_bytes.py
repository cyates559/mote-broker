from packet.types.type import PacketType


class PacketRemainingBytes(PacketType):
    async def read(self, handler, kwargs):
        length = kwargs["length"]
        if length == 0:
            return None, 0
        return await handler.try_read(length), length

    @classmethod
    def to_bytes(cls, value) -> bytes:
        return value


remaining_bytes = PacketRemainingBytes
