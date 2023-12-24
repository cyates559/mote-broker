from abc import abstractmethod
from struct import unpack


class ReaderWriter:
    @abstractmethod
    def read(self, n: int) -> bytes:
        pass

    @abstractmethod
    def write(self, data: bytes):
        pass

    def decode_str(self) -> (str, int):
        length_bytes = self.read(2)
        length = unpack("!H", length_bytes)
        if length[0]:
            length = length[0]
            total_length = length + 2
            byte_str = self.read(length)
            try:
                return byte_str.decode(encoding="utf-8"), total_length
            except UnicodeDecodeError:
                return str(byte_str), total_length
        else:
            return "", 2

    def read_int(self, size: int) -> int:
        data = self.read(size)
        return int.from_bytes(data, byteorder="big")

    def decode_bytes(self):
        length_bytes = self.read(2)
        length = unpack("!H", length_bytes)
        data = self.read(length[0])
        byte_count = 2 + length[0]
        return data, byte_count

    def decode_packet_length(self):
        multiplier = 1
        value = 0
        buffer = bytearray()
        while True:
            encoded_byte = self.read(1)
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

    def decode_header(self):
        byte1 = self.read(1)
        int1 = unpack("!B", byte1)
        msg_type = (int1[0] & 0xF0) >> 4
        flags = int1[0] & 0x0F
        return msg_type, flags
