from packet.base_packet import BlankPacket


class PingRequestPacket(BlankPacket):
    type_code = 0x0C
