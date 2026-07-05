import json
import hashlib

class IdempotencyShield:
    def __init__(self, redis_client):
        """Pass any connection-configured redis-py client driver here."""
        self.redis = redis_client

    def generate_hash(self, body_bytes: bytes) -> str:
        """Compute a deterministic SHA-256 fingerprint from raw request input bytes."""
        return hashlib.sha256(body_bytes or b"").hexdigest()

    def process_request(self, key: str, body_bytes: bytes) -> dict:
        """
        Evaluate structural tracking signatures inside Redis memory space.
        Returns a decision dictionary establishing downstream framework behavior.
        """
        request_hash = self.generate_hash(body_bytes)
        initial_state = {"status": "STARTED", "request_hash": request_hash}
        
        # Atomic lock assignment
        is_new = self.redis.setnx(key, json.dumps(initial_state))
        self.redis.expire(key, 120)  # 2-minute short-circuit security TTL

        if not is_new:
            cached_raw = self.redis.get(key)
            cached_data = json.loads(cached_raw) if cached_raw else {}

            if cached_data.get("request_hash") != request_hash:
                return {"action": "REJECT_TAMPERED"}
            if cached_data.get("status") == "STARTED":
                return {"action": "REJECT_CONCURRENT"}
            if cached_data.get("status") == "COMPLETED":
                return {"action": "SERVE_CACHE", "data": cached_data.get("response")}

        return {"action": "PROCEED", "request_hash": request_hash}

    def commit_success(self, key: str, request_hash: str, response_data: dict):
        """Finalize state properties following a completely successful route process pipeline."""
        final_payload = {
            "status": "COMPLETED",
            "request_hash": request_hash,
            "response": response_data
        }
        self.redis.setex(key, 86400, json.dumps(final_payload))

    def rollback_lock(self, key: str):
        """Evict processing markers if backend router logic drops execution exceptions."""
        self.redis.delete(key)