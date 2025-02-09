from functools import cached_property
from typing import List, Optional, Union

from models.constants import TOPIC_SEP, TABLE_FLAG


class Topic:
    def __init__(self, node: str, parent: "Topic" = None, full_str: str = None, node_list: list = None):
        self.node = node
        self.parent = parent
        self._nodes = node_list
        self._str = full_str

    @classmethod
    def from_nodes(cls, nodes: list, **kwargs) -> Optional["Topic"]:
        if len(nodes) == 0:
            return None
        if len(nodes) == 1:
            parent = None
        else:
            parent = cls.from_nodes(nodes[:-1])
        return cls(nodes[-1], parent=parent, **kwargs)

    @classmethod
    def from_str(cls, s: str) -> Optional["Topic"]:
        return cls.from_nodes(s.split(TOPIC_SEP), full_str=s)

    def __truediv__(self, node: str) -> "Topic":
        return Topic(node, parent=self)

    def __str__(self):
        return self.full_str

    def __repr__(self):
        return f"{self.__class__.__name__}({self.full_str})"

    def __hash__(self):
        return self.__str__().__hash__()

    def __eq__(self, other):
        return str(self) == str(other)

    def __getitem__(self, item: int) -> Union[str, "Topic"]:
        r = self.node_list[item]
        if isinstance(item, slice):
            # ignore pycharm, r is a list
            # noinspection PyTypeChecker
            return self.__class__.from_nodes(r)
        else:
            return r

    @cached_property
    def for_table(self) -> bool:
        return self.node_list[0][0] == TABLE_FLAG

    @cached_property
    def length(self):
        return len(self.node_list)

    @property
    def full_str(self) -> str:
        if self._str is None:
            self._str = TOPIC_SEP.join(self.node_list)
        return self._str

    @property
    def node_list(self) -> List[str]:
        if self._nodes is None:
            ancestors = []
            topic = self
            while topic is not None:
                ancestors.append(topic.node)
                topic = topic.parent
            self._nodes = list(reversed(ancestors))
        return self._nodes
