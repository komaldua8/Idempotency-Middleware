from functools import wraps
from fastapi import Request
from fastapi.responses import JSONResponse
from app.core.shield_core import IdempotencyShield

def fastapi_idempotent(shield: IdempotencyShield):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Resolve FastAPI's Request parameter instantiation mapping
            request: Request = kwargs.get("request") or next((a for a in args if isinstance(a, Request)), None)
            if not request:
                raise RuntimeError(f"Endpoint '{func.__name__}' must include an explicit 'request: Request' parameter.")

            key = request.headers.get("X-Idempotency-Key")
            if not key:
                return JSONResponse(status_code=400, content={"error": "Missing Required X-Idempotency-Key Header"})

            body_bytes = await request.body()
            
            # Reset ASGI stream tracker position context
            async def receive(): return {"type": "http.request", "body": body_bytes, "more_body": False}
            request._receive = receive

            # Execute Core Logic Audit Process Flow
            decision = shield.process_request(key, body_bytes)
            action = decision["action"]

            if action == "REJECT_TAMPERED":
                return JSONResponse(status_code=422, content={"error": "Idempotency Key Conflict: Request body mismatch."})
            if action == "REJECT_CONCURRENT":
                return JSONResponse(status_code=409, content={"error": "A request with this key is already in progress."})
            if action == "SERVE_CACHE":
                return JSONResponse(status_code=200, content={"_source": "idempotency_cache", "data": decision["data"]})

            try:
                result = await func(*args, **kwargs)
                shield.commit_success(key, decision["request_hash"], result)
                return result
            except Exception as e:
                shield.rollback_lock(key)
                raise e
        return wrapper
    return decorator