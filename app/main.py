from fastapi import FastAPI
from app.routers import payments
# FIX: Explicitly import the FUNCTION from the middleware file
from app.middleware.idempotency import idempotency_middleware

app = FastAPI(title="Idempotency Middleware Engine")

# Globally register the middleware function
@app.middleware("http")
async def add_idempotency_layer(request, call_next):
    # FIX: Make sure this calls 'idempotency_middleware', not the module name
    return await idempotency_middleware(request, call_next)

# Include the payments router explicitly
app.include_router(payments.router)

@app.on_event("startup")
async def startup_event():
    from app.config.redis_config import get_redis_client
    try:
        client = get_redis_client()
        if client.ping():
            print("🚀 Successfully connected to the Docker Redis instance!")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")