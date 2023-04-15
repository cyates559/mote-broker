from packet.base_packet import PacketWithId
from packet.payload import Payload
from packet.types.dynamic_list import dynamic_list
from packet.types.dynamic_str import dynamic_str
from packet.types.static_int import static_int


class SubscribePayload(Payload):
    topic = dynamic_str()
    qos = static_int(1)


class SubscribePacket(PacketWithId):
    type_code = 0x08
    id = static_int(2)
    requests = dynamic_list(SubscribePayload)
