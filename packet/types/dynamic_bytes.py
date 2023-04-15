from packet.types.type import PacketType


class PacketDynamicBytes(PacketType):
    @classmethod
    async def read(cls, handler, kwargs):
        return await handler.decode_bytes()


dynamic_bytes = PacketDynamicBytes
