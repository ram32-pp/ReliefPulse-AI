"""
Automated Test Suite for ReliefPulse-AI Voice, Text, and Location Verification Pipeline.

Acceptance Criteria:
  1. Clean emergency voice note + matching text -> deterministic score >= 75 (HIGH or CRITICAL).
  2. Silent/empty voice note with empty/vague text -> outputs requires_human_triage (fail-open safety, zero crashes).
  3. Non-matching prank audio (synthetic/prank) -> clamps score <= 15 (false_or_prank).
  4. Zero-grounding search scenario -> report classified as "unreported_localized_incident" with NO penalty (neutral baseline +10 pts).
  5. Speed & Resilience -> Verify POST /api/v1/reports returns HTTP 201 within 300ms fast path.
"""

import sys
import os
import time
import asyncio
import unittest

# Add backend directory to sys.path so app imports resolve
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.scoring_engine import scoring_engine, DeterministicScoringEngine
from app.ai.verification_pipeline import EmergencyVerificationPipeline, verification_pipeline


class TestVoiceVerificationPipeline(unittest.TestCase):
    def setUp(self):
        self.engine = DeterministicScoringEngine()

    def test_clean_emergency_voice_note_and_matching_text(self):
        """
        Scenario 1: Clean emergency voice note with high distress, specific details,
        acoustic cues, matching text, and cluster corroboration -> score >= 75 (CRITICAL/HIGH).
        """
        result = self.engine.compute_score(
            speaker_distress_level="critical",
            specific_details_provided=True,
            acoustic_cues=["rushing_water", "sirens"],
            text_audio_alignment=True,
            has_contradiction=False,
            is_authoritative_grounded=True,
            grounding_status="authoritative_match",
            is_cluster_corroborated=True,
            corroborating_reports_count=3,
            suspected_prank_or_synthetic=False,
            is_audio_silent_or_corrupted=False,
            has_text_content=True,
            location_name="Korangi Sector 4, Karachi",
            detected_hazards=["flood", "trapped"],
        )

        # Expected:
        # Acoustic/Semantic: 15 (critical) + 15 (details) + 10 (cues) = 40 pts
        # Consistency: 20 pts
        # Grounding: 20 pts
        # Clustering: 20 pts
        # Total: 100 pts
        self.assertGreaterEqual(result.verification_score, 75)
        self.assertIn(result.vulnerability_level, ["critical", "high"])
        self.assertEqual(result.semantic_score, 40)
        self.assertEqual(result.consistency_score, 20)
        self.assertEqual(result.grounding_score, 20)
        self.assertEqual(result.cluster_score, 20)
        print(f"\n[PASS] Clean Emergency Note: Score={result.verification_score}, Level={result.vulnerability_level}")

    def test_silent_empty_voice_note_fail_open(self):
        """
        Scenario 2: Silent/corrupted audio with empty text -> fail-open safety,
        outputs requires_human_triage with score 0 (zero crashes).
        """
        result = self.engine.compute_score(
            speaker_distress_level="inaudible",
            specific_details_provided=False,
            acoustic_cues=[],
            text_audio_alignment=True,
            has_contradiction=False,
            is_authoritative_grounded=False,
            grounding_status="unreported_localized_incident",
            is_cluster_corroborated=False,
            corroborating_reports_count=0,
            suspected_prank_or_synthetic=False,
            is_audio_silent_or_corrupted=True,
            has_text_content=False,
            location_name="Unknown Location",
            detected_hazards=[],
        )

        self.assertEqual(result.verification_score, 0)
        self.assertEqual(result.vulnerability_level, "requires_human_triage")
        self.assertIn("SECURITY_OVERRIDE_SILENT_EMPTY", result.breakdown["flags"])
        print(f"[PASS] Silent/Empty Audio: Score={result.verification_score}, Level={result.vulnerability_level} (Fail-Open Safety)")

    def test_prank_synthetic_audio_clamp(self):
        """
        Scenario 3: Non-matching prank audio or synthetic TTS -> clamps score <= 15 (false_or_prank).
        """
        result = self.engine.compute_score(
            speaker_distress_level="elevated",
            specific_details_provided=True,
            acoustic_cues=[],
            text_audio_alignment=False,
            has_contradiction=True,
            is_authoritative_grounded=True,
            grounding_status="authoritative_match",
            is_cluster_corroborated=False,
            suspected_prank_or_synthetic=True,
            is_audio_silent_or_corrupted=False,
            has_text_content=True,
            location_name="Downtown",
            detected_hazards=["flood"],
        )

        self.assertLessEqual(result.verification_score, 15)
        self.assertEqual(result.verification_score, 10)
        self.assertEqual(result.vulnerability_level, "false_or_prank")
        self.assertIn("SECURITY_OVERRIDE_PRANK_CLAMP", result.breakdown["flags"])
        print(f"[PASS] Prank Audio Clamp: Score={result.verification_score}, Level={result.vulnerability_level}")

    def test_zero_grounding_unreported_localized_incident_no_penalty(self):
        """
        Scenario 4: Early-stage disaster with zero web records -> classified as
        unreported_localized_incident with NO penalty (+10 neutral baseline).
        """
        result = self.engine.compute_score(
            speaker_distress_level="critical",
            specific_details_provided=True,
            acoustic_cues=["rushing_water"],
            text_audio_alignment=True,
            has_contradiction=False,
            is_authoritative_grounded=False,
            grounding_status="unreported_localized_incident",
            is_cluster_corroborated=False,
            corroborating_reports_count=0,
            suspected_prank_or_synthetic=False,
            is_audio_silent_or_corrupted=False,
            has_text_content=True,
            location_name="Remote Sector 9",
            detected_hazards=["flash_flood"],
        )

        # Grounding must provide +10 baseline points (NOT 0, and NEVER negative)
        self.assertEqual(result.grounding_score, 10)
        self.assertEqual(result.breakdown["grounding_status"], "unreported_localized_incident")
        # Acoustic 40 + Consistency 20 + Grounding 10 + Cluster 5 = 75 pts (Critical)
        self.assertGreaterEqual(result.verification_score, 75)
        self.assertEqual(result.vulnerability_level, "critical")
        print(f"[PASS] Zero-Grounding Scenario: Score={result.verification_score}, Grounding={result.grounding_score}/20, Status={result.breakdown['grounding_status']}")

    def test_pipeline_async_full_run(self):
        """
        Test end-to-end async verification pipeline execution with mocked inputs.
        """
        pipeline = EmergencyVerificationPipeline()

        async def run_test():
            res = await pipeline.run_full_pipeline(
                location_name="Karachi Central, Block 3",
                gps_coords=(24.8607, 67.0011),
                text_message="Paani barh raha hai, ghar ki chhat par 4 log phanse hain madad bhejein",
                hazard_tags=["flood", "trapped"],
            )
            self.assertIn("verification_score", res)
            self.assertIn("vulnerability_level", res)
            self.assertIn("voice_transcript", res)
            self.assertIn("grounding_status", res)
            self.assertGreaterEqual(res["verification_score"], 50)
            print(f"[PASS] Full Async Pipeline Run: Score={res['verification_score']}, Level={res['vulnerability_level']}")

        asyncio.run(run_test())

    def test_fast_path_latency_and_http_201(self):
        """
        Scenario 5: Speed & Resilience: Verify POST /api/v1/reports returns HTTP 201 within 300ms.
        """
        import httpx
        from app.main import app

        payload = {
            "input_type": "voice",
            "text_note": "Rapid urban flood on Street 4, 3 individuals stranded on rooftop",
            "hazards": ["Rising Floodwater", "Trapped People"],
            "address_text": "Gulshan-e-Iqbal Block 13-D, Karachi",
            "latitude": 24.9180,
            "longitude": 67.0971,
        }

        async def run_req():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                # Connection pool warm-up
                await client.post("/api/v1/reports", json=payload, headers={"X-Device-ID": f"test-warmup-{time.time()}"})
                start_time = time.perf_counter()
                resp = await client.post("/api/v1/reports", json=payload, headers={"X-Device-ID": f"test-measure-{time.time()}"})
                elapsed = (time.perf_counter() - start_time) * 1000
                return resp, elapsed

        response, elapsed_ms = asyncio.run(run_req())

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("report_id", data)
        self.assertIn("display_code", data)
        self.assertEqual(data["status"], "pending_audit")

        # Verify < 300ms fast-path latency invariant
        print(f"[PASS] Fast-Path Ingestion: HTTP Status={response.status_code}, Latency={elapsed_ms:.1f}ms (<300ms invariant satisfied)")
        self.assertLess(elapsed_ms, 300, f"Fast-path latency ({elapsed_ms:.1f}ms) exceeded 300ms limit")


if __name__ == "__main__":
    unittest.main()
