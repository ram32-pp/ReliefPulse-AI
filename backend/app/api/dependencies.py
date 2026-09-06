from fastapi import Header, HTTPException, Depends, Request
from firebase_admin import auth, credentials
import firebase_admin
from app.config import settings
from redis import Redis
import json
import time
from typing import Dict

if settings.firebase_credentials_json and not firebase_admin._apps:
    try:
        cred = credentials.Certificate(json.loads(settings.firebase_credentials_json))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        pass  # Handle gracefully in dev without full creds

redis_client = Redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=0.05,
    socket_timeout=0.05,
)
_redis_reachable = None
_in_memory_device_limits: Dict[str, float] = {}

async def verify_firebase_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        if settings.fastapi_env == "development":
            return {"uid": "dev_user", "phone_number": "+1234567890"}
        raise HTTPException(status_code=401, detail="Invalid token format")
    
    token = authorization.split("Bearer ")[1]
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def device_rate_limit(window_seconds: int = 180, max_requests: int = 1):
    """
    Enforces strict rate limiting: 1 report / 3 minutes / device using device fingerprint & IP tracking.
    Zero-login compatible. Uses Redis with in-memory TTL fallback.
    """
    async def dependency(request: Request):
        # Extract device identifier or client IP
        device_id = (
            request.headers.get("X-Device-ID")
            or request.headers.get("X-Device-Fingerprint")
            or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or (request.client.host if request.client else "unknown_client")
        )
        key = f"rate_limit:device:{device_id}"
        now = time.time()

        # 1. Try Redis if reachable
        global _redis_reachable
        if _redis_reachable is not False:
            try:
                current = redis_client.get(key)
                _redis_reachable = True
                if current and int(current) >= max_requests:
                    ttl = redis_client.ttl(key)
                    remaining = ttl if ttl > 0 else window_seconds
                    raise HTTPException(
                        status_code=429,
                        detail=f"Rate limit exceeded: 1 emergency report per 3 minutes per device. Please wait {remaining} seconds before submitting again."
                    )
                pipe = redis_client.pipeline()
                pipe.incr(key)
                if not current:
                    pipe.expire(key, window_seconds)
                pipe.execute()
                return device_id
            except HTTPException:
                raise
            except Exception:
                _redis_reachable = False

        # 2. In-memory fallback
        # Clean expired timestamps
        expired = [k for k, exp in _in_memory_device_limits.items() if exp < now]
        for k in expired:
            _in_memory_device_limits.pop(k, None)

        last_exp = _in_memory_device_limits.get(device_id)
        if last_exp and last_exp > now:
            remaining = int(last_exp - now)
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: 1 emergency report per 3 minutes per device. Please wait {remaining} seconds before submitting again."
            )

        _in_memory_device_limits[device_id] = now + window_seconds
        return device_id

    return dependency


def rate_limit(key_prefix: str, limit: int = 1, window: int = 180):
    """Backwards-compatible wrapper delegating to device_rate_limit for unauthenticated routes."""
    return device_rate_limit(window_seconds=window, max_requests=limit)
