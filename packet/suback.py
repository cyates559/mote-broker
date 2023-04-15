from packet.base_packet import PacketWithId
from packet.types.dynamic_list import dynamic_list
from packet.types.static_int import static_int

# noinspection SpellCheckingInspection
SUBACK_INVALID_TOPIC = 0x80


class SubscribeAcknowledgePacket(PacketWithId):
    type_code = 0x09
    id = static_int(2)
    response_codes = dynamic_list(static_int(1))
