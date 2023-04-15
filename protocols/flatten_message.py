from models.constants import EVERYTHING_CARD, ALL_CARD
from protocols.exceptions import InvalidEverythingCard
from utils.tree_item import TreeItem


def flatten_message_into_rows(
    topic: list,
    data: TreeItem,
    qos: int,
    base: list,
) -> list:
    """
    Parse a topic with wildcards into multiple messages
    with payloads cherry-picked from the incoming data tree
    """
    node = topic[0]
    next_topic = topic[1:]
    if node == EVERYTHING_CARD:
        raise InvalidEverythingCard
    elif node == ALL_CARD:
        if not next_topic:
            return [
                (base + [key], val.encode(), qos)
                for key, val in data.items()
            ]
        else:
            result = []
            for key, val in data.items():
                result.extend(flatten_message_into_rows(
                    topic=next_topic,
                    data=val,
                    qos=qos,
                    base=base,
                ))
            return result
    elif not next_topic:
        return [(base + topic, data.encode(), qos)]
    else:
        return flatten_message_into_rows(
            topic=next_topic,
            data=data,
            qos=qos,
            base=base + [node],
        )
