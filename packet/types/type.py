def enabled_default(*_, **__):
    return True


class PacketType:
    is_enabled = enabled_default

    @classmethod
    def read(cls, handler, kwargs):
        pass

    @classmethod
    def to_bytes(cls, value) -> bytes:
        pass

    def enabled(self, func):
        self.is_enabled = func
        return func
