from abc import abstractmethod
from functools import cached_property
from queue import Queue
from threading import Thread

from models.messages import OutgoingMessage


class Client:
    id: str
    alive: bool

    @cached_property
    def _str(self):
        return f"Client {self.id}"

    @cached_property
    def subscriptions(self):
        return set()

    @cached_property
    def message_queue(self) -> Queue[OutgoingMessage]:
        return Queue()

    def __str__(self):
        return self._str

    def queue_message(self, message: OutgoingMessage):
        self.message_queue.put(message)

    @abstractmethod
    def write_loop(self):
        pass

    @abstractmethod
    def read_loop(self):
        pass

    @abstractmethod
    def override_connection(self):
        pass

    @cached_property
    def read_thread(self):
        return Thread(target=self.read_loop, daemon=False)

    @cached_property
    def write_thread(self):
        return Thread(target=self.write_loop, daemon=False)

    def start_threads(self):
        self.read_thread.start()
        self.write_thread.start()
