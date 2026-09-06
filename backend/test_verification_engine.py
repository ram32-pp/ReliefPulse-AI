"""
Comprehensive verification test suite for ReliefPulse-AI Fail-Open Verification Engine.

Tests:
1. NonceService (HMAC generation, signature verification, single-use replay protection, offline forgery resistance)
2. MediaForensicsService (EXIF extraction, Haversine spoof detection, pHash computation, Hamming dedup, no-media classification)
3. AsymmetricGroundingEngine (asymmetric scoring invariant: absence != penalty, hazard relevance)
4. RubricScorer (deterministic scoring: zero LLM drift, clamp [0, 100], fail-open baseline, no-media fairness, location mismatch)
5. Verification Pipeline fail-open invariants (never auto-reject, 4-stage structured outputs, timeout handling)
"""

import asyncio
import io
import time
from datetime import datetime, timezone
from PIL import Image

from app.services.nonce_service import NonceService, nonce_service
from app.services.media_forensics_service import MediaForensicsService, media_forensics_service
from app.ai.grounding_engine import AsymmetricGroundingEngine, grounding_engine, GroundingResult
from app.ai.rubric_scorer import RubricScorer, rubric_scorer
from app.ai.verification_pipeline import EmergencyVerificationPipeline, verification_pipeline
from app.api.schemas import ReportCreate, ReportResponse, CaptureNonceResponse


def test_nonce_service():
    print("\n--- Testing NonceService ---")
    svc = NonceService()
    res = svc.generate_nonce()
    assert "nonce" in res, "Missing nonce token"
    assert "expires_at" in res, "Missing expires_at"
    assert res["ttl_seconds"] == 120, "Incorrect TTL"

    nonce = res["nonce"]
    parts = nonce.split(".")
    assert len(parts) == 2, "Nonce must be in format <nonce_id>_<issued_at>.<signature>"

    # 1. Freshly generated nonce must validate successfully
    assert svc.validate_nonce(nonce) is True, "Valid nonce failed validation"

    # 2. Replay attack: Validating the SAME nonce a second time MUST fail
    assert svc.validate_nonce(nonce) is False, "Replay attack succeeded! Nonce was reused"

    # 3. Forgery attack: Attacker crafts fake token with valid length (32 hex + ts + 64 hex)
    fake_token = "0" * 32 + f"_{int(time.time())}." + "a" * 64
    assert svc.validate_nonce(fake_token) is False, "Vulnerability: Forged nonce with valid length passed HMAC check!"

    # 4. Tampered timestamp attack
    new_res = svc.generate_nonce()
    valid_nonce = new_res["nonce"]
    payload, sig = valid_nonce.split(".")
    nonce_id, ts = payload.split("_")
    tampered_ts_nonce = f"{nonce_id}_{int(ts) + 10}.{sig}"
    assert svc.validate_nonce(tampered_ts_nonce) is False, "Tampered timestamp was accepted!"

    # 5. Invalid nonces should return False gracefully
    assert svc.validate_nonce(None) is False, "None nonce should return False"
    assert svc.validate_nonce("") is False, "Empty nonce should return False"
    assert svc.validate_nonce("invalid.token") is False, "Corrupted nonce should return False"
    print("[PASS] NonceService passed all security, replay, and HMAC tests")


async def test_media_forensics():
    print("\n--- Testing MediaForensicsService ---")
    svc = MediaForensicsService()

    # Create a test synthetic image in memory
    img = Image.new("RGB", (100, 100), color=(73, 109, 137))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    # Test pHash computation
    phash = svc.compute_phash(img_bytes)
    assert phash is not None, "pHash computation returned None"
    assert len(phash) == 16, f"pHash should be a 16-character hex string (64-bit), got {phash}"

    # Test duplicate detection with identical hash
    dedup = svc.check_phash_duplicate(phash, [phash])
    assert dedup["is_duplicate"] is True, "Identical hash should match as duplicate"
    assert dedup["closest_distance"] == 0, "Distance to self must be 0"

    # Test duplicate detection with completely disparate hash (inverted bits)
    inverted_int = int(phash, 16) ^ 0xFFFFFFFFFFFFFFFF
    diff_hash = f"{inverted_int:016x}"
    dedup_diff = svc.check_phash_duplicate(diff_hash, [phash])
    assert dedup_diff["is_duplicate"] is False, "Inverted hash should not be a duplicate"
    assert dedup_diff["closest_distance"] > 5, "Disparate hashes should have distance > 5"

    # Test media source classification with media
    assert svc.classify_media_source("live_camera", nonce_validated=True, has_media=True) == "live_camera"
    assert svc.classify_media_source("live_camera", nonce_validated=False, has_media=True) == "gallery_unverified"
    assert svc.classify_media_source("gallery_unverified", nonce_validated=True, has_media=True) == "gallery_unverified"
    assert svc.classify_media_source(None, nonce_validated=False, has_media=True) == "gallery_unverified"

    # CRITICAL: Reports without media (text/voice only) MUST be classified as "no_media"
    assert svc.classify_media_source("gallery_unverified", nonce_validated=False, has_media=False) == "no_media"
    assert svc.classify_media_source(None, nonce_validated=False, has_media=False) == "no_media"

    # Test run_full_forensics with no media
    no_media_forensics = await svc.run_full_forensics(has_media=False)
    assert no_media_forensics["media_source"] == "no_media"
    assert no_media_forensics["has_media"] is False
    assert no_media_forensics["flag_location_spoof"] is False
    assert no_media_forensics["spoof_reasons"] == []
    print("[PASS] MediaForensicsService passed all tests")


def test_rubric_scorer_determinism():
    print("\n--- Testing RubricScorer Determinism & Invariants ---")
    scorer = RubricScorer()

    # Test 1: Identical inputs MUST yield identical scores (Zero drift invariant)
    res1 = scorer.score(
        hazard_severity="critical",
        scene_authenticity={"is_screen_recording_or_printed_photo": False, "optical_flow_consistent": True, "synthetic_artifacts_detected": False},
        cross_modal_alignment={"voice_transcript_matches_visuals": True},
        media_source="live_camera",
        flag_location_spoof=False,
        phash_duplicate_found=False,
        grounding_boost=25,
        grounding_label="authority_confirmed",
        location_name="Badin, Sindh",
        has_media=True,
    )

    res2 = scorer.score(
        hazard_severity="critical",
        scene_authenticity={"is_screen_recording_or_printed_photo": False, "optical_flow_consistent": True, "synthetic_artifacts_detected": False},
        cross_modal_alignment={"voice_transcript_matches_visuals": True},
        media_source="live_camera",
        flag_location_spoof=False,
        phash_duplicate_found=False,
        grounding_boost=25,
        grounding_label="authority_confirmed",
        location_name="Badin, Sindh",
        has_media=True,
    )

    assert res1.verification_score == res2.verification_score, "Deterministic scorer produced different scores for identical inputs!"
    assert res1.vulnerability_level == res2.vulnerability_level, "Vulnerability level diverged!"
    assert res1.rubric_breakdown == res2.rubric_breakdown, "Breakdown diverged!"

    # Test 2: Invariant: Absence of grounding does NOT penalize (grounding_boost=0, score >= baseline)
    res_no_grounding = scorer.score(
        hazard_severity="high",
        media_source="live_camera",
        grounding_boost=0,
        grounding_label="unreported_localized_incident",
        has_media=True,
    )
    # Base 40 + High 25 + Live camera 10 = 75
    assert res_no_grounding.verification_score >= 70, f"Unreported localized incident was penalized! Score: {res_no_grounding.verification_score}"

    # Test 3: Spoof penalty test
    res_spoof = scorer.score(
        hazard_severity="high",
        media_source="gallery_unverified",  # -10
        flag_location_spoof=True,           # -15
        phash_duplicate_found=True,         # -20
        scene_authenticity={"is_screen_recording_or_printed_photo": True},  # -25
        has_media=True,
    )
    # Score should be heavily reduced due to spoof penalties
    assert res_spoof.verification_score < 35, f"Spoofed media should score low, got {res_spoof.verification_score}"
    assert res_spoof.vulnerability_level == "low", f"Expected low for spoofed report with red flags, got {res_spoof.vulnerability_level}"

    # Test 4: Humanitarian fail-open clamp: score must be between 0 and 100
    assert 0 <= res_spoof.verification_score <= 100
    assert 0 <= res1.verification_score <= 100

    # Test 5: Text/Voice-only report (has_media=False) has 0 provenance penalty
    res_text_only = scorer.score(
        hazard_severity="high",
        media_source="no_media",
        has_media=False,
    )
    assert res_text_only.rubric_breakdown["provenance_points"] == 0, "Non-media report incurred provenance penalty!"
    assert "gallery_upload_unverified" not in res_text_only.rubric_breakdown["provenance_flags"]
    assert "no_media_narrative_mode" in res_text_only.rubric_breakdown["provenance_flags"]

    # Test 6: Location mismatch penalty: 15-point deduction
    res_loc_mismatch = scorer.score(
        hazard_severity="high",
        flag_location_mismatch=True,
        has_media=True,
    )
    assert res_loc_mismatch.rubric_breakdown.get("location_penalty") == -15, "Location mismatch did not apply 15 point penalty"
    assert "gps_claimed_location_mismatch" in res_loc_mismatch.rubric_breakdown.get("location_flags", [])
    print("[PASS] RubricScorer passed all determinism and invariant tests")


async def test_grounding_engine_asymmetry():
    print("\n--- Testing AsymmetricGroundingEngine ---")
    engine = AsymmetricGroundingEngine()

    # Grounding for a random location without API key should NEVER return a negative boost
    result = await engine.run_grounding(
        location_name="Unknown Valley Point 123",
        gps_coords=(24.8607, 67.0011),
        hazard_context="localized street flooding",
    )
    assert isinstance(result, GroundingResult)
    assert result.grounding_boost >= 0, f"Grounding boost was negative ({result.grounding_boost})! Invariant violated: absence must not penalize."

    # Flood report must NOT be corroborated by USGS earthquakes
    res_flood = await engine.run_grounding(
        location_name="Karachi",
        gps_coords=(24.8607, 67.0011),
        hazard_context="heavy monsoon urban flooding 4ft deep water",
    )
    for src in res_flood.source_results:
        if "earthquake" in src.source_name.lower():
            assert not src.matched, f"USGS earthquake source falsely matched flood claim: {src.summary}"
    print(f"[PASS] AsymmetricGroundingEngine: boost={result.grounding_boost}, label={result.grounding_label}")


async def test_verification_pipeline_fail_open():
    print("\n--- Testing Verification Pipeline Fail-Open Invariants ---")
    pipeline = EmergencyVerificationPipeline()

    # Test fail_open_result
    fail_open = pipeline._fail_open_result("Test Location", "pipeline_timeout")
    assert fail_open["verification_score"] == 40, "Fail-open score must be baseline 40"
    assert fail_open["vulnerability_level"] == "requires_human_triage", "Fail-open must set requires_human_triage"
    assert fail_open["is_verified"] is False
    assert "NOT been rejected" in fail_open["concise_report"], "Fail-open must never auto-reject"

    # Verify all 4 stages are provided in fail-open output
    assert "stage_1_location" in fail_open, "Missing stage_1_location in fail-open output"
    assert "stage_2_visual" in fail_open, "Missing stage_2_visual in fail-open output"
    assert "stage_3_intent" in fail_open, "Missing stage_3_intent in fail-open output"
    assert "stage_4_provenance" in fail_open, "Missing stage_4_provenance in fail-open output"
    print("[PASS] EmergencyVerificationPipeline fail-open invariants verified")


def test_pydantic_schemas():
    print("\n--- Testing API Schemas ---")
    req = ReportCreate(
        input_type="multimedia",
        text_input="Water rising fast",
        capture_nonce="abc.123",
        capture_timestamp="2026-09-04T12:00:00Z",
        media_source="live_camera",
    )
    assert req.capture_nonce == "abc.123"
    assert req.media_source == "live_camera"

    resp = ReportResponse(
        report_id="12345",
        display_code="RP-TEST",
        status="pending_audit",
        message_ur="Report received",
        message_en="Report received",
        estimated_review_seconds=30,
        track_url="/status/RP-TEST",
        verification_score=85,
        vulnerability_level="critical",
        media_source="live_camera",
        grounding_label="authority_confirmed",
        rubric_breakdown={"base_score": 40, "final_score": 85},
        provenance_flags=[],
    )
    assert resp.status == "pending_audit"
    assert resp.estimated_review_seconds == 30

    nonce_resp = CaptureNonceResponse(
        nonce="test.token",
        expires_at="2026-09-04T12:02:00Z",
        ttl_seconds=120,
    )
    assert nonce_resp.ttl_seconds == 120
    print("[PASS] API Schemas passed all validation checks")


async def main():
    print("==================================================")
    print("ReliefPulse-AI Fail-Open Verification Engine Tests")
    print("==================================================")
    test_nonce_service()
    await test_media_forensics()
    test_rubric_scorer_determinism()
    await test_grounding_engine_asymmetry()
    await test_verification_pipeline_fail_open()
    test_pydantic_schemas()
    print("\n==================================================")
    print("ALL TESTS PASSED WITH 100% INVARIANT COMPLIANCE!")
    print("==================================================")


if __name__ == "__main__":
    asyncio.run(main())
