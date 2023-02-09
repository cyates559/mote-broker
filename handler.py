import dataclasses
from abc import abstractmethod
from functools import cached_property


@dataclasses.dataclass
class Handler:
    @cached_property
    def host(self):
        return self.host_port_tuple[0]

    @cached_property
    def port(self):
        return self.host_port_tuple[1]

    @cached_property
    def host_port_tuple(self):
        return self.get_host_port_tuple()

    @abstractmethod
    def get_host_port_tuple(self) -> (str, int):
        pass

    @abstractmethod
    def write(self, data):
        pass

    @abstractmethod
    async def read(self, n=-1) -> bytes:
        pass

    @abstractmethod
    async def drain(self):
        pass

    @abstractmethod
    async def close(self):
        pass
