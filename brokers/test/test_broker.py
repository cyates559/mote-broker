class TestMainLoop:
    def test_startup_shutdown(
        self,
        broker,
        patched_load_tree,
        patched_start_persistence_manager,
        patched_stop_persistence_manager,
        patched_start_server,
        patched_stop_server,
        patch_process_row_stop_server,
        mock_broadcast_queue,
    ):
        """
        Load the tree first, start the persistence manager, the tcp_server, and
        the websocket_server, run the broker, then close everything in reverse order
        """
        broker.main_loop()
        patched_load_tree.assert_called_once()
        patched_start_persistence_manager.assert_called_once()
        assert patched_start_server.call_count == 2
        patch_process_row_stop_server.assert_called_once()
        assert patched_stop_server.call_count == 2
        patched_stop_persistence_manager.assert_called_once()
