from packet.base_packet import Packet
from packet.types.static_int import static_int


class ConnectAcknowledgePacket(Packet):
    type_code = 0x02
    session_parent = static_int(1)
    return_code = static_int(1)

    class ReturnCode:
        ACCEPTED = 0x00
        PROTOCOL_VERSION_REJECTED = 0x01
        IDENTIFIER_REJECTED = 0x02
        SERVER_UNAVAILABLE = 0x03
        USERNAME_PASSWORD_REJECTED = 0x04
        NOT_AUTHORIZED = 0x05
