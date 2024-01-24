import dataclasses

import mock
import pytest

from broker.broker import Broker
from models.client import Client
from tree.manager import PersistenceManager
from servers.server import Server


@pytest.fixture
def broker():
    return Broker()


@pytest.fixture
def mock_broadcast_queue(broker):
    broker.broadcast_queue.put([("the_topic", b"message_bytes", 0)])
    return broker.broadcast_queue


@pytest.fixture
def patch_process_row__stop_server(broker):
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


@dataclasses.dataclass
class MockClient(Client):
    send_message = print
    id: str


@pytest.fixture
def patched_client_send_message():
    with mock.patch.object(MockClient, "send_message") as patched:
        yield patched


@pytest.fixture
def mock_client1():
    return MockClient(id="test_client_1")


@pytest.fixture
def mock_client2():
    return MockClient(id="test_client_2")


@pytest.fixture
def patched_create_messages():
    target = "protocols.create_messages_for_subscriptions.create_messages_for_subscriptions"
    with mock.patch(target) as patched:
        yield patched
