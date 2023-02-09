import dataclasses
from abc import abstractmethod
from functools import cached_property
from typing import Any


@dataclasses.dataclass
class Server:
    host: str
    port: int
    ssl_context: Any
    event_loop: Any
    instance: Any = None

    @abstractmethod
    async def start_instance(self):
        pass

    async def __aenter__(self):
        print(f"Starting {self.name}...", end="")
        self.instance = await self.start_instance()
        print("Done")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        print(f"Stopping {self.name}...", end="")
        await self.close()
        print("Done")

    async def close(self):
        self.instance.close()

    @cached_property
    def name(self):
        return self.__class__.__name__
