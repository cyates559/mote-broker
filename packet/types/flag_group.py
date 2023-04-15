from packet.types.static_int import PacketStaticInt


class PacketFlagGroup(PacketStaticInt):
    size = 1

    def __init__(self, data: int, kwargs: dict):
        super().__init__(self.size)
        self.data = data
        self.kwargs = kwargs
        for keyword, arg in kwargs.items():
            setattr(self, keyword, arg)

    def __int__(self):
        return self.data

    def __repr__(self):
        items = self.kwargs.items()
        data = " ".join([f"{key}={val}" for key, val in items])
        return f"{self.__class__.__name__}({data})"

    @classmethod
    def from_kwargs(cls, kwargs):
        data = 0
        for name, typ in cls.__annotations__.items():
            if isinstance(typ, int):
                if kwargs[name]:
                    data |= typ
                else:
                    data &= ~typ
            else:
                data = typ.write(data, kwargs[name])
        return cls(data, kwargs)

    @classmethod
    def from_int(cls, data: int):
        kwargs = {}
        for name, typ in cls.__annotations__.items():
            if isinstance(typ, int):
                kwargs[name] = bool(data & typ)
            else:
                kwargs[name] = typ.read(data)
        return cls(data, kwargs)

    @classmethod
    async def read(cls, handler, kwargs):
        f = await handler.read_int(cls.size)
        return cls.from_int(f), cls.size
