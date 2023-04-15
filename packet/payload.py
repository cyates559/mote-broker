import inspect
from collections import OrderedDict
from functools import cached_property

from packet.types.type import PacketType


def is_packet_type(obj):
    if inspect.isclass(obj):
        return issubclass(obj, PacketType)
    else:
        return isinstance(obj, PacketType)


class PayloadMeta(type):
    def __init__(cls, name, bases, dct):
        fields = OrderedDict()
        for name, packet_type in dct.items():
            if is_packet_type(packet_type):
                fields[name] = packet_type
        super().__init__(name, bases, dct)
        cls.fields = fields


class Payload(object, metaclass=PayloadMeta):
    def __init__(self, **kwargs):
        for kw, arg in kwargs.items():
            setattr(self, kw, arg)
        self.kwargs = kwargs

    @cached_property
    def _keywords(self) -> str:
        return " ".join([f"{kw}={arg}" for kw, arg in self.kwargs.items()])

    def __repr__(self):
        return f"{self.__class__.__name__}({self._keywords})"
