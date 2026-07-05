import json
from functools import wraps
from django.http import JsonResponse, HttpRequest
from app.core.shield_core import IdempotencyShield

def django_idempotent(shield: IdempotencyShield):
    """
    Decorator to enforce framework-agnostic idempotency on selective Django views.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 1. Ensure we are inspecting a valid Django HttpRequest object
            if not isinstance(request, HttpRequest):
                # If used on a Class-Based View method, the first arg is 'self', second is 'request'
                if args and isinstance(args[0], HttpRequest):
                    request = args[0]
                else:
                    raise RuntimeError("Django adapter could not locate the HttpRequest object.")

            # 2. Extract header (Django normalizes HTTP headers into HTTP_UPPERCASE_NAME)
            key = request.META.get("HTTP_X_IDEMPOTENCY_KEY")
            if not key:
                return JsonResponse({"error": "Missing Required X-Idempotency-Key Header"}, status=400)

            # Only intercept mutation requests
            if request.method != "POST":
                return view_func(request, *args, **kwargs)

            # 3. Extract raw body bytes from Django's request stream
            body_bytes = request.body

            # 4. Evaluate against Core Engine
            decision = shield.process_request(key, body_bytes)
            action = decision["action"]

            if action == "REJECT_TAMPERED":
                return JsonResponse({"error": "Idempotency Key Conflict: Request body mismatch."}, status=422)
            if action == "REJECT_CONCURRENT":
                return JsonResponse({"error": "A request with this key is already in progress."}, status=409)
            if action == "SERVE_CACHE":
                return JsonResponse({"_source": "idempotency_cache", "data": decision["data"]}, status=200)

            # 5. Core Execution & Exception Management Flow
            try:
                # Execute Django's underlying view function
                response = view_func(request, *args, **kwargs)
                
                # Check if the view returned a successful response layout
                if response.status_code == 200:
                    # Parse out response content safely to commit to Redis cache
                    try:
                        response_data = json.loads(response.content.decode("utf-8"))
                    except ValueError:
                        # Fallback if content isn't stringified JSON
                        response_data = response.content.decode("utf-8")

                    shield.commit_success(key, decision["request_hash"], response_data)
                else:
                    # Client or server error: instantly strip lock state
                    shield.rollback_lock(key)
                    
                return response

            except Exception as e:
                # System panic cleanup trigger
                shield.rollback_lock(key)
                raise e

        return _wrapped_view
    return decorator