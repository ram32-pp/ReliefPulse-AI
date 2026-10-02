from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.api.schemas import ReportCreate, ReportResponse, ReportStatus, TimelineStep, GPSLocation
from app.services.report_service import get_report_service, ReportService
from app.services.storage_service import storage_service
from app.api.dependencies import rate_limit, device_rate_limit
from app.i18n.messages import get_message
from datetime import datetime
from typing import Optional, List
import uuid
import json

router = APIRouter(prefix="/reports", tags=["Reports"])


def _make_display_code(report_id: uuid.UUID) -> str:
    """Generate a human-readable report code like RP-2847."""
    return f"RP-{str(report_id)[:4].upper()}"


def _build_timeline(report) -> List[TimelineStep]:
    """Build the end-to-end relief progression timeline."""
    current_status = getattr(report, "relief_status", "pending") or report.status or "pending"
    is_verified_step = current_status in ["verified", "dispatched", "en_route", "delivered", "resolved"]
    is_dispatched_step = current_status in ["dispatched", "en_route", "delivered", "resolved"]
    is_en_route_step = current_status in ["en_route", "delivered", "resolved"]
    is_delivered_step = current_status in ["delivered", "resolved"]

    return [
        TimelineStep(
            step="received",
            label_ur="SOS Bhej di gai",
            label_en="SOS Broadcast Received",
            completed=True,
            at=report.created_at,
        ),
        TimelineStep(
            step="verified",
            label_ur="AI Verification Mukammal",
            label_en="AI Verification Complete",
            completed=is_verified_step,
            at=report.created_at if is_verified_step else None,
        ),
        TimelineStep(
            step="dispatched",
            label_ur="Team Dispatch Ho Gai",
            label_en="Rescue Team Dispatched",
            completed=is_dispatched_step,
            at=None,
        ),
        TimelineStep(
            step="en_route",
            label_ur="Madad Raste Mein Hai",
            label_en="Relief En Route",
            completed=is_en_route_step,
            at=None,
        ),
        TimelineStep(
            step="delivered",
            label_ur="Madad Mil Gai",
            label_en="Relief Delivered & Safe",
            completed=is_delivered_step,
            at=None,
        ),
    ]


def _build_provenance_flags(report) -> list[str]:
    flags = []
    if getattr(report, "flag_location_spoof", False):
        flags.append("Location spoof detected: EXIF GPS discrepancy")
    if getattr(report, "flag_location_mismatch", False):
        flags.append("Location mismatch: GPS coordinates do not match reported place")
    return flags


@router.post("", response_model=ReportResponse, status_code=201, dependencies=[Depends(device_rate_limit(180, 1))])
async def submit_report_json(
    report_data: ReportCreate,
    request: Request,
    report_service: ReportService = Depends(get_report_service),
):
    """Submit a new emergency report via JSON payload. Returns HTTP 201 <300ms fast path."""
    client_ip = request.client.host if request.client else None
    report = await report_service.create_report(report_data, client_ip=client_ip)
    code = _make_display_code(report.id)

    ai_rep = getattr(report, "ai_verification_report", {}) or {}
    prov_flags = _build_provenance_flags(report)

    return ReportResponse(
        report_id=str(report.id),
        display_code=code,
        status=report.status,
        message_ur=get_message("report_received", "roman_urdu"),
        message_en=get_message("report_received", "en"),
        estimated_review_seconds=30,
        track_url=f"/status/{code}",
        parsed_text=getattr(report, "parsed_text", None) or getattr(report, "raw_input", None),
        raw_input=getattr(report, "raw_input", None),
        voice_transcript=getattr(report, "voice_transcript", None),
        acoustic_distress_level=getattr(report, "acoustic_distress_level", None),
        ai_extraction=getattr(report, "ai_extraction", None),
        semantic_score=getattr(report, "semantic_score", 0),
        consistency_score=getattr(report, "consistency_score", 0),
        grounding_score=getattr(report, "grounding_score", 10),
        cluster_score=getattr(report, "cluster_score", 5),
        verification_score=getattr(report, "verification_score", 0),
        vulnerability_level=getattr(report, "vulnerability_level", "requires_human_triage"),
        grounding_status=getattr(report, "grounding_status", "unreported_localized_incident"),
        cluster_id=getattr(report, "cluster_id", None),
        concise_report=ai_rep.get("concise_report"),
        audio_url=report.audio_url,
        grounding_label=getattr(report, "grounding_label", None),
        rubric_breakdown=getattr(report, "rubric_breakdown", None),
        provenance_flags=prov_flags,
        triage_tier=getattr(report, "triage_tier", "suspected_unconfirmed"),
        cluster_density_factor=getattr(report, "cluster_density_factor", 0.0),
        device_integrity_score=getattr(report, "device_integrity_score", 100),
        media_forensics_score=getattr(report, "media_forensics_score", 100),
        semantic_consistency_score=getattr(report, "semantic_consistency_score", 100),
        tamper_penalty=getattr(report, "tamper_penalty", 0),
        callback_status=getattr(report, "callback_status", None),
        verification_breakdown_5layer=getattr(report, "verification_breakdown_5layer", None),
    )


@router.post("/multipart", response_model=ReportResponse, status_code=201, dependencies=[Depends(device_rate_limit(180, 1))])
async def submit_report_multipart(
    request: Request,
    input_type: str = Form("voice"),
    text_input: Optional[str] = Form(None),
    text_note: Optional[str] = Form(None),
    address_text: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    hazard_types: Optional[str] = Form(None), # JSON or comma separated
    hazards: Optional[str] = Form(None),
    audio_file: Optional[UploadFile] = File(None),
    image_file: Optional[UploadFile] = File(None),
    media_source: Optional[str] = Form("voice_direct"),
    capture_nonce: Optional[str] = Form(None),
    report_service: ReportService = Depends(get_report_service),
):
    """
    Submit emergency SOS with direct voice audio (.webm, .wav, .mp3, .m4a), text, and optional media.
    Uploads media to storage and executes 5-layer verification.
    Returns HTTP 201 in <300ms fast path.
    """
    client_ip = request.client.host if request.client else None
    audio_bytes = None
    audio_url = None
    if audio_file:
        audio_bytes = await audio_file.read()
        audio_url = await storage_service.upload_bytes(
            audio_bytes,
            original_filename=audio_file.filename or "voice.webm",
            content_type=audio_file.content_type or "audio/webm",
            folder="audio",
        )

    image_bytes = None
    if image_file:
        image_bytes = await image_file.read()

    parsed_hazards = []
    raw_h = hazards or hazard_types
    if raw_h:
        try:
            parsed_hazards = json.loads(raw_h)
        except Exception:
            parsed_hazards = [h.strip() for h in raw_h.split(",") if h.strip()]

    gps_loc = None
    if latitude is not None and longitude is not None:
        gps_loc = GPSLocation(latitude=latitude, longitude=longitude)

    effective_text = text_note or text_input

    report_create = ReportCreate(
        input_type=input_type,
        text_input=effective_text,
        text_note=effective_text,
        address_text=address_text,
        latitude=latitude,
        longitude=longitude,
        gps_location=gps_loc,
        audio_blob_url=audio_url,
        hazard_types=parsed_hazards,
        hazards=parsed_hazards,
        media_source=media_source,
        capture_nonce=capture_nonce,
    )

    report = await report_service.create_report(
        report_data=report_create,
        audio_bytes=audio_bytes,
        audio_mime_type=audio_file.content_type if audio_file else "audio/webm",
        image_bytes=image_bytes,
        client_ip=client_ip,
    )

    code = _make_display_code(report.id)
    ai_rep = getattr(report, "ai_verification_report", {}) or {}
    prov_flags = _build_provenance_flags(report)

    return ReportResponse(
        report_id=str(report.id),
        display_code=code,
        status=report.status,
        message_ur=get_message("report_received", "roman_urdu"),
        message_en=get_message("report_received", "en"),
        estimated_review_seconds=30,
        track_url=f"/status/{code}",
        parsed_text=getattr(report, "parsed_text", None) or getattr(report, "raw_input", None),
        raw_input=getattr(report, "raw_input", None),
        voice_transcript=getattr(report, "voice_transcript", None),
        acoustic_distress_level=getattr(report, "acoustic_distress_level", None),
        ai_extraction=getattr(report, "ai_extraction", None),
        semantic_score=getattr(report, "semantic_score", 0),
        consistency_score=getattr(report, "consistency_score", 0),
        grounding_score=getattr(report, "grounding_score", 10),
        cluster_score=getattr(report, "cluster_score", 5),
        verification_score=getattr(report, "verification_score", 0),
        vulnerability_level=getattr(report, "vulnerability_level", "requires_human_triage"),
        grounding_status=getattr(report, "grounding_status", "unreported_localized_incident"),
        cluster_id=getattr(report, "cluster_id", None),
        concise_report=ai_rep.get("concise_report"),
        audio_url=report.audio_url,
        grounding_label=getattr(report, "grounding_label", None),
        rubric_breakdown=getattr(report, "rubric_breakdown", None),
        provenance_flags=prov_flags,
        triage_tier=getattr(report, "triage_tier", "suspected_unconfirmed"),
        cluster_density_factor=getattr(report, "cluster_density_factor", 0.0),
        device_integrity_score=getattr(report, "device_integrity_score", 100),
        media_forensics_score=getattr(report, "media_forensics_score", 100),
        semantic_consistency_score=getattr(report, "semantic_consistency_score", 100),
        tamper_penalty=getattr(report, "tamper_penalty", 0),
        callback_status=getattr(report, "callback_status", None),
        verification_breakdown_5layer=getattr(report, "verification_breakdown_5layer", None),
    )


@router.get("/latest/status", response_model=ReportStatus)
async def get_latest_report_status(
    report_service: ReportService = Depends(get_report_service),
):
    """Get the live status of the latest emergency report."""
    report = await report_service.get_report_by_display_code("latest")
    if not report:
        raise HTTPException(status_code=404, detail="No reports found")
    return _serialize_report_status(report)


@router.get("/code/{code}/status", response_model=ReportStatus)
async def get_report_status_by_code(
    code: str,
    report_service: ReportService = Depends(get_report_service),
):
    """Get the live verification and relief status timeline by display code (e.g. RP-2847)."""
    report = await report_service.get_report_by_display_code(code)
    if not report:
        raise HTTPException(status_code=404, detail="Incident report not found")

    return _serialize_report_status(report)


@router.get("/{report_id}/status", response_model=ReportStatus)
async def get_report_status(
    report_id: str,
    report_service: ReportService = Depends(get_report_service),
):
    """Get the live verification and relief status timeline for a report by UUID or code."""
    try:
        parsed_uuid = uuid.UUID(report_id)
        report = await report_service.get_report_by_id(parsed_uuid)
    except (ValueError, AttributeError):
        report = await report_service.get_report_by_display_code(report_id)

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return _serialize_report_status(report)


def _extract_lat_lng(gps_loc) -> Optional[tuple[float, float]]:
    if not gps_loc:
        return None
    import re, struct
    loc_str = str(gps_loc)
    m = re.search(r'POINT\s*\(\s*([0-9.-]+)\s+([0-9.-]+)\s*\)', loc_str, re.IGNORECASE)
    if m:
        return float(m.group(2)), float(m.group(1)) # lat, lng

    raw = getattr(gps_loc, "data", None)
    if raw is None and isinstance(gps_loc, (bytes, bytearray)):
        raw = bytes(gps_loc)
    elif raw is not None:
        raw = bytes(raw)

    if raw and len(raw) >= 21:
        try:
            endian = '<' if raw[0] == 1 else '>'
            lng, lat = struct.unpack_from(endian + 'dd', raw, offset=len(raw) - 16)
            return float(lat), float(lng)
        except Exception:
            pass
    return None


def _serialize_report_status(report) -> ReportStatus:
    timeline = _build_timeline(report)
    ai_rep = getattr(report, "ai_verification_report", {}) or {}
    prov_flags = _build_provenance_flags(report)

    # Privacy Protection: Role-Based Coordinate Blurring (500m random spatial jitter)
    blurred_coords = None
    coords = _extract_lat_lng(getattr(report, "gps_location", None))
    if coords is not None:
        lat, lng = coords
        import random, math
        angle = random.uniform(0, 2 * math.pi)
        distance_m = random.uniform(250, 500)
        jitter_lat = (distance_m * math.cos(angle)) / 111320.0
        jitter_lng = (distance_m * math.sin(angle)) / (111320.0 * math.cos(math.radians(lat)))
        blurred_coords = {
            "latitude": round(lat + jitter_lat, 5),
            "longitude": round(lng + jitter_lng, 5),
        }

    return ReportStatus(
        report_id=str(report.id),
        display_code=_make_display_code(report.id),
        status=report.status,
        timeline=timeline,
        incident_id=str(report.incident_id) if report.incident_id else None,
        rescue_eta_minutes=getattr(report, "relief_eta_minutes", 25) or 25,
        helpline_number="1122",
        parsed_text=getattr(report, "parsed_text", None) or getattr(report, "raw_input", None),
        raw_input=getattr(report, "raw_input", None),
        voice_transcript=getattr(report, "voice_transcript", None),
        acoustic_distress_level=getattr(report, "acoustic_distress_level", None),
        ai_extraction=getattr(report, "ai_extraction", None),
        semantic_score=getattr(report, "semantic_score", 0),
        consistency_score=getattr(report, "consistency_score", 0),
        grounding_score=getattr(report, "grounding_score", 10),
        cluster_score=getattr(report, "cluster_score", 5),
        verification_score=getattr(report, "verification_score", 0),
        vulnerability_level=getattr(report, "vulnerability_level", "requires_human_triage"),
        grounding_status=getattr(report, "grounding_status", "unreported_localized_incident"),
        cluster_id=getattr(report, "cluster_id", None),
        concise_report=ai_rep.get("concise_report"),
        ai_verification_report=ai_rep,
        relief_status=getattr(report, "relief_status", "pending") or "pending",
        relief_team_name=getattr(report, "relief_team_name", "Rescue 1122 Rapid Unit"),
        audio_url=report.audio_url,
        location_name=getattr(report, "extracted_location_name", "Reported Site"),
        gps_coords=blurred_coords,
        media_source=getattr(report, "media_source", None),
        grounding_label=getattr(report, "grounding_label", None),
        rubric_breakdown=getattr(report, "rubric_breakdown", None),
        provenance_flags=prov_flags,
        triage_tier=getattr(report, "triage_tier", "suspected_unconfirmed"),
        cluster_density_factor=getattr(report, "cluster_density_factor", 0.0),
        device_integrity_score=getattr(report, "device_integrity_score", 100),
        media_forensics_score=getattr(report, "media_forensics_score", 100),
        semantic_consistency_score=getattr(report, "semantic_consistency_score", 100),
        tamper_penalty=getattr(report, "tamper_penalty", 0),
        callback_status=getattr(report, "callback_status", None),
        verification_breakdown_5layer=getattr(report, "verification_breakdown_5layer", None),
    )


def _build_mock_timeline() -> List[TimelineStep]:
    return [
        TimelineStep(step="received", label_ur="SOS Bhej di gai", label_en="SOS Broadcast Received", completed=True, at=datetime.utcnow()),
        TimelineStep(step="verified", label_ur="AI Verification Mukammal", label_en="AI Verification Complete", completed=True, at=datetime.utcnow()),
        TimelineStep(step="dispatched", label_ur="Team Dispatch Ho Gai", label_en="Rescue Team Dispatched", completed=True, at=datetime.utcnow()),
        TimelineStep(step="en_route", label_ur="Madad Raste Mein Hai", label_en="Relief En Route", completed=False, at=None),
        TimelineStep(step="delivered", label_ur="Madad Mil Gai", label_en="Relief Delivered", completed=False, at=None),
    ]
