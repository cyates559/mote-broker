from models.constants import ALL_CARD, EVERYTHING_CARD


def is_node_static(node: str):
    return node not in [ALL_CARD, EVERYTHING_CARD]
