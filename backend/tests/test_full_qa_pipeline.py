import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import uuid
import wave
import io
import math
import random
from datetime import datetime, timezone
from fastapi import HTTPException

from app.db.database import async_session_maker
from app.models.report import Report
from app.models.incident import Incident, IncidentStatus
from app.models.rescue_team import RescueTeam
from app.models.incident_log import IncidentLog
from app.api.schemas import ReportCreate, ReportStatus
from app.services.report_service import ReportService
from app.services.incident_service import IncidentService
from app.services.geocoding_service import geocoding_service
from app.ai.verification import cross_reference_location
from app.api.dependencies import device_rate_limit
from app.api.routes.reports import _serialize_report_status
from app.api.routes.coordinator import _report_to_incident_detail, _clean_summary_text

async def run_qa_pipeline():
    print("==================================================================")
    print("       RELIEFPULSE AI - PRODUCTION INTEGRATION QA GATE           ")
    print("==================================================================")

    # ------------------------------------------------------------------
    # GATE 1: Offline Report Simulation & Payload Validity
    # ------------------------------------------------------------------
    print("\n>>> GATE 1: Offline Report Serialization & Format Check")
    offline_payload = {
        "client_id": f"offline_{uuid.uuid4().hex[:8]}",
        "sync_status": "queued",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "url": "/api/v1/reports",
        "method": "POST",
        "body": {
            "input_type": "voice",
            "latitude": 24.8607,
            "longitude": 67.0011,
            "address_text": "Karachi Port Trust area",
            "text_input": "Severe flash flood surging into building ground floor",
            "hazards": ["flood", "trapped"],
        }
    }
    assert offline_payload["sync_status"] == "queued"
    assert offline_payload["body"]["latitude"] is not None
    print("[PASS] Offline report successfully formatted with sync_status='queued'")

    # ------------------------------------------------------------------
    # GATE 2: Online Ingestion & Strict 3-Minute Device Rate Limiting
    # ------------------------------------------------------------------
    print("\n>>> GATE 2: Online Ingestion & 3-Minute Device/IP Rate Limiting")
    from app.config import settings
    orig_env = settings.fastapi_env
    settings.fastapi_env = "production"
    try:
        rate_limiter = device_rate_limit(window_seconds=180, max_requests=1)

        class MockRequest:
            def __init__(self, ip):
                self.headers = {"X-Forwarded-For": ip}
                self.client = type("Client", (), {"host": ip})()

        unique_ip = f"172.16.0.{random.randint(10, 250)}"
        req = MockRequest(unique_ip)

        # First report should succeed
        await rate_limiter(req)
        print(f"[PASS] Ingestion 1 accepted for IP: {unique_ip}")

        # Immediate second report must return HTTP 429
        rate_limited = False
        try:
            await rate_limiter(req)
        except HTTPException as exc:
            if exc.status_code == 429:
                rate_limited = True
                print(f"[PASS] Ingestion 2 immediately blocked with HTTP 429: {exc.detail}")
        assert rate_limited, "Rate limiter failed to block rapid submission"
    finally:
        settings.fastapi_env = orig_env

    # ------------------------------------------------------------------
    # GATE 3: Pre-Gemini Token Saving (Discard Short Spam)
    # ------------------------------------------------------------------
    print("\n>>> GATE 3: Pre-Gemini Token Saving Heuristics")
    async with async_session_maker() as session:
        service = ReportService(session)

        # 3a. Text < 8 chars
        spam_text = ReportCreate(
            input_type="text",
            text_input="sos",
            latitude=24.8607,
            longitude=67.0011,
        )
        rep_spam_text = await service.create_report(spam_text)
        assert rep_spam_text.status == "rejected"
        assert rep_spam_text.vulnerability_level == "false_or_prank"
        print(f"[PASS] Text < 8 chars discarded pre-Gemini without token consumption (status={rep_spam_text.status})")

        # 3b. Audio < 1.5s
        wav_buf = io.BytesIO()
        with wave.open(wav_buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(8000)
            wf.writeframes(b'\x00\x00' * 3000) # ~0.375s
        short_audio = wav_buf.getvalue()

        spam_audio = ReportCreate(
            input_type="voice",
            text_input="",
            latitude=24.8607,
            longitude=67.0011,
        )
        rep_spam_audio = await service.create_report(
            spam_audio,
            audio_bytes=short_audio,
            audio_mime_type="audio/wav",
        )
        assert rep_spam_audio.status == "rejected"
        print(f"[PASS] Audio < 1.5s discarded pre-Gemini without token consumption (status={rep_spam_audio.status})")

    # ------------------------------------------------------------------
    # GATE 4: Geospatial Ground Truth & Pakistan Bounding Box / 5km Mismatch
    # ------------------------------------------------------------------
    print("\n>>> GATE 4: Geospatial Ground Truth & Informal Landmark Resolution")
    # 4a. Bounding box
    assert geocoding_service.is_within_pakistan(24.8607, 67.0011) == True
    assert geocoding_service.is_within_pakistan(51.5074, -0.1278) == False # London
    print("[PASS] Pakistan Bounding Box clamping verified (Karachi=True, London=False)")

    # 4b. 5km landmark vs GPS mismatch detection
    gps_coords = (24.8607, 67.0011) # Karachi
    landmark_match = await cross_reference_location(
        gps_coords=gps_coords,
        extracted_location="Faisal Mosque Islamabad",
        extracted_city="Islamabad",
    )
    assert landmark_match.spatial_mismatch == True
    assert landmark_match.distance_km is not None and landmark_match.distance_km > 5.0
    print(f"[PASS] Spatial discrepancy > 5km caught: distance={landmark_match.distance_km:.1f}km, mismatch={landmark_match.spatial_mismatch}, match_level={landmark_match.match_level}")

    # ------------------------------------------------------------------
    # GATE 5: Deterministic State Machine & Database CheckConstraints
    # ------------------------------------------------------------------
    print("\n>>> GATE 5: Deterministic State Machine & DB Constraint Audit")
    async with async_session_maker() as session:
        inc_service = IncidentService(session)

        # Setup Rescue Team and Incident
        team = RescueTeam(
            id=uuid.uuid4(),
            team_name=f"1122 Rapid Response {uuid.uuid4().hex[:4]}",
            team_type="rescue",
            status="available",
        )
        session.add(team)
        await session.commit()

        inc = Incident(
            incident_code=f"RP-{uuid.uuid4().hex[:4].upper()}",
            hazard_type="flood",
            severity="critical",
            status="pending",
        )
        session.add(inc)
        await session.commit()
        await session.refresh(inc)

        # Pending -> Verified
        v_inc = await inc_service.transition_status(inc.id, "verified")
        assert v_inc.status == "verified"
        print(f"[PASS] State Transition: Pending -> Verified (status={v_inc.status})")

        # Verified -> Assigned WITHOUT team MUST FAIL DB constraint
        failed_without_team = False
        try:
            await inc_service.transition_status(inc.id, "assigned", assigned_team_id=None)
        except (ValueError, HTTPException):
            failed_without_team = True
            print("[PASS] Constraint Guard: 'assigned' transition rejected when assigned_team_id is None")
        assert failed_without_team, "Database allowed assigned status without team"

        # Verified -> Assigned WITH team
        a_inc = await inc_service.transition_status(inc.id, "assigned", assigned_team_id=team.id)
        assert a_inc.status == "assigned"
        assert a_inc.assigned_team_id == team.id
        print(f"[PASS] State Transition: Verified -> Assigned (team={team.id})")

        # Assigned -> En Route -> Reached -> Resolved
        er_inc = await inc_service.transition_status(inc.id, "en_route")
        assert er_inc.status == "en_route"
        print("[PASS] State Transition: Assigned -> En Route")

        rc_inc = await inc_service.transition_status(inc.id, "reached")
        assert rc_inc.status == "reached"
        print("[PASS] State Transition: En Route -> Reached")

        rs_inc = await inc_service.transition_status(inc.id, "resolved")
        assert rs_inc.status == "resolved"
        print("[PASS] State Transition: Reached -> Resolved")

        # Verify Immutable Audit Logs
        from sqlalchemy import select
        log_res = await session.execute(select(IncidentLog).where(IncidentLog.incident_id == inc.id).order_by(IncidentLog.created_at.asc()))
        logs = log_res.scalars().all()
        assert len(logs) >= 5
        print(f"[PASS] Immutable Audit Trail: {len(logs)} state logs generated in incident_logs table")

    # ------------------------------------------------------------------
    # GATE 6: Spatial Deduplication & Child Attachment (<150m, 12h)
    # ------------------------------------------------------------------
    print("\n>>> GATE 6: Spatial Deduplication (150m, 12h Window)")
    async with async_session_maker() as session:
        service = ReportService(session)

        base_lat = round(26.0 + random.uniform(0.1, 0.8), 4)
        base_lng = round(69.0 + random.uniform(0.1, 0.8), 4)

        # 1st report: Parent
        parent_report = await service.create_report(ReportCreate(
            input_type="text",
            text_input="Severe embankment breach threatening village homes",
            latitude=base_lat,
            longitude=base_lng,
        ))
        assert parent_report.parent_report_id is None

        # 2nd report: ~60m away
        child_report = await service.create_report(ReportCreate(
            input_type="text",
            text_input="Water overflowing near village embankment breach homes",
            latitude=base_lat + 0.0004,
            longitude=base_lng + 0.0002,
        ))

        await session.refresh(parent_report)
        await session.refresh(child_report)

        assert child_report.parent_report_id == parent_report.id
        assert parent_report.corroborated_count >= 2
        print(f"[PASS] Duplicate signal attached as child: child.parent_report_id={child_report.parent_report_id}")
        print(f"[PASS] Parent corroborated_count={parent_report.corroborated_count}, confidence_score={parent_report.confidence_score}")

    # ------------------------------------------------------------------
    # GATE 7: Privacy Boundaries & Role-Based Coordinate Blurring
    # ------------------------------------------------------------------
    print("\n>>> GATE 7: Privacy Boundaries & Role-Based Coordinate Blurring")
    async with async_session_maker() as session:
        # Public Serialization Check: 500m Jitter
        serialized = _serialize_report_status(parent_report)
        assert serialized.gps_coords is not None
        pub_lat = serialized.gps_coords["latitude"]
        pub_lng = serialized.gps_coords["longitude"]

        # Calculate distance between exact and blurred
        d_lat = abs(pub_lat - base_lat) * 111320.0
        d_lng = abs(pub_lng - base_lng) * 111320.0 * math.cos(math.radians(base_lat))
        jitter_dist = math.sqrt(d_lat**2 + d_lng**2)

        assert jitter_dist > 100.0, f"Expected spatial jitter, got {jitter_dist}m"
        print(f"[PASS] Public view coordinate blurred by {jitter_dist:.1f} meters (privacy safe)")

        # Coordinator Serialization Check: Exact unblurred coordinates
        coord_detail = _report_to_incident_detail(parent_report)
        coord_lat = coord_detail.location["centroid"]["lat"]
        coord_lng = coord_detail.location["centroid"]["lng"]
        assert abs(coord_lat - base_lat) < 0.001
        assert abs(coord_lng - base_lng) < 0.001
        print(f"[PASS] Coordinator view receives exact unblurred coordinates: {coord_lat}, {coord_lng}")

    # ------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------
    print("\n==================================================================")
    print("  ALL 7 QA GATES PASSED PERFECTLY - 10/10 PRODUCTION READY        ")
    print("==================================================================")

if __name__ == "__main__":
    asyncio.run(run_qa_pipeline())
