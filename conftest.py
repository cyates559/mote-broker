from unittest.mock import patch, DEFAULT

from pytest import fixture

from persistence.manager import PersistenceManager


default_tree = {}


@fixture
def mock_persistence_manager():
    with patch.multiple(
        PersistenceManager,
        load_tree=DEFAULT,
        retain=DEFAULT,
        start=DEFAULT,
        stop=DEFAULT,
        create_loop_process=DEFAULT,
    ) as patched:
        patched["load_tree"].return_value = default_tree
        patched["create_loop_process"].return_value = "mock_loop"
        yield patched
