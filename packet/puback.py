from packet.base_packet import PacketWithId
from packet.types.packet_id import packet_id


class PublishAcknowledgePacket(PacketWithId):
    type_code = 0x04
    id = packet_id()
