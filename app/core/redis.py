import logging
from typing import AsyncGenerator, Optional

from redis.asyncio import Redis, from_url

from app.core.config import settings

logger = logging.getLogger("uvicorn.error")

redis_client: Optional[Redis] = None


async def init_redis() -> Optional[Redis]:
    """Initialize Redis connection pool on application startup."""
    global redis_client
    try:
        redis_client = from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=2.0,
            socket_connect_timeout=3.0,
            max_connections=50,
            health_check_interval=30,
            retry_on_timeout=True,
        )
        # Test connection ping
        await redis_client.ping()
        logger.info("Successfully connected to Redis at %s", settings.REDIS_URL)
        return redis_client
    except Exception as e:
        logger.warning(
            "Redis connection failed (%s). App will continue with fallback/mock caching.",
            e,
        )
        redis_client = None
        return None


async def close_redis() -> None:
    """Close Redis connection pool on application shutdown."""
    global redis_client
    if redis_client:
        try:
            await redis_client.aclose()
            logger.info("Redis connection closed gracefully.")
        except Exception as e:
            logger.error("Error closing Redis connection: %s", e)
        finally:
            redis_client = None


def get_redis_client() -> Optional[Redis]:
    """Get the active initialized Redis client instance."""
    return redis_client


async def get_redis() -> AsyncGenerator[Optional[Redis], None]:
    """FastAPI Dependency for accessing Redis client instance."""
    yield redis_client
