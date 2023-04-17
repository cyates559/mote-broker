from models.constants import EVERYTHING_CARD, MANY_CARD, LEAF_KEY
from protocols.exceptions import InvalidEverythingCard
from utils.recursive_default_dict import RecursiveDefaultDict
from utils.tree_item import TreeItem, empty

missing = object()


def flatten_message_into_rows(
    topic: list,
    data: TreeItem,
    qos: int,
    base: list,
    tree: RecursiveDefaultDict,
) -> list:
    """
    Parse a topic with wildcards into multiple messages
    with payloads cherry-picked from the incoming data tree
    """
    node = topic[0]
    next_topic = topic[1:]
    if node == EVERYTHING_CARD:
        raise InvalidEverythingCard
    elif node == MANY_CARD:
        if not next_topic:
            flags = data.pop(LEAF_KEY, None)
            results = [
                (base + [key], val.encode(), qos)
                for key, val in data.items()
            ]
            if flags == MANY_CARD:
                # using this flag means the keys in our retained tree should
                # match the keys in the retained tree once we are done
                for key, val in tree.items():
                    if key == LEAF_KEY:
                        continue
                    leaf = val.get(LEAF_KEY, missing)
                    if leaf is missing:
                        continue
                    if data.get(key, missing) is missing:
                        results.append((base + [key], empty, qos))
            return results
        else:
            result = []
            for key, val in data.items():
                result.extend(flatten_message_into_rows(
                    topic=next_topic,
                    data=val,
                    qos=qos,
                    base=base + [key],
                    tree=tree.get(key, {}),
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
            tree=tree.get(node, {})
        )
