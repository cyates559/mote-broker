import dataclasses
from abc import abstractmethod
from functools import cached_property
from typing import Any

from logger import log


@dataclasses.dataclass
class Server:
    host: str
    port: int
    ssl_context: Any
    instance: Any = None

    @abstractmethod
    async def start_instance(self):
        pass

    async def __aenter__(self):
        log.info(f"Starting {self.name}...", end="")
        try:
            self.instance = await self.start_instance()
        except:
            log.traceback()
            raise
        log.info("Done")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        log.info(f"Stopping {self.name}...", end="")
        await self.close()
        log.info("Done")

    async def close(self):
        self.instance.close()

    @cached_property
    def name(self):
        return self.__class__.__name__
