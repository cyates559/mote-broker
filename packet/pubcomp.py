from packet.base_packet import PacketWithId
from packet.types.packet_id import packet_id


class PublishCompletePacket(PacketWithId):
    type_code = 0x07
    id = packet_id()
