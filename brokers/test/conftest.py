from queue import Queue

import mock
import pytest

from brokers.broker import Broker
from persistence.manager import PersistenceManager
from servers.server import Server


@pytest.fixture
def broker():
    return Broker()


@pytest.fixture
def mock_broadcast_queue(broker):
    broker.broadcast_queue.put([("the_topic", b"message_bytes", 0)])
    return broker.broadcast_queue


@pytest.fixture
def patch_process_row_stop_server(broker):
    def process_rows(*_):
        broker.running = False

    with mock.patch.object(Broker, "process_rows", wraps=process_rows) as patched:
        yield patched


@pytest.fixture
def patched_load_tree():
    with mock.patch.object(PersistenceManager, "load_tree") as patched:
        yield patched


@pytest.fixture
def patched_start_persistence_manager():
    with mock.patch.object(PersistenceManager, "__enter__") as patched:
        yield patched


@pytest.fixture
def patched_stop_persistence_manager():
    with mock.patch.object(PersistenceManager, "__exit__") as patched:
        yield patched


@pytest.fixture
def patched_start_server():
    with mock.patch.object(Server, "__enter__") as patched:
        yield patched


@pytest.fixture
def patched_stop_server():
    with mock.patch.object(Server, "__exit__") as patched:
        yield patched
