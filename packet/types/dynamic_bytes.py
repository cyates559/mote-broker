from packet.types.type import PacketType


class PacketDynamicBytes(PacketType):
    @classmethod
    def read(cls, handler, kwargs):
        return handler.decode_bytes()


dynamic_bytes = PacketDynamicBytes
