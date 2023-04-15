from packet.connack import ConnectAcknowledgePacket
from packet.connect import ConnectPacket
from packet.pingreq import PingRequestPacket
from packet.pingresp import PingResponsePacket
from packet.puback import PublishAcknowledgePacket
from packet.pubcomp import PublishCompletePacket
from packet.publish import PublishPacket
from packet.pubrec import PublishReceivedPacket
from packet.pubrel import PublishReleasedPacket
from packet.suback import SubscribeAcknowledgePacket
from packet.subscribe import SubscribePacket
from packet.unsub import UnsubscribePacket
from packet.unsuback import UnsubscribeAcknowledgePacket


all_packets = [
    ConnectPacket,
    ConnectAcknowledgePacket,
    PublishPacket,
    PublishAcknowledgePacket,
    PublishReceivedPacket,
    PublishReleasedPacket,
    PublishCompletePacket,
    SubscribePacket,
    SubscribeAcknowledgePacket,
    UnsubscribePacket,
    UnsubscribeAcknowledgePacket,
    PingRequestPacket,
    PingResponsePacket,
]


class UnknownPacketError(Exception):
    pass


def infer_packet_class(packet_type: int):
    for cls in all_packets:
        if cls.type_code == packet_type:
            return cls
    raise UnknownPacketError(packet_type)
