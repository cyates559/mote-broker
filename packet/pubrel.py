from packet.base_packet import PacketWithId
from packet.types.packet_id import packet_id


class PublishReleasedPacket(PacketWithId):
    type_code = 0x06
    id = packet_id()
