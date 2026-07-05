from functools import wraps
from flask import request, jsonify, make_response
from app.core.shield_core import IdempotencyShield

def flask_idempotent(shield: IdempotencyShield):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = request.headers.get("X-Idempotency-Key")
            if not key:
                return make_response(jsonify({"error": "Missing Required X-Idempotency-Key Header"}), 400)

            # Extract Synchronous Flask execution network byte streams
            body_bytes = request.get_data()

            # Execute Core Logic Audit Process Flow
            decision = shield.process_request(key, body_bytes)
            action = decision["action"]

            if action == "REJECT_TAMPERED":
                return make_response(jsonify({"error": "Idempotency Key Conflict: Request body mismatch."}), 422)
            if action == "REJECT_CONCURRENT":
                return make_response(jsonify({"error": "A request with this key is already in progress."}), 409)
            if action == "SERVE_CACHE":
                return make_response(jsonify({"_source": "idempotency_cache", "data": decision["data"]}), 200)

            try:
                result = func(*args, **kwargs)
                shield.commit_success(key, decision["request_hash"], result)
                return result
            except Exception as e:
                shield.rollback_lock(key)
                raise e
        return wrapper
    return decorator