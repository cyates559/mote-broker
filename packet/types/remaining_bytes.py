from packet.types.type import PacketType


class PacketRemainingBytes(PacketType):
    def read(self, handler, kwargs):
        length = kwargs["length"]
        if length < 1:
            return None, 0
        return handler.read(length), length

    @classmethod
    def to_bytes(cls, value) -> bytes:
        if value is None:
            return b""
        return value


remaining_bytes = PacketRemainingBytes
