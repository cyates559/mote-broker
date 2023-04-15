import dataclasses
from json import loads as treeify

from models.constants import TOPIC_SEP
from models.topic import Topic
from packet.connect import ConnectPacket
from packet.publish import PublishPacket
from protocols.get_applicable_rows import get_applicable_rows
from protocols.flatten_message import flatten_message_into_rows
from protocols.exceptions import DynamicMessageError
from protocols.is_node_static import is_node_static
from protocols.stringify import stringify


@dataclasses.dataclass
class IncomingMessage:
    topic: Topic
    qos: int
    retain: bool
    update: bool
    tree: bool
    data: bytes

    @classmethod
    def from_packet(cls, packet: PublishPacket):
        return cls.from_raw_data(packet.topic, packet.data, packet.flags.qos, packet.flags.retain)

    def flatten_into_rows(self) -> list:
        data = treeify(self.data.decode())
        return flatten_message_into_rows(
            self.topic.node_list,
            data,
            self.qos,
            [],
        )

    @classmethod
    def from_raw_data(cls, raw_topic: str, data: bytes, qos: int, retain: bool):
        """
        The tree flag is normally False unless
        the topic has a trailing boob;
        The update flag is normally True unless
        the topic has a trailing slash
        """
        if retain:
            first = raw_topic[-1]
            topic = raw_topic
            if first == "/":
                topic = topic[:-1]
                tree = True
            else:
                tree = False
            return cls(
                topic=Topic.from_str(topic),
                qos=qos,
                retain=True,
                update=True,
                tree=tree,
                data=data,
            )
        else:
            return cls(
                topic=Topic.from_str(raw_topic),
                qos=qos,
                retain=False,
                update=False,
                tree=False,
                data=data,
            )

    def get_applicable_rows(self, tree):
        return get_applicable_rows(self.topic.node_list, self.data, self.qos, [], tree)

    def as_single_row(self):
        for node in self.topic.node_list:
            if not is_node_static(node):
                raise DynamicMessageError
        return (self.topic.node_list, self.data, self.qos)

    @classmethod
    def last_will(cls, packet: ConnectPacket):
        return cls.from_raw_data(
            packet.last_will_topic,
            packet.last_will_message,
            packet.connect_flags.last_will_qos,
            packet.connect_flags.retain_last_will,
        )


@dataclasses.dataclass
class OutgoingMessage:
    topic: str
    qos: int
    data: bytes

    @classmethod
    def from_tree_item(cls, topic: str, qos: int, tree_item):
        if isinstance(tree_item, dict):
            tree_item = stringify(tree_item)
        return cls(topic=topic, qos=qos, data=tree_item)
