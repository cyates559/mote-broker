from functools import cached_property

from backends.worker import BackendWorker


class StoreWorker(BackendWorker):
    @cached_property
    def command_map(self):
        return {
            "": None
        }

    def run_tasks(self, *tasks: (str,)):
        for _ in tasks:
            print(_)