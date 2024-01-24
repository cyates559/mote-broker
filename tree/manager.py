import os
from functools import cached_property
from multiprocessing import Process, Condition, Lock, Manager

from logger import log
from models.topic import TOPIC_SEP
from utils.recursive_default_dict import RecursiveDefaultDict


class PersistenceManager:
    def __init__(self):
        self.condition = Condition(lock=Lock())
        self.running = Manager().list([False])
        self.events = Manager().list()
        self.process = self.create_loop_process()

    def create_loop_process(self):
        return Process(
            target=loop, args=(self.running, self.condition, self.events)
        )

    @staticmethod
    def load_tree() -> RecursiveDefaultDict:
        import django

        os.environ["DJANGO_SETTINGS_MODULE"] = "db.settings"
        django.setup()
        from tree.models import Message

        results = RecursiveDefaultDict()
        for message in Message.objects.all():
            split_topic = message.topic.split("/")
            pointer = results
            for node in split_topic:
                if node != "":
                    pointer = pointer[node]
            pointer["/"] = message.data
        return results

    def retain(self, *messages: (list, bytes, int)):
        with self.condition:
            self.events.extend(messages)
            self.condition.notify()

    @staticmethod
    def parse_topic(topic: str) -> str:
        parsed = topic.replace("//", "/")
        return parsed

    @cached_property
    def name(self):
        return self.__class__.__name__

    def start(self):
        log.info(f"Starting {self.name}...", end="")
        self.running[0] = True
        self.process.start()
        log.info("Done")

    def stop(self):
        log.info(f"Stopping {self.name}...", end="")
        self.running[0] = False
        with self.condition:
            self.condition.notify()
        self.process.join()
        log.info("Done")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    __enter__ = start


def loop(running, condition, events):
    try:
        import django

        os.environ["DJANGO_SETTINGS_MODULE"] = "db.settings"
        django.setup()
        from tree.models import Message

        while running[0]:
            with condition:
                condition.wait_for(lambda: events or not running[0])
                consumed = list(events)
                while events:
                    events.pop()
            delete_list = []
            create_list = []
            for topic_nodes, data, qos in consumed:
                topic = TOPIC_SEP.join(topic_nodes)
                if data is None:
                    delete_list.append(topic)
                else:
                    create_list.append(
                        Message(
                            topic=topic,
                            data=data,
                            qos=qos,
                        )
                    )
            if delete_list:
                queryset = Message.objects.filter(topic__in=delete_list)
                count, _ = queryset.delete()
            if create_list:
                Message.objects.bulk_create(
                    create_list,
                    update_conflicts=True,
                    unique_fields=["topic"],
                    update_fields=["data", "qos"],
                )
    except KeyboardInterrupt:
        pass
