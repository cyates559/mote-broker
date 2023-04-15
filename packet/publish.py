from packet.base_packet import PacketWithId
from packet.types.dynamic_str import dynamic_str
from packet.types.flag import PacketFlag
from packet.types.flag_group import PacketFlagGroup
from packet.types.packet_id import packet_id
from packet.types.remaining_bytes import remaining_bytes


class QOSFlag(PacketFlag):
    @classmethod
    def read(cls, data: int):
        return (data & 0x06) >> 1

    @classmethod
    def write(cls, data: int, val) -> int:
        data &= 0xF9
        data |= val << 1
        return data


class PublishFlags(PacketFlagGroup):
    retain: 0x01
    qos: QOSFlag


class PublishPacket(PacketWithId):
    type_code = 0x03
    topic = dynamic_str()
    id = packet_id()
    data = remaining_bytes()
    flag_class: PublishFlags

    @id.enabled
    def enable_id(self, flags, **_):
        return flags.qos > 0
