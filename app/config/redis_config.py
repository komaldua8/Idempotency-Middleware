import redis

REDIS_HOST="localhost"
REDIS_PORT="6379"

redis_client=redis.Redis.from_url(
    f"redis://{REDIS_HOST}:{REDIS_PORT}",
    decode_responses=True #Automatically converts bytes into python strings
)

def get_redis_client():
    return redis_client