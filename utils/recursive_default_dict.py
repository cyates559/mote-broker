import dataclasses
from collections import defaultdict

from models.constants import LEAF_KEY


@dataclasses.dataclass
class RecursiveDefaultDict(defaultdict):
    default_type: callable = lambda: None

    def __repr__(self):
        return f"{self.__class__.__name__}({self.default_type})"

    def __missing__(self, key):
        if key == LEAF_KEY:
            # noinspection PyNoneFunctionAssignment
            r = self.default_type()
        else:
            r = RecursiveDefaultDict(default_type=self.default_type)
        self[key] = r
        return r

    @property
    def leaf(self):
        return self[LEAF_KEY]

    @leaf.setter
    def leaf(self, data):
        self[LEAF_KEY] = data

    def cascade_delete(self, path: list):
        """
        Climb the tree following a set path, remove the leaf
        at the end of the path and on the way back down remove
        any branches above us that are empty
        """
        node = path[0]
        next_nodes = path[1:]
        if next_nodes:
            self[node].cascade_delete(next_nodes)
        else:
            self[node].pop(LEAF_KEY)
        if not self[node]:
            self.pop(node)

    def __lshift__(self, path: list):
        node = path[0]
        next_path = path[1:]
        if next_path:
            return self[node] << next_path
        else:
            return self[node][LEAF_KEY]

    def __truediv__(self, path: list):
        """
        Return the value at the end of the path if the path can be followed all the way to the end,
        otherwise return None
        """
        node = path[0]
        next_path = path[1:]
        if next_path:
            branch = self[node]
            if branch is None:
                return None
            return branch / next_path
        else:
            return self[node]
