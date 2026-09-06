from fastapi import APIRouter
from app.api.schemas import CaptureNonceResponse
from app.services.nonce_service import nonce_service

router = APIRouter(prefix="/auth", tags=["Auth & Attestation"])


@router.get("/capture-nonce", response_model=CaptureNonceResponse)
async def get_capture_nonce():
    """
    Generate a signed single-use capture nonce for live camera attestation.
    Valid for 120 seconds. Consumed upon first validation.
    """
    nonce_data = nonce_service.generate_nonce()
    return CaptureNonceResponse(
        nonce=nonce_data["nonce"],
        expires_at=nonce_data["expires_at"],
        ttl_seconds=nonce_data["ttl_seconds"],
    )
