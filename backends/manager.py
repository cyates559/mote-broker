import dataclasses
from multiprocessing import Process, Condition, Lock, Manager
from typing import Type

from backends.worker import Handle, BackendWorker, QUERY, RESPONSE, RUNNING
from logger import log


@dataclasses.dataclass(frozen=True)
class ProcessManager(Handle):
    name: str
    process: Process
    worker_class = None

    def query(self, *query):
        with self.query_lock:
            with self.task_condition:
                self.status[QUERY] = (tuple(query))
                self.task_condition.notify()
            with self.response_condition:
                response = None
                while response is None:
                    self.response_condition.wait()
                    response = self.status[RESPONSE]
                self.status[RESPONSE] = None
        return response

    @classmethod
    def setup(cls, worker_class: Type[BackendWorker] = None):
        if worker_class is None:
            worker_class = cls.worker_class
        memory_manager = Manager()
        task_condition = Condition(lock=Lock())
        response_condition = Condition(lock=Lock())
        query_lock = Lock(),
        tasks = memory_manager.list([])
        status = memory_manager.list([False, None, None])
        args = (task_condition, tasks, status, query_lock, response_condition,)
        return cls(
            *args,
            name=worker_class.__name__,
            process=Process(target=worker_class, args=args),
        )

    def add_tasks(self, *tasks):
        with self.task_condition:
            self.tasks.extend(tasks)
            self.task_condition.notify()

    def __enter__(self):
        log.info(f"Starting {self.name}...", end="")
        self.status[RUNNING] = True
        self.process.start()
        log.info("Done")

    def __exit__(self, exc_type, exc_val, exc_tb):
        log.info(f"Stopping {self.name}...", end="")
        self.status[RUNNING] = False
        with self.task_condition:
            self.task_condition.notify()
        self.process.join()
        log.info("Done")
