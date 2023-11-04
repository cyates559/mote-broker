from pytest import mark
from brokers.broker import Broker


class TestStartup:
    @mark.asyncio
    async def test_startup(self, mock_persistence_manager):
        b = Broker()
        b.start_main_task()
        mock_persistence_manager["load_tree"].assert_called_once()
        mock_persistence_manager["start"].assert_called_once()
