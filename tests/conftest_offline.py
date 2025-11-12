from tests.conftest import BaseTest
import pytest
from tools.geolocalisation import Geolocalisation
import socket

@pytest.mark.offline_simulation
class OfflineTestClass(BaseTest):
    def no_internet(*args, **kwargs):
        raise RuntimeError("No internet access during this test!")

    @pytest.fixture(autouse=True)
    def no_network(self, monkeypatch):
        monkeypatch.setattr(socket, "socket", self.no_internet)
