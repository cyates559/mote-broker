from logger import log
from models.constants import LEAF_KEY
from utils.tree_item import TreeItem


def get_everything_as_rows(
    topic: list, data: bytes, qos: int, tree: TreeItem, start=True
):
    """
    Obtain a list of rows to be updated with data that
    covers an entire retained tree (or branch)
    """
    result = []
    print("T", topic, data)
    for key, val in tree.items():
        if key == LEAF_KEY and not start:
            result.append((topic, data, qos))
        elif val is None:
            log.error("branch is null", topic, data)
        else:
            branch_rows = get_everything_as_rows(
                topic=topic + [key],
                data=data,
                qos=qos,
                tree=val,
                start=False,
            )
            result.extend(branch_rows)
    return result
