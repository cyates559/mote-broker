import dataclasses
from abc import abstractmethod
from multiprocessing import Condition, Lock
from typing import Any


RUNNING: int = 0
QUERY = 1
RESPONSE = 1


@dataclasses.dataclass
class ProcessHandle:
    task_condition: Condition
    tasks: "ListProxy"
    responses: "ListProxy"
    status: "ListProxy"
    query_lock: Lock
    response_condition: Condition


class ProcessWorker(ProcessHandle):
    """
    Describes a background process worker that can consume tasks and run queries.
    The worker MUST implement the `run_tasks` method and can also implement the `query` method.
    """
    @abstractmethod
    def run_tasks(self, tasks: list):
        """
        This method must consume all the tasks passed to it.
        Tasks can be any type. They can be added to the task queue via the `ProcessManager` class.
        """

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
                    with self.response_condition:
                        self.response_condition.notify()
                if consumed_tasks:
                    self.run_tasks(*consumed_tasks)
        except (KeyboardInterrupt, InterruptedError):
            pass


