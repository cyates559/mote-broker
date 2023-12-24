import dataclasses
from typing import Union, Type

from packet.payload import Payload
from packet.types.type import PacketType


@dataclasses.dataclass
class PacketDynamicList(PacketType):
    type: Union[PacketType, Type[Payload]]

    def read(self, handler, kwargs):
        result = []
        byte_count = 0
        while kwargs["length"] > 0:
            if isinstance(self.type, PacketType):
                item, read_length = self.type.read(handler, kwargs)
                byte_count += read_length
                kwargs["length"] -= read_length
                result.append(item)
            else:
                sub_kwargs = {}
                for name, subtype in self.type.fields.items():
                    sub_kwargs[name], read_length = subtype.read(handler, kwargs)
                    byte_count += read_length
                    kwargs["length"] -= read_length
                # noinspection PyArgumentList
                result.append(self.type(**sub_kwargs))
        return result, byte_count

    def to_bytes(self, data: list):
        byte_list = [self.type.to_bytes(item) for item in data]
        result = b"".join(byte_list)
        return result


dynamic_list = PacketDynamicList
