from packet.base_packet import PacketWithId
from packet.types.packet_id import packet_id


class PublishReceivedPacket(PacketWithId):
    type_code = 0x05
    id = packet_id()
