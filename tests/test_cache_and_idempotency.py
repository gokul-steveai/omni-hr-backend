import fnmatch

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.core.services.cache_service import CacheService, cache_response
from app.core.services.idempotency_service import IdempotencyService


class FakeAsyncRedis:
    """In-memory Redis mock for unit testing."""

    def __init__(self):
        self._store = {}

    async def get(self, name: str):
        return self._store.get(name)

    async def set(self, name: str, value: str, ex: int | None = None, nx: bool = False):
        if nx and name in self._store:
            return None
        self._store[name] = value
        return True

    async def setex(self, name: str, time: int, value: str):
        self._store[name] = value
        return True

    async def delete(self, *names: str):
        count = 0
        for n in names:
            if n in self._store:
                del self._store[n]
                count += 1
        return count

    async def keys(self, pattern: str = "*"):
        return [k for k in self._store.keys() if fnmatch.fnmatch(k, pattern)]

    async def scan_iter(self, match: str = "*", count: int = 100):
        for k in list(self._store.keys()):
            if fnmatch.fnmatch(k, match):
                yield k

    async def ping(self):
        return True

    async def aclose(self):
        pass


@pytest.fixture
def fake_redis():
    return FakeAsyncRedis()


@pytest.mark.asyncio
async def test_cache_service_crud(fake_redis):
    cache = CacheService(client=fake_redis)

    # Test Set & Get
    stored = await cache.set("user:100", {"id": 100, "name": "Alice"})
    assert stored is True

    user_data = await cache.get("user:100")
    assert user_data == {"id": 100, "name": "Alice"}

    # Test Delete
    deleted = await cache.delete("user:100")
    assert deleted is True
    assert await cache.get("user:100") is None


@pytest.mark.asyncio
async def test_cache_service_delete_pattern(fake_redis):
    cache = CacheService(client=fake_redis)

    await cache.set("dept:1:emp:1", "data1")
    await cache.set("dept:1:emp:2", "data2")
    await cache.set("dept:2:emp:3", "data3")

    deleted_count = await cache.delete_pattern("dept:1:*")
    assert deleted_count == 2
    assert await cache.get("dept:1:emp:1") is None
    assert await cache.get("dept:2:emp:3") == "data3"


@pytest.mark.asyncio
async def test_idempotency_service(fake_redis):
    idempotency = IdempotencyService(client=fake_redis)
    path = "/api/v1/payroll/process"
    key = "unique-tx-12345"

    # Test locking key
    locked_first = await idempotency.lock_key(key, path)
    assert locked_first is True

    # Test concurrent lock rejection
    locked_second = await idempotency.lock_key(key, path)
    assert locked_second is False

    # Save response
    saved = await idempotency.save_response(
        idempotency_key=key,
        path=path,
        status_code=201,
        content={"message": "Payrun processed successfully", "payrun_id": "p-99"},
    )
    assert saved is True

    # Fetch cached response
    cached_response = await idempotency.get_cached_response(key, path)
    assert cached_response is not None
    assert cached_response.status_code == 201
    assert cached_response.headers.get("X-Cache-Idempotent") == "HIT"


@pytest.mark.asyncio
async def test_route_cache_decorator(fake_redis, monkeypatch):
    import app.core.services.cache_service as cache_module

    monkeypatch.setattr(cache_module, "get_redis_client", lambda: fake_redis)

    test_app = FastAPI()
    call_count = 0

    @test_app.get("/test-cached")
    @cache_response(ttl_seconds=60, key_prefix="test")
    async def sample_endpoint(request: Request):
        nonlocal call_count
        call_count += 1
        return {"count": call_count, "status": "ok"}

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        # First call: Cache Miss
        res1 = await client.get("/test-cached")
        assert res1.status_code == 200
        assert res1.json() == {"count": 1, "status": "ok"}

        # Second call: Cache Hit (count remains 1)
        res2 = await client.get("/test-cached")
        assert res2.status_code == 200
        assert res2.headers.get("X-Cache") == "HIT"
        assert res2.json() == {"count": 1, "status": "ok"}
        assert call_count == 1


@pytest.mark.asyncio
async def test_cache_invalidation_prefix(fake_redis, monkeypatch):
    import app.core.services.cache_service as cache_module

    monkeypatch.setattr(cache_module, "get_redis_client", lambda: fake_redis)
    cache = cache_module.CacheService(client=fake_redis)

    test_app = FastAPI()
    call_count = 0

    @test_app.get("/items")
    @cache_response(ttl_seconds=60, key_prefix="items")
    async def get_items(request: Request):
        nonlocal call_count
        call_count += 1
        return {"items": ["item1", "item2"], "version": call_count}

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        # Cache initial GET
        r1 = await client.get("/items")
        assert r1.json()["version"] == 1

        # Cache HIT
        r2 = await client.get("/items")
        assert r2.headers.get("X-Cache") == "HIT"
        assert r2.json()["version"] == 1

        # Invalidate route cache
        await cache.invalidate_prefix("items")

        # Third call: Cache Miss after invalidation
        r3 = await client.get("/items")
        assert r3.headers.get("X-Cache") is None
        assert r3.json()["version"] == 2


@pytest.mark.asyncio
async def test_route_cache_without_request_param(fake_redis, monkeypatch):
    import uuid

    import app.core.services.cache_service as cache_module

    monkeypatch.setattr(cache_module, "get_redis_client", lambda: fake_redis)

    test_app = FastAPI()
    call_count = 0
    target_id = uuid.uuid4()

    @test_app.get("/roles/{role_id}/permissions")
    @cache_response(ttl_seconds=60, key_prefix="role_permissions")
    async def get_role_permissions(role_id: uuid.UUID):
        nonlocal call_count
        call_count += 1
        return {"role_id": str(role_id), "count": call_count}

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        url = f"/roles/{target_id}/permissions"

        # First GET: Cache Miss
        r1 = await client.get(url)
        assert r1.status_code == 200
        assert r1.json()["count"] == 1
        assert r1.headers.get("X-Cache") is None

        # Second GET: Cache HIT
        r2 = await client.get(url)
        assert r2.status_code == 200
        assert r2.headers.get("X-Cache") == "HIT"
        assert r2.json()["count"] == 1
        assert call_count == 1
