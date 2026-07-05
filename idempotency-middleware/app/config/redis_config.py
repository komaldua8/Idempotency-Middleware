import redis

_redis_client = None

def get_redis_client(redis_url: str = "redis://localhost:6379/0"):
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(redis_url, decode_responses=True)
    return _redis_client