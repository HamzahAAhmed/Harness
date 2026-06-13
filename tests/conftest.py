import socket
from datetime import date

import pytest

from journey.models import TripPreferences, TripRequest


@pytest.fixture(autouse=True)
def block_live_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Automated tests must not make live network requests.")

    monkeypatch.setattr(socket.socket, "connect", blocked)


@pytest.fixture
def trip_request() -> TripRequest:
    return TripRequest(destination="Austin, Texas", start_date=date(2026, 7, 1), end_date=date(2026, 7, 1), travelers=2, budget=300, preferences=TripPreferences(interests=["Food", "Art"], pace="relaxed"))
