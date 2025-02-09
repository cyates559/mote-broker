from asyncio import Task
from functools import cached_property
from typing import Any

from models.client import Client
from utils.recursive_default_dict import RecursiveDefaultDict


class BrokerContext:
    instance: Any
    main_task: Task
    running = True

    def __new__(cls, *args, **kwargs):
        self = BrokerContext.instance = super().__new__(cls)
        self.main_task = None
        self.subscriptions = RecursiveDefaultDict(default_type=dict)
        return self

    @cached_property
    def clients(self) -> dict[str, Client]:
        return {}
