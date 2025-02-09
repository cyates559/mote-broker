import os
from functools import cached_property

from backends.manager import ProcessManager
from backends.worker import ProcessWorker
from logger import log
from models.messages import IncomingMessage, OutgoingMessage
from models.topic import TOPIC_SEP, Topic
from protocols.filter_tree import filter_tree_with_topic
from utils.recursive_default_dict import RecursiveDefaultDict
from utils.tree_item import TreeItem


class TreeWorker(ProcessWorker):
    """
    Runs inside its own process, writes data to the database.
    """
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
        print("MESG",messages)
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
    """
    Holds the entire tree in memory, gives tasks to the TreeWorker to run.
    """
    tree: RecursiveDefaultDict = None
    worker_class = TreeWorker

    def preload(self):
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
        self.tree = results

    def retain_rows(self, rows: list):
        print("RR", rows)
        self.add_tasks(*rows)
        for topic_nodes, data, _ in rows:
            branch = self.tree / topic_nodes
            if branch is not None:
                branch.leaf = data

    def process_message(self, message: IncomingMessage) -> list:
        if message.graft:
            rows = message.flatten_into_rows(self.tree)
        else:
            rows = message.get_applicable_rows(self.tree)
        self.retain_rows(rows)
        return rows

    def filter(self, topic: Topic) -> TreeItem:
        return filter_tree_with_topic(
            topic=topic.node_list,
            tree=self.tree,
        )

    def get_message(self, topic: Topic, qos: int) -> OutgoingMessage:
        tree_item = self.filter(topic)
        return OutgoingMessage.from_tree_item(
            topic=topic.full_str,
            qos=qos,
            tree_item=tree_item,
        )
