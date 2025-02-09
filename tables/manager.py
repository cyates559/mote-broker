import json
import os
from functools import cached_property
from typing import Callable


from backends.worker import ProcessWorker
from backends.manager import ProcessManager
from logger import log
from models.messages import OutgoingMessage
from models.topic import Topic
from tables.exceptions import UnknownOperation, InvalidPayload

operator_type = Callable[[Topic, any], None]


class TableWorker(ProcessWorker):
    models: dict = {}

    def setup(self):
        self.load_models()

    @cached_property
    def meta(self):
        import django
        os.environ["DJANGO_SETTINGS_MODULE"] = "db.settings"
        django.setup()
        from tables.models import TableMeta
        return TableMeta

    @cached_property
    def operator_map(self) -> dict[str, operator_type]:
        return {
            "@&": self.create_table,
            "@--": self.drop_table,
            "@$": self.write_objects,
        }

    def create_table(self, topic: Topic, data: bytes):
        self.meta.create_table(topic.full_str, data)

    def write_objects(self, topic: Topic, data: bytes):
        pass

    def drop_table(self, topic, data):
        log.debug("DROP", topic, data)
        if topic in self.models:
            log.debug("ACTUALLY DROP", topic)
            self.models[topic].drop()
            del self.models[topic]


    def run_tasks(self, tasks: tuple[Topic, bytes]):
        for full_topic, payload in tasks:
            self.handle_operation(full_topic, payload)

    def handle_operation(self, full_topic: Topic, payload: bytes):
        nodes = full_topic.node_list
        operator = self.operator_map.get(nodes[0])
        if operator is None:
            raise UnknownOperation
        topic = Topic.from_nodes(nodes[1:])
        try:
            return operator(topic, payload)
        except:
            log.traceback()
            return False

    def query(self, topic: str) -> bytes:
        return b"test response"

    def load_models(self):
        log.debug("LOAD ALL...")
        self.models = {
            table_data.topic: table_data.build()
            for table_data in self.meta.objects.all()
        }
        log.debug("LOADED UP")


class TableManager(ProcessManager):
    worker_class = TableWorker

    def get_message(self, topic: Topic, qos: int) -> OutgoingMessage:
        topic_str = topic.full_str
        data = self.query(topic_str)
        return OutgoingMessage(topic_str, qos, data)

