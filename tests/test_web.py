import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from futbin_sdk.web import Lookup, app, relevance


def test_relevance_accents_and_surname():
    kylian = {"name": "Kylian Mbappé", "rating": 91}
    ethan = {"name": "Ethan Mbappé", "rating": 74}
    assert relevance(kylian, "mbappe") > relevance(ethan, "mbappe")
    assert relevance(kylian, "kylian mbappe")[0] == 5


async def test_cache_coalesces_requests():
    lookup = Lookup(None)
    calls = 0

    async def fetch():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return {"price": 123}

    results = await asyncio.gather(*(lookup.cached("same", fetch) for _ in range(10)))
    assert calls == 1
    assert all(r == {"price": 123} for r in results)
    assert await lookup.cached("same", fetch) == {"price": 123}
    assert calls == 1


async def test_failed_requests_are_not_cached():
    lookup = Lookup(None)

    async def fail():
        raise TimeoutError()

    with pytest.raises(TimeoutError):
        await lookup.cached("fail", fail)
    assert not lookup.pending
    assert not lookup.cache


def test_routes_validation_and_upstream_failure():
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert client.get("/api/search?q=a").status_code == 422
        assert client.get("/api/prices/8?platform=bad").status_code == 422
        assert client.get("/api/prices/-1").status_code == 400

        async def fail(query):
            raise httpx.ConnectError("offline")

        app.state.lookup.search = fail
        response = client.get("/api/search?q=mbappe")
        assert response.status_code == 502
        assert "FUTBIN" in response.json()["detail"]
