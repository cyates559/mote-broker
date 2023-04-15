from packet.base_packet import PacketWithId
from packet.types.dynamic_str import dynamic_str
from packet.types.dynamic_list import dynamic_list
from packet.types.packet_id import packet_id


class UnsubscribePacket(PacketWithId):
    type_code = 0x0A
    id = packet_id()
    topics = dynamic_list(dynamic_str())
