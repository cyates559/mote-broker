from packet.base_packet import Packet
from packet.types.dynamic_bytes import dynamic_bytes
from packet.types.dynamic_str import dynamic_str
from packet.types.flag import PacketFlag
from packet.types.flag_group import PacketFlagGroup
from packet.types.static_int import static_int


class WillQOSFlag(PacketFlag):
    @classmethod
    def read(cls, data: int) -> int:
        return (data & 0x18) >> 3

    @classmethod
    def write(cls, data: int, val: int) -> int:
        data &= 0xE7
        data |= val << 3
        return data


class ConnectFlags(PacketFlagGroup):
    clean_session: 0x02
    enable_last_will: 0x04
    retain_last_will: 0x20
    enable_password: 0x40
    enable_username: 0x80
    last_will_qos: WillQOSFlag


class ConnectPacket(Packet):
    type_code = 0x01
    protocol_name = dynamic_str()
    protocol_level = static_int(1)
    connect_flags = ConnectFlags
    keep_alive = static_int(2)
    client_id = dynamic_str(optional=True)
    last_will_topic = dynamic_str()
    last_will_message = dynamic_bytes()
    username = dynamic_str()
    password = dynamic_str()

    @last_will_topic.enabled
    @last_will_message.enabled
    def enable_last_will(self, **kwargs):
        """
        Only read the last will topic and message if the
        enable_last_will flag is set in the packet header
        """
        return kwargs["connect_flags"].enable_last_will

    @username.enabled
    def enable_username(self, **kwargs):
        """
        Only read the username if the enable_username
        flag is set in the packet header
        """
        return kwargs["connect_flags"].enable_username

    @password.enabled
    def enable_password(self, **kwargs):
        """
        Only read the password if the enable_password
        flag is set in the packet header
        """
        return kwargs["connect_flags"].enable_password
