from asyncio import Task
from typing import Any

from utils.recursive_default_dict import RecursiveDefaultDict


class BrokerContext:
    instance: Any
    tree: RecursiveDefaultDict
    main_task: Task
    running = True

    def __new__(cls, *args, **kwargs):
        self = BrokerContext.instance = super().__new__(cls, *args, **kwargs)
        self.main_task = None
        self.subscriptions = RecursiveDefaultDict(default_type=dict)
        self.clients = {}
        return self
