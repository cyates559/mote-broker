from packet.base_packet import BlankPacket


class PingResponsePacket(BlankPacket):
    type_code = 0x0D
