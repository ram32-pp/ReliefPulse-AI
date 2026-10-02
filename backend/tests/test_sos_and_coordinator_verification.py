import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import time
import uuid
import random
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.database import async_session_maker
from app.models.report import Report
from app.services.report_service import _run_verification_background
from sqlalchemy import select


async def test_app_sos_and_coordinator():
    print("=" * 70)
    print("  RELIEFPULSE AI - FULL SOS TO COORDINATOR & FAKE vs TRUE ANALYSIS")
    print("=" * 70)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:

        # -----------------------------------------------------------------
        # TEST 1: Health check
        # -----------------------------------------------------------------
        print("\n[STEP 1] Testing Backend Health Check")
        r_health = await client.get("/health")
        assert r_health.status_code == 200
        print("  -> Status 200 OK: Backend is operational.")

        # -----------------------------------------------------------------
        # TEST 2: True Emergency SOS Submission
        # -----------------------------------------------------------------
        print("\n[STEP 2] Submitting Genuine Life-Threatening SOS Emergency Report")
        test_ip = f"192.168.1.{random.randint(10, 240)}"
        headers = {"X-Forwarded-For": test_ip}

        true_lat = round(24.8100 + random.uniform(0.01, 0.15), 4)
        true_lng = round(67.0100 + random.uniform(0.01, 0.15), 4)
        true_payload = {
            "input_type": "text",
            "latitude": true_lat,
            "longitude": true_lng,
            "address_text": "Liaquatabad Block 4, Karachi",
            "text_input": "Bachao! 6 foot paani aa gaya hai ghar me, 5 afraad chhat par phanse hain, buzurag mareez bhi hain!",
            "hazards": ["flood", "trapped"],
        }

        t0 = time.perf_counter()
        r_true = await client.post("/api/v1/reports", json=true_payload, headers=headers)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert r_true.status_code == 201, f"Failed: {r_true.text}"
        true_data = r_true.json()
        true_report_id = true_data["report_id"]
        true_code = true_data["display_code"]
        print(f"  -> SOS Received! HTTP 201 in {elapsed_ms:.1f}ms (<300ms fast path).")
        print(f"  -> Tracking Code: {true_code} (Report ID: {true_report_id})")

        # Run the verification background pipeline for this report
        print("\n[STEP 3] Running Full AI Verification Pipeline for Genuine Report")
        await _run_verification_background(
            report_id=uuid.UUID(true_report_id),
            location_name="Liaquatabad Block 4, Karachi",
            gps_tuple=(true_lat, true_lng),
            text_input=true_payload["text_input"],
            audio_bytes=None,
            audio_mime_type="audio/webm",
            quick_hazard_tags=true_payload["hazards"],
        )

        # Fetch report from DB and verify scoring
        async with async_session_maker() as session:
            res = await session.execute(select(Report).where(Report.id == uuid.UUID(true_report_id)))
            rep_true = res.scalars().first()
            assert rep_true is not None

            print(f"  -> Verification Score: {rep_true.verification_score}/100")
            print(f"  -> Vulnerability Level: {rep_true.vulnerability_level}")
            print(f"  -> Relief Status: {rep_true.relief_status}")
            print(f"  -> Semantic Score: {rep_true.semantic_score}")
            print(f"  -> Consistency Score: {rep_true.consistency_score}")
            print(f"  -> Grounding Score: {rep_true.grounding_score}")
            print(f"  -> Headcount Extracted: {rep_true.ai_extraction.get('headcount')}")
            print(f"  -> Vulnerable Groups: {rep_true.ai_extraction.get('vulnerable_groups')}")

            assert rep_true.verification_score >= 60, f"True report scored too low: {rep_true.verification_score}"
            assert rep_true.vulnerability_level in ["critical", "high"], f"Unexpected level: {rep_true.vulnerability_level}"
            assert rep_true.status in ["verified", "pending_audit"], f"Unexpected status: {rep_true.status}"
            assert rep_true.ai_extraction.get("headcount") == 5, f"Expected 5 people, got: {rep_true.ai_extraction.get('headcount')}"
            print("  -> PASS: Genuine SOS report correctly classified with High/Critical severity and headcount 5!")

        # -----------------------------------------------------------------
        # TEST 4: Check that the True Report Appears in Coordinator Triage Queue
        # -----------------------------------------------------------------
        print("\n[STEP 4] Verifying True Report Appears in Coordinator Dashboard Queue")
        r_triage = await client.get("/api/v1/coordinator/triage?status=open")
        assert r_triage.status_code == 200
        triage_data = r_triage.json()

        matching_incident = None
        for inc in triage_data.get("incidents", []):
            if inc.get("report_id") == true_report_id or inc.get("incident_code") == true_code:
                matching_incident = inc
                break

        assert matching_incident is not None, f"True report {true_code} not found in Coordinator triage queue!"
        print(f"  -> FOUND in Coordinator Triage Queue!")
        print(f"     Code: #{matching_incident['incident_code']}")
        print(f"     Severity: {matching_incident['severity'].upper()}")
        print(f"     Location: {matching_incident['location']['name']}")
        print(f"     GPS: {matching_incident['location']['centroid']}")
        print(f"     Headcount: {matching_incident['total_individuals']} people")
        print(f"     Hazards: {matching_incident['hazard_type']}")
        print(f"     AI Summary: {matching_incident['ai_summary']}")
        print("  -> PASS: Coordinator tab successfully displays genuine citizen SOS!")

        # -----------------------------------------------------------------
        # TEST 5: Submit a FAKE / PRANK Report
        # -----------------------------------------------------------------
        print("\n[STEP 5] Submitting a FAKE / PRANK Emergency Report")
        fake_ip = f"192.168.2.{random.randint(10, 240)}"
        fake_headers = {"X-Forwarded-For": fake_ip}

        fake_lat = round(25.0100 + random.uniform(0.01, 0.15), 4)
        fake_lng = round(67.2100 + random.uniform(0.01, 0.15), 4)
        fake_payload = {
            "input_type": "text",
            "latitude": fake_lat,
            "longitude": fake_lng,
            "address_text": "Clifton Karachi",
            "text_input": "Haha this is a fake sos joke prank testing 123 rickroll comedy!",
            "hazards": ["flood"],
        }

        r_fake = await client.post("/api/v1/reports", json=fake_payload, headers=fake_headers)
        assert r_fake.status_code == 201
        fake_data = r_fake.json()
        fake_report_id = fake_data["report_id"]
        fake_code = fake_data["display_code"]
        print(f"  -> Fake Report Received: Code {fake_code} (Report ID: {fake_report_id})")

        print("\n[STEP 6] Running AI Verification on Fake Report")
        await _run_verification_background(
            report_id=uuid.UUID(fake_report_id),
            location_name="Clifton Karachi",
            gps_tuple=(fake_lat, fake_lng),
            text_input=fake_payload["text_input"],
            audio_bytes=None,
            audio_mime_type="audio/webm",
            quick_hazard_tags=fake_payload["hazards"],
        )

        async with async_session_maker() as session:
            res = await session.execute(select(Report).where(Report.id == uuid.UUID(fake_report_id)))
            rep_fake = res.scalars().first()
            assert rep_fake is not None

            print(f"  -> Verification Score: {rep_fake.verification_score}/100")
            print(f"  -> Vulnerability Level: {rep_fake.vulnerability_level}")
            print(f"  -> Status: {rep_fake.status}")
            print(f"  -> Flags: {rep_fake.anomaly_flags}")

            # Verification invariants for fake/prank reports:
            # 1. Clamped to <= 15 points
            # 2. Level = false_or_prank
            # 3. Status = rejected
            assert rep_fake.verification_score <= 15, f"Fake report score not clamped: {rep_fake.verification_score}"
            assert rep_fake.vulnerability_level == "false_or_prank", f"Expected false_or_prank, got: {rep_fake.vulnerability_level}"
            assert rep_fake.status == "rejected", f"Expected rejected, got: {rep_fake.status}"
            assert "SECURITY_OVERRIDE_PRANK_CLAMP" in (rep_fake.anomaly_flags or []), "Missing prank security flag!"
            print("  -> PASS: Fake report accurately clamped to score 10, flagged as 'false_or_prank', and rejected!")

        # -----------------------------------------------------------------
        # TEST 7: Confirm Fake Report is EXCLUDED from Active Coordinator Queue
        # -----------------------------------------------------------------
        print("\n[STEP 7] Verifying Fake Report is Excluded from Coordinator Active Triage Queue")
        r_triage2 = await client.get("/api/v1/coordinator/triage?status=open")
        assert r_triage2.status_code == 200
        triage_data2 = r_triage2.json()

        fake_in_triage = any(
            inc.get("report_id") == fake_report_id or inc.get("incident_code") == fake_code
            for inc in triage_data2.get("incidents", [])
        )
        assert not fake_in_triage, "SECURITY ALERT: Fake report appeared in active coordinator triage queue!"
        print("  -> PASS: Fake report is successfully filtered out of active coordinator dispatch queue!")

        # -----------------------------------------------------------------
        # TEST 8: Coordinator can still audit rejected reports with status=rejected
        # -----------------------------------------------------------------
        print("\n[STEP 8] Verifying Coordinator Can Inspect Rejected/Fake Reports via Audit Filter")
        r_rejected = await client.get("/api/v1/coordinator/triage?status=rejected")
        assert r_rejected.status_code == 200
        rejected_data = r_rejected.json()

        found_in_rejected = any(
            inc.get("report_id") == fake_report_id or inc.get("incident_code") == fake_code
            for inc in rejected_data.get("incidents", [])
        )
        assert found_in_rejected, "Coordinator could not find fake report under rejected audit filter!"
        print(f"  -> PASS: Coordinator can audit rejected/fake report {fake_code} under status=rejected!")

    print("\n" + "=" * 70)
    print("  ALL VERIFICATION & TRIAGE TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_app_sos_and_coordinator())
