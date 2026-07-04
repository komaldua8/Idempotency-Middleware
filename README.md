# Idempotency Middleware Engine

An idempotency middleware engine built with **FastAPI** and **Redis**. This system guarantees that identical API requests are processed safely exactly once—preventing double-charging in payment processing, eliminating distributed concurrent race conditions, and defending against payload hijacking.

## 🏗️ Architecture & Core Mechanics

The engine handles incoming `POST` requests by shifting tracking keys through an atomic lifecycle state machine inside Redis.

### The 3 States of an Idempotency Key
1. **`STARTED` (In-Flight Lock):** The first request is currently executing slow downstream code (e.g., a payment gateway). Concurrent duplicates are blocked.
2. **`COMPLETED` (Finalized Cache):** The transaction succeeded, and the final response payload is cached safely for 24 hours.
3. **`DELETED` (Auto-Recovery):** If the server crashes mid-execution or downstream services throw an error, the lock is automatically expunged so the client can try again.

---

##  Step-by-Step Code Walkthrough

The core system logic resides in `app/middleware/idempotency.py`. Here is how the engineering blocks operate under the hood:

### 1. Cryptographic Payload Fingerprinting
To prevent a client from reusing an old idempotency token to send different transaction parameters (e.g., shifting the cost from $10 to $999), we read the raw body bytes and compute a deterministic SHA-256 fingerprint:
```
body_bytes = await request.body()
request_hash = hashlib.sha256(body_bytes).hexdigest()
```

###2. The Stream Rewind Solution
Because ASGI request bodies are network streams, reading the body consumes it. If left unhandled, your core routers would receive an empty body. We patch the private communication layer of the request object to reset the stream point:
```
async def receive():
    return {"type": "http.request", "body": body_bytes, "more_body": False}
request._receive = receive
```
3. Distributed Atomic Locking via Redis
To prevent race conditions, we utilize Redis's atomic setnx (Set if Not Exists) function. If two requests hit at the exact same millisecond, only one wins the boolean flag. We also apply an explicit 2-minute short TTL to prevent permanent deadlock conditions if the server loses power during processing:
