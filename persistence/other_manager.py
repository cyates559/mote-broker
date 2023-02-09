from collections import defaultdict
from multiprocessing import Process, Condition, Lock

import django
import os

from asgiref.sync import sync_to_async

os.environ["DJANGO_SETTINGS_MODULE"] = "db.settings"
django.setup()

from persistence.models import Message


def RecursiveDefaultDict():
    return defaultdict(RecursiveDefaultDict)


def loop():
    global events
    global running
    print("RUNNIN", running)
    while running:
        with condition:
            condition.wait_for(lambda: events or not running)
            consumed = events
            events = []
        print("EVENTS", events)
        for topic, data, qos in consumed:
            if data is None:
                Message.objects.filter(topic=topic).delete()
            else:
                Message.objects.update_or_create(
                    topic=topic,
                    defaults={"data": data, "qos": qos},
                )


condition = Condition(lock=Lock())
events = []
process = Process(target=loop)
running = False


async def get_tree_async():
    return await sync_to_async(get_tree, thread_sensitive=False)()


def get_tree() -> defaultdict:
    results = RecursiveDefaultDict()
    for message in Message.objects.all():
        split_topic = message.topic.split("/")
        pointer = results
        for node in split_topic:
            if node != "":
                pointer = pointer[node]
        pointer["/"] = message
    return results


def clear(topic: str):
    with condition:
        events.append((topic, None, 0))
        condition.notify()


def retain(topic: str, message: bytes, qos: int):
    with condition:
        events.append((topic, message, qos))
        condition.notify()


def start():
    global process
    global running
    running = True
    process.start()


def stop():
    global process
    global running
    running = False
    with condition:
        condition.notify()
    process.join()
