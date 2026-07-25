import asyncio
import random
from fastapi import APIRouter, Request
from app.config.redis_config import get_redis_client
from app.core.shield_core import IdempotencyShield
from app.adapters.fastapi_adapter import fastapi_idempotent

router = APIRouter(prefix="/api/v1")

# Initialize engine instances
redis_client = get_redis_client()
shield_engine = IdempotencyShield(redis_client)

@router.post("/payments")
@fastapi_idempotent(shield_engine) # 👈 Decorator attached here
async def create_payment(payload: dict, request: Request): # 👈 Added 'request: Request'
    await asyncio.sleep(2)
    transaction_id = f"tx_mock_{random.randint(4400000000, 4499999999)}"
    return {
        "success": True,
        "amount": payload.get("amount"),
        "transaction_id": transaction_id
    }