from logger import log
from packet.payload import Payload


class PacketMismatchError(Exception):
    def __init__(self, expected_class, actual_class):
        super().__init__(
            f"Expected to receive {expected_class}, but actually received {actual_class}"
        )


class Packet(Payload):
    type_code: int
    length: int

    def __init__(self, flags=0x00, length=0, **kwargs):
        flag_class = self.__annotations__.get("flag_class")
        if flag_class:
            if isinstance(flags, dict):
                self.flags = flag_class.from_kwargs(flags)
            else:
                self.flags = flag_class.from_int(flags)
        else:
            self.flags = flags
        self.length = length
        super().__init__(**kwargs, flags=self.flags)

    @classmethod
    def read_payload(cls, handler, flags_int, length) -> (dict, int):
        kwargs = {"length": length}
        flag_class = cls.__annotations__.get("flag_class")
        if flag_class:
            kwargs["flags"] = flag_class.from_int(flags_int)
        byte_count = 0
        for name, packet_type in cls.fields.items():
            if packet_type.is_enabled(None, **kwargs):
                kwargs[name], read_length = packet_type.read(handler, kwargs)
                byte_count += read_length
                kwargs["length"] -= read_length
        kwargs["length"] = length
        kwargs["flags"] = flags_int
        return kwargs, byte_count

    def get_header_bytes(self, length) -> bytearray:
        header = bytearray()
        header.append((self.type_code << 4) | int(self.flags))
        while True:
            length_byte = length % 0x80
            length //= 0x80
            if length > 0:
                length_byte |= 0x80
            header.append(length_byte)
            if length <= 0:
                break
        return header

    def to_bytes(self):
        cls = self.__class__
        payload = bytearray()
        for name, packet_type in cls.fields.items():
            if not packet_type.is_enabled(None, **self.kwargs):
                continue
            try:
                data = self.kwargs.get(name)
            except KeyError:
                raise TypeError(f"{cls.__name__}: {name} not found")
            b = packet_type.to_bytes(data)
            payload.extend(b)
        length = len(payload)
        header_bytes = self.get_header_bytes(length)
        return header_bytes + payload

    @classmethod
    def read(cls, handler, flags=None):
        if flags is None:
            msg_type, flags = handler.decode_header()
            cur_class = handler.infer_packet_class(msg_type)
            if cls != cur_class:
                raise PacketMismatchError(cls, cur_class)
        length = handler.decode_packet_length()
        kwargs, bytes_read = cls.read_payload(handler, flags, length)
        # noinspection PyArgumentList
        result = cls(**kwargs)
        client_id = result.__dict__.get("client_id")
        if client_id is None:
            client_id = handler.id
        log.info("Read", result, "from", client_id)
        handler.flush()
        return result

    def write(self, handler):
        data = self.to_bytes()
        handler.write(data)
        log.info("Wrote", self, "to", handler.id)


class PacketWithId(Packet):
    id: int


class BlankPacket(Packet):
    def __repr__(self):
        return self.__class__.__name__
