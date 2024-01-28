import dataclasses
from abc import abstractmethod
from multiprocessing import Condition, Lock
from typing import Any


RUNNING: int = 0
QUERY = 1
RESPONSE = 1


@dataclasses.dataclass(frozen=True)
class Handle:
    task_condition: Condition
    tasks: "ListProxy"
    status: "ListProxy"
    query_lock: Lock
    response_condition: Condition


class BackendWorker(Handle):
    @abstractmethod
    def run_tasks(self, *tasks):
        pass

    def query(self, *args) -> Any:
        return True

    def setup(self):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup()
        try:
            while self.status[RUNNING]:
                with self.task_condition:
                    while True:
                        self.task_condition.wait()
                        running, query, _ = self.status
                        consumed_tasks = list(self.tasks)
                        while self.tasks:
                            self.tasks.pop()
                        self.status[QUERY] = None
                        if query or consumed_tasks or not running:
                            break
                if query:
                    self.status[RESPONSE] = self.query(*query)
                    self.response_condition.notify()
                if consumed_tasks:
                    self.run_tasks(*consumed_tasks)
        except (KeyboardInterrupt, InterruptedError):
            pass
