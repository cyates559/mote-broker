from collections import defaultdict

from models.constants import LEAF_KEY, ALL_CARD
from protocols.is_node_static import is_node_static
from protocols.stringify import stringify
from utils.recursive_default_dict import RecursiveDefaultDict


def build_message_data(leaf_rows: list, base: list):
    tree = RecursiveDefaultDict()
    for topic, data, _ in leaf_rows:
        ref = [tree]
        ref_key = 0
        # we climb to the second to last node in the path;
        # the last node to climb is set to ref_key;
        for current_filter_node, node in zip(base, topic):
            if not is_node_static(current_filter_node):
                ref = ref[ref_key]
                ref_key = node
        # set the leaf
        ref[ref_key] = data
    return stringify(tree)


def _create_messages_for_subscriptions(subscriptions: dict, rows: list, base: list, depth=0):
    """
    Return a list of tuples of ([(client, qos), ...], topic, data)
    """
    leaf_rows = []
    rows_by_current_node = defaultdict(list)
    # organize rows into a dict by literal node at given depth
    for row in rows:
        topic = row[0]
        try:
            # branch
            node = topic[depth]
        except IndexError:
            # leaf
            leaf_rows.append(row)
        else:
            rows_by_current_node[node].append(row)

    messages = []
    for filter_node, branch in subscriptions.items():
        if filter_node == LEAF_KEY:
            response_data = build_message_data(
                leaf_rows,
                base,
            )
            messages.append((
                branch,
                base,
                response_data,
            ))
        else:
            if filter_node == ALL_CARD:
                new_rows = rows
            else:
                new_rows = rows_by_current_node[filter_node]
            if new_rows:
                messages.extend(
                    _create_messages_for_subscriptions(
                        subscriptions=branch,
                        rows=new_rows,
                        base=base + [filter_node],
                        depth=depth + 1,
                    )
                )
    return messages


def create_messages_for_subscriptions(subscriptions, rows):
    return _create_messages_for_subscriptions(subscriptions, rows, [])
