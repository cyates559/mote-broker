from abc import abstractmethod
from asyncio import IncompleteReadError
from struct import unpack

from exceptions.disconnected import Disconnected


class ReaderWriter:
    async def try_read(self, size=-1, optional=False):
        try:
            data = await self.read(size)
        except (IncompleteReadError, ConnectionResetError, BrokenPipeError):
            if optional:
                return None
            else:
                raise Disconnected
        if not (data or optional):
            raise Disconnected
        return data

    async def decode_str(self, optional) -> (str, int):
        length_bytes = await self.try_read(2)
        length = unpack("!H", length_bytes)
        if length[0]:
            length = length[0]
            total_length = length + 2
            byte_str = await self.try_read(length, optional=optional)
            try:
                return byte_str.decode(encoding="utf-8"), total_length
            except UnicodeDecodeError:
                return str(byte_str), total_length
        else:
            return "", 2

    async def read_int(self, size: int) -> int:
        data = await self.try_read(size)
        return int.from_bytes(data, byteorder="big")

    async def decode_bytes(self):
        length_bytes = await self.try_read(2)
        length = unpack("!H", length_bytes)
        data = await self.try_read(length[0])
        byte_count = 2 + length[0]
        return data, byte_count

    async def decode_packet_length(self):
        multiplier = 1
        value = 0
        buffer = bytearray()
        while True:
            encoded_byte = await self.read(1)
            int_byte = unpack("!B", encoded_byte)
            buffer.append(int_byte[0])
            value += (int_byte[0] & 0x7F) * multiplier
            if (int_byte[0] & 0x80) == 0:
                break
            else:
                multiplier *= 128
                if multiplier > 128 * 128 * 128:
                    buf_str = "0x" + "".join(format(b, "02x") for b in buffer)
                    raise IOError(f"Invalid remaining length bytes: {buf_str}")
        return value

    async def decode_header(self, block=True):
        byte1 = await self.try_read(1)
        int1 = unpack("!B", byte1)
        msg_type = (int1[0] & 0xF0) >> 4
        flags = int1[0] & 0x0F
        return msg_type, flags

    @abstractmethod
    async def read(self, n=-1) -> bytes:
        pass

    @abstractmethod
    def write(self, data: bytes):
        pass
