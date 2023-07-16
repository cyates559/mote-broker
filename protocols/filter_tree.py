from models.constants import EVERYTHING_CARD, MANY_CARD, LEAF_KEY
from protocols.exceptions import InvalidEverythingCard
from protocols.is_node_static import is_node_static
from utils.tree_item import empty, TreeItem


def filter_tree_with_topic(
    topic: list,
    tree: TreeItem,
    found_wildcard=False,
) -> TreeItem:
    """
    Cherry-pick a retained tree to create a
    new tree based on a topic structure
    """
    node = topic[0]
    next_topic = topic[1:]
    if node == EVERYTHING_CARD:
        if not next_topic:
            return tree
        raise InvalidEverythingCard(next_topic)
    elif node == MANY_CARD:
        result = {}
        if not next_topic:
            for key, val in tree.items():
                if key == LEAF_KEY:
                    continue
                leaf = val.get(LEAF_KEY)
                if leaf:
                    result[key] = leaf
        else:
            for key, val in tree.items():
                if key == LEAF_KEY:
                    continue
                branch = filter_tree_with_topic(
                    topic=next_topic,
                    tree=val,
                    found_wildcard=True,
                )
                if branch not in ["", {}]:
                    result[key] = branch
        return result
    else:
        branch = tree.get(node)
        if branch is None:
            if next_topic:
                found_wildcard = not is_node_static(next_topic[-1])
            else:
                found_wildcard = False
            return {} if found_wildcard else ""
        elif not next_topic:
            return branch.get(LEAF_KEY, empty)
        else:
            return filter_tree_with_topic(
                topic=next_topic,
                tree=branch,
                found_wildcard=found_wildcard,
            )
