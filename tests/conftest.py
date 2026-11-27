import pytest


@pytest.fixture(autouse=True)
def isolate_request_limits(monkeypatch):
    from collections import defaultdict, deque
    import app

    monkeypatch.setattr(app, 'RATE', defaultdict(deque))
