"""
Capture Nonce Service — Single-use HMAC-SHA256 signed nonces for live camera attestation.

Nonces are generated via GET /api/v1/auth/capture-nonce, valid for 120 seconds,
and consumed (deleted from Redis) upon first validation. This ensures that media
submitted with a valid nonce was captured live, not recycled from storage.
"""

import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.config import settings

# Attempt Redis import — degrade gracefully in dev without Redis
try:
    from app.api.dependencies import redis_client
    _REDIS_AVAILABLE = True
except Exception:
    redis_client = None
    _REDIS_AVAILABLE = False


NONCE_TTL_SECONDS = 120


class NonceService:
    """Manages single-use capture nonces backed by HMAC and Redis/in-memory storage."""

    def __init__(self):
        self.secret = settings.capture_nonce_secret.encode("utf-8")
        # In-memory storage fallback for dev / offline Redis
        self._active_nonces: dict[str, dict] = {}
        self._consumed_nonces: dict[str, float] = {}

    def _cleanup_expired(self):
        """Purge expired nonces from in-memory fallback stores."""
        now = time.time()
        expired_keys = [k for k, v in self._active_nonces.items() if v.get("expires_at", 0) < now]
        for k in expired_keys:
            self._active_nonces.pop(k, None)

        consumed_expired = [k for k, t in self._consumed_nonces.items() if now - t > NONCE_TTL_SECONDS * 2]
        for k in consumed_expired:
            self._consumed_nonces.pop(k, None)

    def generate_nonce(self) -> dict:
        """
        Generate a signed single-use capture nonce.

        Returns:
            dict with 'nonce', 'expires_at' (ISO timestamp), and 'ttl_seconds'.
        """
        self._cleanup_expired()
        nonce_id = uuid.uuid4().hex
        issued_at = int(time.time())
        expires_at = issued_at + NONCE_TTL_SECONDS

        # Create HMAC signature over nonce_id + issued_at
        payload = f"{nonce_id}:{issued_at}"
        signature = hmac.new(self.secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()

        # Token format: <nonce_id>_<issued_at>.<signature> (preserves 2-part format with embedded timestamp)
        nonce_token = f"{nonce_id}_{issued_at}.{signature}"

        nonce_record = {
            "nonce_id": nonce_id,
            "signature": signature,
            "issued_at": issued_at,
            "expires_at": expires_at,
            "consumed": False,
        }

        # Store in local memory store
        self._active_nonces[nonce_id] = nonce_record

        # Store in Redis with TTL for distributed single-use enforcement
        if _REDIS_AVAILABLE and redis_client:
            try:
                redis_key = f"capture_nonce:{nonce_id}"
                redis_client.setex(
                    redis_key,
                    NONCE_TTL_SECONDS,
                    json.dumps(nonce_record),
                )
            except Exception as e:
                print(f"[NonceService] Redis store warning: {e}")

        expires_dt = datetime.fromtimestamp(expires_at, tz=timezone.utc)

        return {
            "nonce": nonce_token,
            "expires_at": expires_dt.isoformat(),
            "ttl_seconds": NONCE_TTL_SECONDS,
        }

    def validate_nonce(self, nonce_token: Optional[str], client_timestamp: Optional[str] = None) -> bool:
        """
        Validate and consume a capture nonce. Returns True if the nonce is valid,
        has a genuine cryptographic HMAC signature, is within TTL, and was successfully consumed.
        Returns False on any forgery, expiration, or replay.
        """
        if not nonce_token or not isinstance(nonce_token, str) or not nonce_token.strip():
            return False

        self._cleanup_expired()
        token = nonce_token.strip()

        nonce_id = None
        issued_at: Optional[int] = None
        submitted_signature = None

        # Parse token
        if "." in token:
            parts = token.split(".")
            if len(parts) == 2:
                left, submitted_signature = parts[0], parts[1]
                if "_" in left:
                    sub_parts = left.split("_", 1)
                    nonce_id = sub_parts[0]
                    try:
                        issued_at = int(sub_parts[1])
                    except (ValueError, TypeError):
                        return False
                else:
                    nonce_id = left
            elif len(parts) == 3:
                nonce_id, ts_str, submitted_signature = parts[0], parts[1], parts[2]
                try:
                    issued_at = int(ts_str)
                except (ValueError, TypeError):
                    return False
            else:
                return False
        else:
            return False

        if not nonce_id or not submitted_signature:
            return False

        # Replay check: has this nonce already been consumed?
        if nonce_id in self._consumed_nonces:
            return False

        now = time.time()

        # If issued_at is embedded, verify cryptographically immediately
        if issued_at is not None:
            # Check clock skew and expiry
            if issued_at > now + 10:  # More than 10s in future
                return False
            if now - issued_at > NONCE_TTL_SECONDS:
                return False

            payload = f"{nonce_id}:{issued_at}"
            expected_sig = hmac.new(self.secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected_sig, submitted_signature):
                return False
        else:
            # If no embedded timestamp, lookup in in-memory store or Redis
            record = self._active_nonces.get(nonce_id)
            if not record and _REDIS_AVAILABLE and redis_client:
                try:
                    redis_key = f"capture_nonce:{nonce_id}"
                    stored = redis_client.get(redis_key)
                    if stored:
                        record = json.loads(stored)
                except Exception:
                    pass

            if not record:
                return False

            if record.get("consumed"):
                return False

            if record.get("expires_at", 0) < now:
                return False

            if not hmac.compare_digest(record.get("signature", ""), submitted_signature):
                return False

        # Check Redis if available for distributed consumption
        if _REDIS_AVAILABLE and redis_client:
            try:
                redis_key = f"capture_nonce:{nonce_id}"
                stored = redis_client.get(redis_key)
                if stored:
                    data = json.loads(stored)
                    if data.get("consumed"):
                        return False
                    redis_client.delete(redis_key)
            except Exception as e:
                print(f"[NonceService] Redis validation check warning: {e}")

        # Mark as consumed in local replay cache (single-use enforcement)
        self._consumed_nonces[nonce_id] = now
        self._active_nonces.pop(nonce_id, None)

        return True

    def classify_media_source(self, nonce_token: Optional[str], client_timestamp: Optional[str] = None) -> str:
        """
        Classify the media source based on nonce validation.

        Returns:
            'live_camera' if valid nonce, 'gallery_unverified' otherwise.
        """
        if self.validate_nonce(nonce_token, client_timestamp):
            return "live_camera"
        return "gallery_unverified"


# Module-level singleton
nonce_service = NonceService()
