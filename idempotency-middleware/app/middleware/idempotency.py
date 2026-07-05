import json
import hashlib
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from app.config.redis_config import get_redis_client

redis_client = get_redis_client()

async def idempotency_middleware(request: Request, call_next):
    if request.method != "POST":
        return await call_next(request)

    idempotency_key = request.headers.get("X-Idempotency-Key")
    if not idempotency_key:
        return JSONResponse(
            status_code=400, 
            content={"error": "Missing Required X-Idempotency-Key Header"}
        )

    # GENERATE PAYLOAD FINGERPRINT 
    # We read the raw body bytes to generate a unique cryptographic hash
    body_bytes = await request.body()
    request_hash = hashlib.sha256(body_bytes).hexdigest()

    # Reconstruct the request stream so the endpoint router can still read it
    async def receive():
        return {"type": "http.request", "body": body_bytes, "more_body": False}
    request._receive = receive

    #ATOMIC LOCKING WITH PAYLOAD FINGERPRINT
    initial_state = {
        "status": "STARTED",
        "request_hash": request_hash
    }
    
    is_new_request = redis_client.setnx(idempotency_key, json.dumps(initial_state))
    redis_client.expire(idempotency_key, 120) 

    if not is_new_request:
        cached_raw = redis_client.get(idempotency_key)
        cached_data = json.loads(cached_raw) if cached_raw else {}

        # Did the payload change for the same key?
        if cached_data.get("request_hash") != request_hash:
            print(f"🛑 Security Alert! Payload mismatch detected for key: {idempotency_key}")
            return JSONResponse(
                status_code=422,
                content={"error": "Idempotency Key Conflict: Request body does not match the original request."}
            )

        # In-flight
        if cached_data.get("status") == "STARTED":
            return JSONResponse(
                status_code=409,
                content={"error": "A request with this idempotency key is already in progress."}
            )
        
        # Cache Hit
        if cached_data.get("status") == "COMPLETED":
            return JSONResponse(
                status_code=200, 
                content={"_source": "idempotency_cache", "data": cached_data.get("response")}
            )

    # PROCESSING PATH 
    try:
        response = await call_next(request)
        
        if response.status_code == 200:
            response_body = [chunk async for chunk in response.body_iterator]
            response.body_iterator = iterate_chunks(response_body)
            
            res_bytes = b"".join(response_body)
            body_json = json.loads(res_bytes.decode("utf-8"))
            
            final_payload = {
                "status": "COMPLETED",
                "request_hash": request_hash, 
                "response": body_json
            }
            redis_client.setex(idempotency_key, 86400, json.dumps(final_payload))
        else:
            redis_client.delete(idempotency_key)
            
        return response

    except Exception as e:
        redis_client.delete(idempotency_key)
        raise e

async def iterate_chunks(chunks):
    for chunk in chunks:
        yield chunk