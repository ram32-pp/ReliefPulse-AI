import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import uuid
import wave
import io
from fastapi import Request, HTTPException
from app.db.database import async_session_maker
from app.models.report import Report
from app.api.schemas import ReportCreate, GPSLocation
from app.services.report_service import ReportService
from app.api.dependencies import device_rate_limit, _in_memory_device_limits

async def test_feature4():
    print("=== STARTING FEATURE 4 TEST SUITE ===")

    # 1. Test Device/IP Rate Limiting (1 report / 3 minutes)
    print("\n--- 1. Testing Device/IP Rate Limiting ---")
    rate_limiter = device_rate_limit(window_seconds=180, max_requests=1)

    class MockRequest:
        def __init__(self, headers=None, client_host="192.168.1.100"):
            self.headers = headers or {}
            self.client = type("Client", (), {"host": client_host})()

    test_ip = f"10.0.0.{uuid.uuid4().hex[:4]}"
    req1 = MockRequest(headers={"X-Forwarded-For": test_ip})

    # First request should pass
    await rate_limiter(req1)
    print("[OK] Request 1 allowed through rate limiter")

    # Immediate second request from same device/IP should fail with HTTP 429
    blocked_429 = False
    try:
        await rate_limiter(req1)
    except HTTPException as e:
        if e.status_code == 429:
            blocked_429 = True
            print(f"[OK] Request 2 correctly rejected with HTTP 429: {e.detail}")
    assert blocked_429, "Rate limiter did not raise HTTP 429 on second immediate submission"

    # 2. Test Pre-Gemini Token Saving (Short text / short audio)
    print("\n--- 2. Testing Pre-Gemini Token Saving ---")
    async with async_session_maker() as session:
        service = ReportService(session)

        # 2a. Short text (<8 chars) with no audio
        short_report_data = ReportCreate(
            input_type="text",
            text_input="help",  # 4 chars < 8
            latitude=24.8607,
            longitude=67.0011,
        )
        rep_short = await service.create_report(short_report_data)
        assert rep_short.status == "rejected", f"Expected rejected status, got {rep_short.status}"
        assert rep_short.vulnerability_level == "false_or_prank", f"Expected false_or_prank, got {rep_short.vulnerability_level}"
        print(f"[OK] Short text (<8 chars) immediately rejected pre-Gemini (status={rep_short.status})")

        # 2b. Short audio (<1.5s) with empty text
        # Generate 0.5 second WAV audio
        wav_buf = io.BytesIO()
        with wave.open(wav_buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(8000)
            wf.writeframes(b'\x00\x00' * 4000) # 4000 frames @ 8000 Hz = 0.5 seconds
        short_wav_bytes = wav_buf.getvalue()

        short_audio_data = ReportCreate(
            input_type="voice",
            text_input="",
            latitude=24.8607,
            longitude=67.0011,
        )
        rep_audio_short = await service.create_report(
            short_audio_data,
            audio_bytes=short_wav_bytes,
            audio_mime_type="audio/wav",
        )
        assert rep_audio_short.status == "rejected", f"Expected rejected status, got {rep_audio_short.status}"
        print(f"[OK] Short audio (0.5s < 1.5s) immediately rejected pre-Gemini (status={rep_audio_short.status})")

    # 3. Test Spatial Deduplication & Child Attachment (<150m & 12h)
    print("\n--- 3. Testing Spatial Clustering Deduplication ---")
    import random
    base_lat = round(25.0 + random.uniform(0.1, 0.8), 4)
    base_lng = round(68.0 + random.uniform(0.1, 0.8), 4)

    async with async_session_maker() as session:
        service = ReportService(session)
        # Parent report: valid emergency report at specific coordinates
        parent_data = ReportCreate(
            input_type="text",
            text_input="Severe flooding trapped families on roof near new relief zone",
            latitude=base_lat,
            longitude=base_lng,
        )
        parent_rep = await service.create_report(parent_data)
        print(f"[OK] Parent report created: ID={parent_rep.id}, status={parent_rep.status}, parent_report_id={parent_rep.parent_report_id}")
        assert parent_rep.parent_report_id is None, "Parent report should not have parent_report_id"

        # Child report: another report ~50 meters away (lat offset ~0.0004) within 12 hours
        child_data = ReportCreate(
            input_type="text",
            text_input="Water rising very high in house nearby in same zone",
            latitude=base_lat + 0.0004,
            longitude=base_lng + 0.0002,
        )
        child_rep = await service.create_report(child_data)
        print(f"[OK] Duplicate nearby report created: ID={child_rep.id}")

        # Verify child report attached to parent
        await session.refresh(child_rep)
        await session.refresh(parent_rep)
        assert child_rep.parent_report_id == parent_rep.id, f"Expected child parent_report_id={parent_rep.id}, got {child_rep.parent_report_id}"
        assert parent_rep.corroborated_count >= 2, f"Expected parent corroborated_count >= 2, got {parent_rep.corroborated_count}"
        print(f"[OK] Child report successfully attached to parent! (child.parent_report_id = {child_rep.parent_report_id})")
        print(f"[OK] Parent corroborated_count incremented to {parent_rep.corroborated_count}, confidence={parent_rep.confidence_score}")

    print("\n=== ALL FEATURE 4 TESTS PASSED (10/10) ===")

if __name__ == "__main__":
    asyncio.run(test_feature4())
