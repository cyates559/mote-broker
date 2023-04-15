from logger import log
from models.constants import LEAF_KEY, EVERYTHING_CARD, ALL_CARD
from protocols.exceptions import InvalidEverythingCard
from protocols.is_node_static import is_node_static
from utils.tree_item import TreeItem, empty


def get_everything_as_rows(topic: list, data: bytes, qos: int, tree: TreeItem, start=True):
    """
    Obtain a list of rows to be updated with data that
    covers an entire retained tree (or branch)
    """
    result = []
    for key, val in tree.items():
        if key == LEAF_KEY and not start:
            result.append((topic, data, qos))
        elif val is None:
            log.error("branch is null", topic, data)
        else:
            branch_rows = get_everything_as_rows(
                topic=topic + [key], data=data, qos=qos, tree=val, start=False,
            )
            result.extend(branch_rows)
    return result


def get_applicable_rows(topic: list, data: bytes, qos: int, base: list, tree: TreeItem, found_wildcard=False) -> list:
    """
    Parse an incoming message into one or more rows with matching
    payloads; Topics are cherry-picked from a retained tree
    """
    node = topic[0]
    next_topic = topic[1:]
    if node == EVERYTHING_CARD:
        if next_topic:
            raise InvalidEverythingCard
        return get_everything_as_rows(
            topic=base,
            data=data,
            qos=qos,
            tree=tree,
        )
    elif node == ALL_CARD:
        result = []
        if not next_topic:
            for key, branch in tree.items():
                if key == LEAF_KEY:
                    continue
                result.append((base + [key], data, qos))
        else:
            for key, branch in tree.items():
                if key == LEAF_KEY:
                    continue
                branch_rows = get_applicable_rows(
                    topic=next_topic,
                    data=data,
                    qos=qos,
                    base=base + [key],
                    tree=branch,
                    found_wildcard=True,
                )
                result.extend(branch_rows)
        return result
    elif not next_topic:
        return [(base + topic, data, qos)]
    else:
        branch = tree.get(node, empty)
        if branch is empty:
            if found_wildcard:
                return []
            else:
                for node in next_topic:
                    if not is_node_static(node):
                        return []
                return [(base + topic, data, qos)]
        return get_applicable_rows(
            topic=next_topic,
            data=data,
            qos=qos,
            base=base + [node],
            tree=branch,
            found_wildcard=found_wildcard
        )
