import dataclasses
from abc import abstractmethod
from functools import cached_property
from threading import Thread

from logger import log


@dataclasses.dataclass
class Server:
    host: str
    port: int
    alive: bool = False

    @cached_property
    def name(self):
        return self.__class__.__name__

    @cached_property
    def thread(self):
        return Thread(target=self.loop)

    @abstractmethod
    def loop(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    def __enter__(self):
        log.info(f"Starting {self.name}...", end="")
        self.thread.start()
        log.info("Done")

    def __exit__(self, exc_type, exc_val, exc_tb):
        log.info(f"Stopping {self.name}...", end="")
        self.stop()
        self.thread.join()
        log.info("Done")
