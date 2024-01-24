import pytest


class TestMainLoop:
    def test_main_loop(
        self,
        broker,
        patched_load_tree,
        patched_start_persistence_manager,
        patched_stop_persistence_manager,
        patched_start_server,
        patched_stop_server,
        patch_process_row__stop_server,
        mock_broadcast_queue,
    ):
        """
        Load the tree first, start the persistence manager, the tcp_server, and
        the websocket_server, run the broker, then close everything in reverse order
        """
        broker.main_loop()
        assert patched_load_tree.call_count == 1
        assert patched_start_persistence_manager.call_count == 1
        assert patched_start_server.call_count == 2
        assert patch_process_row__stop_server.call_count == 1
        assert patched_stop_server.call_count == 2
        assert patched_stop_persistence_manager.call_count == 1


class TestAddRemoveClient:
    def test_add_client(
        self,
        broker,
        mock_client1,
    ):
        """
        Adds a client to the list of connected clients
        """
        broker.add_client(mock_client1)
        assert list(broker.clients.values()) == [mock_client1]

    def test_remove_client(
        self,
        broker,
        mock_client1,
    ):
        """
        Removes a client from the list of connected clients
        """
        broker.add_client(mock_client1)
        broker.remove_client(mock_client1)
        assert list(broker.clients.values()) == []

    def test_remove_client_fail(
        self,
        broker,
        mock_client1,
    ):
        """
        Raise KeyError if the client is not found
        """
        with pytest.raises(KeyError):
            broker.remove_client(mock_client1)


class TestProcessRows:
    def test_process_rows(self, patched_create_messages):
        pass