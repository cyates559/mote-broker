from models.constants import MANY_CARD, EVERYTHING_CARD


def is_node_static(node: str):
    return node not in [MANY_CARD, EVERYTHING_CARD]
