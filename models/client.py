from abc import abstractmethod
from functools import cached_property

from models.messages import OutgoingMessage


class Client:
    id: str

    @abstractmethod
    async def handle_message(self, message: OutgoingMessage):
        pass

    @cached_property
    def _str(self):
        return f"Client {self.id}"

    @cached_property
    def subscriptions(self):
        return set()

    def __repr__(self):
        return self._str
