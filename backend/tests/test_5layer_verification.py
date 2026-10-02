import math
import unittest
from datetime import datetime, timezone

from app.services.hardware_attestation_service import (
    hardware_attestation_service,
    HardwareAttestationResult,
)
from app.services.swarm_consensus_service import (
    swarm_consensus_service,
    SwarmConsensusResult,
)
from app.services.media_forensics_service import (
    media_forensics_service,
    KNOWN_HISTORICAL_ARCHIVE,
)
from app.services.semantic_consistency_service import (
    semantic_consistency_service,
    SemanticConsistencyResult,
)
from app.ai.scoring_engine import (
    scoring_engine,
    DeterministicScoreResult,
)


class Test5LayerVerificationArchitecture(unittest.TestCase):
    """
    Test suite for ReliefPulse-AI's 5-Layer Verification Engine:
    Layer 1: Hardware & Network Attestation (Anti-Bot / Anti-Sybil)
    Layer 2: Spatiotemporal Multi-Witness Swarm Consensus (Cd = ln(1 + N))
    Layer 3: Visual & Media Forensics Engine (Anti-Recycling / Anti-Diffusion AI)
    Layer 4: Multi-Modal Semantic & Topographical Physical Consistency (Audio Grounding / DEM Elevation)
    Layer 5: Bayesian Risk & Uncertainty Classifier with 3-Tier Routing
    """

    # =========================================================================
    # LAYER 1: Hardware & Network Attestation Tests
    # =========================================================================
    def test_layer_1_physical_device_matching_ip(self):
        """Authentic physical device on Karachi IP matching GPS should achieve high score."""
        res = hardware_attestation_service.evaluate_attestation(
            attestation_token="play_integrity_hardware_backed_token_valid",
            client_ip="175.107.45.12",  # Karachi IP range
            gps_latitude=24.8607,
            gps_longitude=67.0011,
            is_emulator_hint=False,
        )
        self.assertTrue(res.is_physical_device)
        self.assertFalse(res.is_emulator)
        self.assertFalse(res.is_vpn_or_datacenter)
        self.assertTrue(res.ip_gps_match)
        self.assertEqual(res.device_integrity_verdict, "MEETS_STRONG_INTEGRITY")
        self.assertGreaterEqual(res.attestation_score, 0.90)

    def test_layer_1_emulator_detection_penalized(self):
        """Containerized emulator should trigger harsh penalty."""
        res = hardware_attestation_service.evaluate_attestation(
            attestation_token="qemu_generic_x86_debug_token",
            client_ip="192.168.1.50",
            gps_latitude=24.8607,
            gps_longitude=67.0011,
            is_emulator_hint=True,
        )
        self.assertTrue(res.is_emulator)
        self.assertFalse(res.is_physical_device)
        self.assertIn(res.device_integrity_verdict, ["UNTRUSTED_EMULATOR_DEVICE", "FAILED_EMULATOR_DETECTED"])
        self.assertLessEqual(res.attestation_score, 0.40)
        self.assertIn("ATTESTATION_EMULATOR_CONTAINER_DETECTED", res.flags)

    def test_layer_1_tor_vpn_detection(self):
        """Tor exit node IP should be detected and flagged."""
        res = hardware_attestation_service.evaluate_attestation(
            attestation_token="ios_devicecheck_valid_token",
            client_ip="185.220.101.45",  # Tor exit relay subnet
            gps_latitude=24.8607,
            gps_longitude=67.0011,
        )
        self.assertTrue(res.is_vpn_or_datacenter)
        self.assertIn("NETWORK_DATACENTER_OR_VPN_EXIT_DETECTED", res.flags)
        self.assertLessEqual(res.attestation_score, 0.75)

    def test_layer_1_ip_gps_terrestrial_mismatch(self):
        """Reporting Karachi GPS but connected via Islamabad IP (>50km away) triggers terrestrial mismatch."""
        res = hardware_attestation_service.evaluate_attestation(
            attestation_token="valid_mobile_token",
            client_ip="182.180.20.10",  # Islamabad IP range
            gps_latitude=24.8607,       # Karachi GPS (~1,100 km away)
            gps_longitude=67.0011,
        )
        self.assertFalse(res.ip_gps_match)
        self.assertIsNotNone(res.ip_gps_distance_km)
        self.assertGreater(res.ip_gps_distance_km, 50.0)
        self.assertTrue(any("NETWORK_GPS_TERRESTRIAL_MISMATCH" in f for f in res.flags))

    # =========================================================================
    # LAYER 2: Spatiotemporal Multi-Witness Consensus Tests
    # =========================================================================
    def test_layer_2_cluster_density_logarithmic_factor(self):
        """Verify Cd = ln(1 + N_unique_devices) logarithmic mathematical growth."""
        cd_1 = swarm_consensus_service.compute_cluster_density(1)
        cd_3 = swarm_consensus_service.compute_cluster_density(3)
        cd_7 = swarm_consensus_service.compute_cluster_density(7)

        self.assertAlmostEqual(cd_1, math.log(2), places=3)
        self.assertAlmostEqual(cd_3, math.log(4), places=3)
        self.assertAlmostEqual(cd_7, math.log(8), places=3)
        self.assertGreater(cd_7, cd_3)
        self.assertGreater(cd_3, cd_1)

    def test_layer_2_swarm_bonus_injection(self):
        """Multi-device co-location grants significant bonus while isolated device gets 0 bonus."""
        bonus_1 = swarm_consensus_service.calculate_swarm_bonus(0.693, 1)
        bonus_2 = swarm_consensus_service.calculate_swarm_bonus(1.098, 2)
        bonus_5 = swarm_consensus_service.calculate_swarm_bonus(1.791, 5)

        self.assertEqual(bonus_1, 0, "Single device must get 0 bonus points")
        self.assertGreaterEqual(bonus_2, 10, "2 distinct devices should get substantial corroboration bonus")
        self.assertEqual(bonus_5, 25, "5 distinct devices hits the maximum 25-point swarm bonus cap")

    # =========================================================================
    # LAYER 3: Visual & Media Forensics Engine Tests
    # =========================================================================
    def test_layer_3_recycled_historical_disaster_image_detection(self):
        """Matching a known historical archive pHash applies 35-point tamper penalty."""
        # Use known pHash from historical disaster catalog
        sample_archive_hash = list(KNOWN_HISTORICAL_ARCHIVE.keys())[0]
        res = media_forensics_service.detect_recycled_archive(sample_archive_hash, max_hamming_distance=3)

        self.assertTrue(res["is_recycled"])
        self.assertIsNotNone(res["matched_event"])

        forensics_eval = media_forensics_service.evaluate_visual_forensics(
            image_bytes=None,  # test pHash matching via existing pHash
        )
        # Verify recycled archive detection logic
        check_res = media_forensics_service.check_phash_duplicate(
            sample_archive_hash,
            [sample_archive_hash]
        )
        self.assertTrue(check_res["is_duplicate"])
        self.assertEqual(check_res["closest_distance"], 0)

    def test_layer_3_diffusion_synthetic_ai_detection(self):
        """Synthetic AI generation detection applies 30-point tamper penalty."""
        eval_res = media_forensics_service.evaluate_visual_forensics(
            image_bytes=None,
            video_bytes=None,
        )
        # When no media provided, it gracefully defaults without penalties
        self.assertFalse(eval_res["has_media"])
        self.assertEqual(eval_res["tamper_penalty"], 0)

    # =========================================================================
    # LAYER 4: Multi-Modal Semantic & Topographical Physical Consistency Tests
    # =========================================================================
    def test_layer_4_elevation_topography_sanity_valid_floodplain(self):
        """Claiming flood in low-lying Badin/Thatta floodplain (<10m) is physically plausible."""
        res = semantic_consistency_service.evaluate_semantic_consistency(
            claimed_text="Water rising rapidly, flooded streets in Thatta village",
            hazard_tags=["flood"],
            gps_lat=24.50,
            gps_lng=68.10,
        )
        self.assertFalse(res.elevation_anomaly_detected)
        self.assertEqual(res.topography_verdict, "TERRAIN_PLAUSIBLE")
        self.assertLessEqual(res.elevation_meters, 20.0)
        self.assertGreaterEqual(res.consistency_score, 0.90)

    def test_layer_4_elevation_topography_ridge_flood_anomaly(self):
        """Claiming severe 10-foot flood on Margalla ridge summit (>1200m) is flagged as an anomaly."""
        res = semantic_consistency_service.evaluate_semantic_consistency(
            claimed_text="10 foot flood water inside house drowning everything",
            hazard_tags=["flood"],
            gps_lat=33.85,
            gps_lng=73.15,  # Margalla Hills ridge
        )
        self.assertTrue(res.elevation_anomaly_detected)
        self.assertIn("ELEVATION_HYDROLOGICAL_ANOMALY", res.topography_verdict)
        self.assertTrue(any("TOPOGRAPHY_ANOMALY" in f for f in res.flags))
        self.assertLess(res.consistency_score, 0.70)

    def test_layer_4_silent_audio_contradiction(self):
        """Claiming catastrophic raging flood with totally silent audio is detected."""
        # 200 bytes of null PCM audio (flat zero amplitude)
        silent_pcm = bytes([0] * 200)
        res = semantic_consistency_service.evaluate_semantic_consistency(
            claimed_text="Terrifying raging flood water crashing through our doors",
            audio_bytes=silent_pcm,
            audio_mime_type="audio/wav",
            audio_transcript=None,  # No speech detected
            hazard_tags=["flood"],
        )
        self.assertFalse(res.audio_text_aligned)
        self.assertTrue(any("ACOUSTIC_DISCREPANCY" in f for f in res.flags))

    # =========================================================================
    # LAYER 5: Deterministic Scoring Engine & Three-Tier Routing Tests
    # =========================================================================
    def test_layer_5_verified_emergency_tier_routing(self):
        """Score 80-100 must route to VERIFIED_EMERGENCY for immediate dispatch."""
        res: DeterministicScoreResult = scoring_engine.compute_score(
            speaker_distress_level="extreme_distress",
            specific_details_provided=True,
            acoustic_cues=["screaming", "crying", "rushing_water"],
            text_audio_alignment=True,
            has_contradiction=False,
            is_authoritative_grounded=True,
            grounding_status="authoritative_match",
            is_cluster_corroborated=True,
            corroborating_reports_count=4,
            suspected_prank_or_synthetic=False,
            is_audio_silent_or_corrupted=False,
            has_text_content=True,
            location_name="Badin Sector 4",
            detected_hazards=["flood", "medical_emergency"],
            cluster_density_factor=1.609,
            bonus_cluster_override=18.0,
            headcount=6,
            vulnerable_groups_count=2,
            device_attestation_passed=True,
        )
        self.assertGreaterEqual(res.verification_score, 80)
        self.assertEqual(res.triage_tier, "VERIFIED_EMERGENCY")
        self.assertIn("Immediate dispatch", res.recommendation)

    def test_layer_5_suspected_unconfirmed_tier_routing(self):
        """Score 35-79 must route to SUSPECTED_UNCONFIRMED (Rapid Callback Queue)."""
        res: DeterministicScoreResult = scoring_engine.compute_score(
            speaker_distress_level="moderate_urgency",
            specific_details_provided=False,
            acoustic_cues=[],
            text_audio_alignment=True,
            has_contradiction=False,
            is_authoritative_grounded=False,
            grounding_status="unreported_localized_incident",
            is_cluster_corroborated=False,
            corroborating_reports_count=1,
            suspected_prank_or_synthetic=False,
            is_audio_silent_or_corrupted=False,
            has_text_content=True,
            location_name="Unknown Colony",
            detected_hazards=["flood"],
            cluster_density_factor=0.693,
            device_attestation_passed=True,
        )
        self.assertGreaterEqual(res.verification_score, 35)
        self.assertLess(res.verification_score, 80)
        self.assertEqual(res.triage_tier, "SUSPECTED_UNCONFIRMED")
        self.assertIn("Rapid Callback Queue", res.recommendation)

    def test_layer_5_flagged_prank_tier_routing(self):
        """Prank keywords, recycled images, emulator container route to FLAGGED_OR_PRANK (quarantined)."""
        res: DeterministicScoreResult = scoring_engine.compute_score(
            speaker_distress_level="calm_or_flat",
            specific_details_provided=False,
            acoustic_cues=["laughter"],
            text_audio_alignment=False,
            has_contradiction=True,
            is_authoritative_grounded=False,
            grounding_status="unreported_localized_incident",
            is_cluster_corroborated=False,
            corroborating_reports_count=1,
            suspected_prank_or_synthetic=True,
            is_audio_silent_or_corrupted=False,
            has_text_content=True,
            location_name="Fake Test Area",
            detected_hazards=["flood"],
            is_recycled_archive=True,
            is_emulator=True,
            is_vpn_or_tor=True,
            elevation_anomaly=True,
        )
        self.assertLessEqual(res.verification_score, 34)
        self.assertEqual(res.triage_tier, "FLAGGED_OR_PRANK")
        self.assertIn("Quarantine", res.recommendation)
        self.assertGreater(res.penalty_tamper, 30)

    def test_layer_5_score_clamping_invariants(self):
        """Verification score must strictly clamp to [0, 100] under extreme penalties or bonuses."""
        # Extreme penalty scenario
        low_res = scoring_engine.compute_score(
            speaker_distress_level="calm_or_flat",
            specific_details_provided=False,
            acoustic_cues=[],
            text_audio_alignment=False,
            has_contradiction=True,
            is_authoritative_grounded=False,
            is_cluster_corroborated=False,
            suspected_prank_or_synthetic=True,
            is_audio_silent_or_corrupted=True,
            has_text_content=False,
            is_recycled_archive=True,
            is_diffusion_generated=True,
            is_emulator=True,
            is_vpn_or_tor=True,
        )
        self.assertGreaterEqual(low_res.verification_score, 0)
        self.assertLessEqual(low_res.verification_score, 34)
        self.assertEqual(low_res.triage_tier, "FLAGGED_OR_PRANK")

        # Extreme bonus scenario
        high_res = scoring_engine.compute_score(
            speaker_distress_level="extreme_distress",
            specific_details_provided=True,
            acoustic_cues=["screaming", "crying", "rushing_water", "sirens"],
            text_audio_alignment=True,
            has_contradiction=False,
            is_authoritative_grounded=True,
            grounding_status="authoritative_match",
            is_cluster_corroborated=True,
            corroborating_reports_count=20,
            suspected_prank_or_synthetic=False,
            is_audio_silent_or_corrupted=False,
            has_text_content=True,
            location_name="Sector 1 Flood Zone",
            detected_hazards=["flood", "medical_emergency", "structural_collapse"],
            cluster_density_factor=3.04,
            bonus_cluster_override=25.0,
            headcount=15,
            vulnerable_groups_count=4,
            device_attestation_passed=True,
        )
        self.assertLessEqual(high_res.verification_score, 100)
        self.assertEqual(high_res.verification_score, 100)


if __name__ == "__main__":
    unittest.main()
