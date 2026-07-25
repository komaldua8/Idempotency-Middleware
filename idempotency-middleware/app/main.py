from fastapi import FastAPI
from app.routers import payments

app = FastAPI(title="Idempotency Middleware Engine")

app.include_router(payments.router)

@app.on_event("startup")
async def startup_event():
    from app.config.redis_config import get_redis_client
    try:
        client = get_redis_client()
        if client.ping():
            print("🚀 Successfully connected to Redis!")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")