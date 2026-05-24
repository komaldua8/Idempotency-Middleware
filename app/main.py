from fastapi import FastAPI
from app.config.redis_config import get_redis_client

app= FastAPI(title = "Idempotency Middleware Engine")

@app.on_event("startup")
async def startup_event():
    try:
        client=get_redis_client()
        if client.ping():
            print("Successfully conected to Docker Redis Engine")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")

@app.get("/")
def read_root():
    return {"message": "Idempotency API Engine is live"}