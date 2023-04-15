from packet.base_packet import Packet


class DisconnectPacket(Packet):
    fixed_header = 0x0E
