import logging
from typing import Optional

from redis.asyncio import Redis, from_url

from app.core.config import settings

logger = logging.getLogger("uvicorn.error")

redis_client: Optional[Redis] = None


async def init_redis() -> Optional[Redis]:
    """Initialize Redis connection pool on application startup."""
    global redis_client
    client: Optional[Redis] = None
    try:
        client = from_url(
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
        await client.ping()
        redis_client = client
        logger.info("Successfully connected to Redis.")
        return redis_client
    except Exception as e:
        if client:
            try:
                await client.aclose()
            except Exception as close_err:
                logger.debug("Error closing failed Redis client: %s", close_err)
        redis_client = None
        logger.warning(
            "Redis connection failed (%s). App will continue with fallback caching.",
            e,
        )
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
