import json
import logging
import uuid
from functools import wraps
from typing import Any, Callable, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.core.redis import get_redis_client

logger = logging.getLogger("uvicorn.error")


class CacheService:
    """Helper service for Redis caching operations with JSON serialization support."""

    def __init__(self, client: Optional[Redis] = None):
        self._client = client

    @property
    def client(self) -> Optional[Redis]:
        return self._client or get_redis_client()

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve and JSON-deserialize value by key."""
        client = self.client
        if not client:
            return None
        try:
            val = await client.get(key)
            if val is None:
                return None
            return json.loads(val)
        except Exception as e:
            logger.warning("Cache GET failed for key '%s': %s", key, e)
            return None

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = 300) -> bool:
        """JSON-serialize and store value with optional TTL (seconds)."""
        client = self.client
        if not client:
            return False
        try:
            serialized = json.dumps(value, default=str)
            if ttl_seconds:
                await client.setex(key, ttl_seconds, serialized)
            else:
                await client.set(key, serialized)
            return True
        except Exception as e:
            logger.warning("Cache SET failed for key '%s': %s", key, e)
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        client = self.client
        if not client:
            return False
        try:
            await client.delete(key)
            return True
        except Exception as e:
            logger.warning("Cache DELETE failed for key '%s': %s", key, e)
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern (e.g. 'users:*') non-blockingly using scan_iter."""
        client = self.client
        if not client:
            return 0
        try:
            total_deleted = 0
            keys_to_delete = []

            # Non-blocking scan_iter for production; fallback to keys() if mock lacks scan_iter
            if hasattr(client, "scan_iter"):
                async for key in client.scan_iter(match=pattern, count=100):
                    keys_to_delete.append(key)
                    if len(keys_to_delete) >= 500:
                        total_deleted += await client.delete(*keys_to_delete)
                        keys_to_delete.clear()
                if keys_to_delete:
                    total_deleted += await client.delete(*keys_to_delete)
            else:
                keys = await client.keys(pattern)
                if keys:
                    total_deleted = await client.delete(*keys)

            return total_deleted
        except Exception as e:
            logger.warning(
                "Cache DELETE_PATTERN failed for pattern '%s': %s", pattern, e
            )
            return 0

    async def invalidate_prefix(self, prefix: str) -> int:
        """Invalidate all route caches starting with prefix (e.g. 'roles', 'users')."""
        return await self.delete_pattern(f"route_cache:*{prefix}*")


cache_service = CacheService()


def cache_response(
    ttl_seconds: int = 300, key_prefix: Optional[str] = None
) -> Callable:
    """Decorator for caching route responses in Redis.

    Usage:
        @router.get("/items")
        @cache_response(ttl_seconds=60, key_prefix="items")
        async def get_items(role_id: uuid.UUID):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            client = get_redis_client()
            if not client:
                return await func(*args, **kwargs)

            # Locate Request object from kwargs or positional args if present
            request: Optional[Request] = kwargs.get("request")
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            prefix = key_prefix or func.__name__

            if request:
                query_str = str(request.query_params)
                tenant_id = getattr(getattr(request, "state", None), "tenant_id", None)
                tenant_prefix = f":tenant:{tenant_id}" if tenant_id else ""
                cache_key = f"route_cache:{prefix}{tenant_prefix}:{request.url.path}:{query_str}"
            else:
                # Build cache key from primitive route parameters (UUID, int, str, bool, etc.)
                serializable_params = []
                for k, v in sorted(kwargs.items()):
                    if isinstance(v, (str, int, float, bool, uuid.UUID, type(None))):
                        serializable_params.append(f"{k}={v}")
                param_str = "&".join(serializable_params)
                cache_key = f"route_cache:{prefix}:{func.__module__}.{func.__qualname__}:{param_str}"

            try:
                cached_data = await client.get(cache_key)
                if cached_data:
                    logger.info("Cache HIT [key=%s]", cache_key)
                    parsed = json.loads(cached_data)
                    return JSONResponse(
                        content=parsed.get("content"),
                        status_code=parsed.get("status_code", 200),
                        headers={"X-Cache": "HIT"},
                    )
            except Exception as e:
                logger.warning("Error reading from route cache: %s", e)

            logger.info("Cache MISS [key=%s] - executing handler", cache_key)

            # Execute route handler
            res = await func(*args, **kwargs)

            # Extract content and status code
            try:
                status_code = 200
                content = res

                if isinstance(res, Response):
                    status_code = res.status_code
                    if hasattr(res, "body"):
                        content = json.loads(res.body.decode("utf-8"))
                elif hasattr(res, "model_dump"):
                    content = res.model_dump(mode="json")
                elif isinstance(res, (dict, list)):
                    content = res

                cache_payload = {"status_code": status_code, "content": content}
                await client.setex(
                    cache_key, ttl_seconds, json.dumps(cache_payload, default=str)
                )
            except Exception as e:
                logger.warning("Error saving route response to cache: %s", e)

            return res

        return wrapper

    return decorator
