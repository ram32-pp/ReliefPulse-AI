"""
RELIEFPULSE-AI // MULTI-DIALECT RESCUE TRIAGE & FORENSIC VERIFICATION TEST SUITE
Acceptance verification across all 7 regional Pakistani languages,
strict numeric disambiguation, adversarial prank forensics, and fail-open life-safety invariants.
"""

import sys
import os
import asyncio
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.triage_engine import (
    process_emergency_broadcast,
    MasterTriagePayload,
    _heuristic_multi_dialect_triage,
)


class TestMultiDialectTriageEngine(unittest.IsolatedAsyncioTestCase):

    async def test_saraiki_golden_anchor_complex_vulnerability(self):
        """
        Golden Few-Shot Anchor 1: Saraiki flash flood with mud structure collapse,
        7ft water depth disambiguation, 6 victims (2 kids, 1 paralyzed grandmother, adults).
        """
        raw_input = (
            "ٻچا گھنو بھائی خدارا! جھوک ٻُݙ ڳئی ہے، پاݨی سر کنوں لنگھ ڳئے، 7 فٹ پاݨی ہے گلی وچ۔ "
            "اساں 6 جݨے کوٹھے تے ٻیٹھے ہیں، 2 نکے ٻال ہن تے ہک مائی بڈھڑی ہے جینکوں فالج ہے۔ "
            "کچی کندھ ڈھاہ پئی ہے، کوٹھا کسے ویلے وی ٻُݙ ویسی۔ ٻیڑی بھیجو!"
        )

        result: MasterTriagePayload = await process_emergency_broadcast(raw_input)

        # 1. Linguistic Detection
        self.assertEqual(result.ingestion_metadata.detected_language, "Saraiki")
        self.assertIn("Derawali", result.ingestion_metadata.detected_dialect_variant)

        # 2. Forensic Authenticity
        self.assertEqual(result.forensic_verification.report_authenticity_verdict, "GENUINE_EMERGENCY")
        self.assertFalse(result.forensic_verification.adversarial_prank_detected)
        self.assertGreaterEqual(result.forensic_verification.confidence_score, 0.90)

        # 3. Numeric Disambiguation (7ft water depth != headcount)
        self.assertEqual(result.spatial_and_tactical_intelligence.water_depth_estimate_feet, 7.0)
        self.assertEqual(result.headcount_matrix.total_estimated_victims, 6)
        self.assertEqual(result.headcount_matrix.demographic_breakdown.infants_and_children, 2)
        self.assertEqual(result.headcount_matrix.demographic_breakdown.elderly_individuals, 1)
        self.assertEqual(result.headcount_matrix.demographic_breakdown.critically_injured_or_sick, 1)

        # 4. Physical Plausibility & Triage Scoring
        self.assertEqual(result.spatial_and_tactical_intelligence.immediate_physical_position, "roof")
        self.assertGreaterEqual(result.triage_scoring.severity_score, 90)
        self.assertEqual(result.triage_scoring.urgency_level, "CRITICAL")
        self.assertTrue(result.triage_scoring.life_safety_threat_confirmed)

        # 5. Pipeline Dictionary Integration
        vdict = result.to_verification_dict()
        self.assertEqual(vdict["headcount"], 6)
        self.assertEqual(vdict["triage_tier"], "genuine_emergency")
        self.assertIn("mud_roof_destabilization", result.triage_scoring.secondary_hazards)

    async def test_prank_golden_anchor_hard_clamp(self):
        """
        Golden Few-Shot Anchor 2: Malicious prank with fake claims, laughter, meme tokens,
        and channel promotion. Must clamp severity <= 10 and quarantine report.
        """
        raw_input = (
            "Oye bachao bachao! Hahaha flood aa gaya bhai ham mar gaye 500 log doob gaye "
            "hamari billi bhi mar gayi prank call challenge subscribe to my channel testing 123"
        )

        result: MasterTriagePayload = await process_emergency_broadcast(raw_input)

        # 1. Forensic Verification & Prank Detection
        self.assertTrue(result.forensic_verification.adversarial_prank_detected)
        self.assertEqual(result.forensic_verification.report_authenticity_verdict, "QUARANTINED_PRANK")

        # 2. Deterministic Safety Clamping
        self.assertLessEqual(result.triage_scoring.severity_score, 10)
        self.assertEqual(result.triage_scoring.urgency_level, "LOW")
        self.assertFalse(result.triage_scoring.life_safety_threat_confirmed)

        # 3. Headcount Clamped
        self.assertEqual(result.headcount_matrix.total_estimated_victims, 0)
        self.assertIn("DO NOT DISPATCH", result.standardized_english_intelligence.actionable_dispatch_command)

        # 4. Pipeline Integration Mapping
        vdict = result.to_verification_dict()
        self.assertTrue(vdict["suspected_prank_or_synthetic"])
        self.assertEqual(vdict["vulnerability_level"], "false_or_prank")

    async def test_sindhi_perso_arabic_and_roman(self):
        """Sindhi: Tests Perso-Arabic script and Roman Sindhi phonetics."""
        # Perso-Arabic
        sindhi_arabic = "مدد گهرجي! پاڻي چڙهي ويو آهي، ڇت تي چڙهيل آهيون، 5 ماڻهو، 2 ٻارڙا آهن بچايو"
        res1 = await process_emergency_broadcast(sindhi_arabic)
        self.assertEqual(res1.ingestion_metadata.detected_language, "Sindhi")
        self.assertEqual(res1.forensic_verification.report_authenticity_verdict, "GENUINE_EMERGENCY")
        self.assertEqual(res1.headcount_matrix.total_estimated_victims, 5)
        self.assertEqual(res1.headcount_matrix.demographic_breakdown.infants_and_children, 2)
        self.assertEqual(res1.spatial_and_tactical_intelligence.immediate_physical_position, "roof")

        # Roman Sindhi
        sindhi_roman = "Bachayo! Bodh achi vayi, pani charhi viyo, 4 jannay chhat te charhyal ahyun, kandhi tuti payi"
        res2 = await process_emergency_broadcast(sindhi_roman)
        self.assertEqual(res2.ingestion_metadata.detected_language, "Sindhi")
        self.assertEqual(res2.forensic_verification.report_authenticity_verdict, "GENUINE_EMERGENCY")
        self.assertEqual(res2.headcount_matrix.total_estimated_victims, 4)

    async def test_pashto_vulnerabilities(self):
        """Pashto: Tests Northern/Southern Pashto, wall collapse, and pregnant woman vulnerability."""
        pashto_text = "مرسته وکړئ! سېلاب راغلی، دیوال نړېدلی دی، 5 کسان ايسار يو، 2 ماشومان او اميندواره مېرمن شته"
        res = await process_emergency_broadcast(pashto_text)

        self.assertEqual(res.ingestion_metadata.detected_language, "Pashto")
        self.assertEqual(res.forensic_verification.report_authenticity_verdict, "GENUINE_EMERGENCY")
        self.assertEqual(res.headcount_matrix.total_estimated_victims, 5)
        self.assertEqual(res.headcount_matrix.demographic_breakdown.infants_and_children, 2)
        self.assertEqual(res.headcount_matrix.demographic_breakdown.pregnant_women, 1)
        self.assertEqual(res.triage_scoring.urgency_level, "CRITICAL")

    async def test_punjabi_electrocution_hazard(self):
        """Punjabi: Tests Shahmukhi Punjabi with secondary hazard of electrocution ('current paya phailda')."""
        punjabi_text = "بچاؤ سانوں رب دا واسطہ! چھت ڈھے پئی، کرنٹ پیا پھیلدا، 6 بندے پھنس گئے آں، 3 نکے نکے بال نیں"
        res = await process_emergency_broadcast(punjabi_text)

        self.assertEqual(res.ingestion_metadata.detected_language, "Punjabi")
        self.assertEqual(res.forensic_verification.report_authenticity_verdict, "GENUINE_EMERGENCY")
        self.assertEqual(res.headcount_matrix.total_estimated_victims, 6)
        self.assertEqual(res.headcount_matrix.demographic_breakdown.infants_and_children, 3)
        self.assertIn("exposed_high_tension_wire", res.triage_scoring.secondary_hazards)

    async def test_balochi_flood_deluge(self):
        """Balochi: Tests Balochi 'Haar aathkag' (deluge), trapped 'maa geer trathagen', children/women."""
        balochi_text = "کمک بہ کناں! ہار اتکگ، آپ زیات بوتگ، لوگ تہا آپ شتگ، ما 4 مردم گیر ترتگیں، چُک ءُ زالبول"
        res = await process_emergency_broadcast(balochi_text)

        self.assertEqual(res.ingestion_metadata.detected_language, "Balochi")
        self.assertEqual(res.forensic_verification.report_authenticity_verdict, "GENUINE_EMERGENCY")
        self.assertEqual(res.headcount_matrix.total_estimated_victims, 4)
        self.assertEqual(res.triage_scoring.primary_hazard_classification, "flash_flood")

    async def test_brahui_inundation(self):
        """Brahui: Tests Brahui 'Deer ura ti basne', 'Nan geeraam masnan', 'chuna ta haal kharab'."""
        brahui_text = "کمک کبو! دیر اُرا ٹی بسنے، نن گیرام مسنن، 5 بندغ نن بپتن، چُنا تا حال خراب ءِ"
        res = await process_emergency_broadcast(brahui_text)

        self.assertEqual(res.ingestion_metadata.detected_language, "Brahui")
        self.assertEqual(res.forensic_verification.report_authenticity_verdict, "GENUINE_EMERGENCY")
        self.assertEqual(res.headcount_matrix.total_estimated_victims, 5)

    async def test_hindko_roof_trap(self):
        """Hindko: Tests Hindko 'Kothe te charhe aan', 'makaan dheh piya', 'paani bohta charh gya'."""
        hindko_text = "مدد کرو جی! مکان ڈھیہہ پیا، کوٹھے تے چڑھے آں، 4 بندے آں، 2 نکے بال ہن، پانی بوہتا چڑھ گیا"
        res = await process_emergency_broadcast(hindko_text)

        self.assertEqual(res.ingestion_metadata.detected_language, "Hindko")
        self.assertEqual(res.forensic_verification.report_authenticity_verdict, "GENUINE_EMERGENCY")
        self.assertEqual(res.headcount_matrix.total_estimated_victims, 4)
        self.assertEqual(res.spatial_and_tactical_intelligence.immediate_physical_position, "roof")

    async def test_strict_numeric_disambiguation_pipeline(self):
        """
        Numeric Disambiguation:
        Input contains Street number (4), Sector (G-11), water depth (6 foot), time (3 ghantay),
        and victim headcount (7 afraad, 2 bache, 1 buzurg).
        MUST NOT confuse address, depth, or duration with headcount!
        """
        complex_numeric_text = (
            "Sector G-11, Street 4 mein 6 foot paani khara hai. 3 ghantay se phansay hain. "
            "Hum 7 afraad hain, jin mein 2 bache aur 1 buzurg shamil hain. Chhat par hain."
        )

        res = await process_emergency_broadcast(complex_numeric_text)

        # Depth isolated
        self.assertEqual(res.spatial_and_tactical_intelligence.water_depth_estimate_feet, 6.0)

        # Headcount isolated (7 total, 2 kids, 1 elderly, 4 adults)
        self.assertEqual(res.headcount_matrix.total_estimated_victims, 7)
        self.assertEqual(res.headcount_matrix.demographic_breakdown.infants_and_children, 2)
        self.assertEqual(res.headcount_matrix.demographic_breakdown.elderly_individuals, 1)
        self.assertEqual(res.headcount_matrix.demographic_breakdown.uninjured_adults, 4)

        # Position isolated
        self.assertEqual(res.spatial_and_tactical_intelligence.immediate_physical_position, "roof")

    async def test_asymmetric_life_safety_fail_open_on_fragmented_audio(self):
        """
        Operating Principle: Asymmetric Life-Safety Invariant (Fail-Open).
        Chaotic, panicky, low-bandwidth fragmented input must NEVER be quarantined as a prank.
        """
        fragmented_distress = "madad... paani... aa gaya... toot gaya... koi suno... bachao!"

        res = await process_emergency_broadcast(fragmented_distress)

        self.assertFalse(res.forensic_verification.adversarial_prank_detected)
        self.assertNotEqual(res.forensic_verification.report_authenticity_verdict, "QUARANTINED_PRANK")
        self.assertIn(res.forensic_verification.report_authenticity_verdict, ["GENUINE_EMERGENCY", "SUSPECTED_UNCONFIRMED"])
        self.assertGreaterEqual(res.triage_scoring.severity_score, 60)
        self.assertIn(res.triage_scoring.urgency_level, ["HIGH", "CRITICAL"])
        self.assertTrue(res.triage_scoring.life_safety_threat_confirmed)


if __name__ == "__main__":
    unittest.main()
