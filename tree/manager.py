import os
from functools import cached_property

from backends.manager import ProcessManager
from backends.worker import BackendWorker
from logger import log
from models.topic import TOPIC_SEP
from utils.recursive_default_dict import RecursiveDefaultDict


class TreeWorker(BackendWorker):
    @cached_property
    def message_class(self):
        import django
        os.environ["DJANGO_SETTINGS_MODULE"] = "db.settings"
        django.setup()
        from tree.models import Message
        return Message

    def run_tasks(self, *messages: (list, bytes, int)):
        delete_list = []
        create_list = []
        for topic_nodes, data, qos in messages:
            topic = TOPIC_SEP.join(topic_nodes)
            if data is None:
                delete_list.append(topic)
            else:
                create_list.append(
                    self.message_class(
                        topic=topic,
                        data=data,
                        qos=qos,
                    )
                )
        if delete_list:
            queryset = self.message_class.objects.filter(topic__in=delete_list)
            count, _ = queryset.delete()
        if create_list:
            self.message_class.objects.bulk_create(
                create_list,
                update_conflicts=True,
                unique_fields=["topic"],
                update_fields=["data", "qos"],
            )


class TreeManager(ProcessManager):
    worker_class = TreeWorker

    @staticmethod
    def load_tree() -> RecursiveDefaultDict:
        log.info("Loading message tree...", end="")
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
        log.info("Done" )
        return results
