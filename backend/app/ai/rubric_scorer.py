"""
Deterministic Rubric Scoring Engine — Eliminates LLM score drift.

CRITICAL DESIGN RULE: Gemini NEVER outputs a numerical score.
Gemini's role is strictly bounded to structured feature extraction.
All scoring is performed by this pure-Python deterministic rubric.

The rubric converts categorical AI-extracted features + provenance signals
into a repeatable, auditable 0–100 integer score with full breakdown.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RubricBreakdown(BaseModel):
    """Full breakdown of how the deterministic score was computed."""
    base_score: int = 40
    hazard_severity_points: int = 0
    hazard_severity_input: str = "none"
    authenticity_penalty: int = 0
    authenticity_flags: List[str] = Field(default_factory=list)
    provenance_points: int = 0
    provenance_flags: List[str] = Field(default_factory=list)
    grounding_boost: int = 0
    grounding_label: str = "neutral"
    cross_modal_points: int = 0
    cross_modal_flags: List[str] = Field(default_factory=list)
    location_penalty: int = 0
    location_flags: List[str] = Field(default_factory=list)
    final_score: int = 40
    score_before_clamp: int = 40


class RubricResult(BaseModel):
    """Final result from the deterministic rubric scorer."""
    verification_score: int
    vulnerability_level: str  # "critical" | "high" | "medium" | "requires_human_triage" | "low"
    rubric_breakdown: Dict[str, Any]
    recommendation: str
    concise_report: str


# ── Hazard severity point table ──────────────────────────────────
HAZARD_SEVERITY_POINTS = {
    "critical": 35,
    "high": 25,
    "medium": 15,
    "low": 5,
    "none": 0,
}


class RubricScorer:
    """
    Pure deterministic scoring engine. No LLM calls. No randomness.
    Identical inputs always produce identical outputs.
    """

    def score(
        self,
        # From Gemini structured extraction
        hazard_severity: str = "none",
        scene_authenticity: Optional[Dict[str, Any]] = None,
        cross_modal_alignment: Optional[Dict[str, Any]] = None,
        detected_hazards: Optional[List[str]] = None,
        visual_distress_cues: Optional[List[str]] = None,
        # From Media Forensics Service
        media_source: str = "gallery_unverified",
        flag_location_spoof: bool = False,
        phash_duplicate_found: bool = False,
        # From Location Claim Verification
        flag_location_mismatch: bool = False,
        location_match_level: str = "exact",
        # From Asymmetric Grounding Engine
        grounding_boost: int = 0,
        grounding_label: str = "neutral",
        # Context
        location_name: str = "Unknown",
        has_media: bool = False,
    ) -> RubricResult:
        """
        Compute the deterministic verification score from categorical inputs.
        """
        scene_authenticity = scene_authenticity or {}
        cross_modal_alignment = cross_modal_alignment or {}
        detected_hazards = detected_hazards or []
        visual_distress_cues = visual_distress_cues or []

        breakdown = RubricBreakdown()

        # ── 1. Base Score (humanitarian fail-open baseline) ──
        score = breakdown.base_score  # 40

        # ── 2. Hazard Severity (from Gemini structured extraction) ──
        severity_key = hazard_severity.lower().strip() if hazard_severity else "none"
        severity_pts = HAZARD_SEVERITY_POINTS.get(severity_key, 0)
        score += severity_pts
        breakdown.hazard_severity_points = severity_pts
        breakdown.hazard_severity_input = severity_key

        # ── 3. Scene Authenticity (only evaluated when media is present) ──
        authenticity_penalty = 0
        authenticity_flags: List[str] = []

        if has_media:
            if scene_authenticity.get("is_screen_recording_or_printed_photo", False):
                authenticity_penalty -= 25
                authenticity_flags.append("screen_recording_or_printed_photo_detected")

            if scene_authenticity.get("synthetic_artifacts_detected", False):
                authenticity_penalty -= 15
                authenticity_flags.append("synthetic_artifacts_detected")

            if scene_authenticity.get("optical_flow_consistent") is False:
                authenticity_penalty -= 10
                authenticity_flags.append("optical_flow_inconsistent")

        score += authenticity_penalty
        breakdown.authenticity_penalty = authenticity_penalty
        breakdown.authenticity_flags = authenticity_flags

        # ── 4. Location Claim Verification ──
        loc_penalty = 0
        loc_flags: List[str] = []
        if flag_location_mismatch or location_match_level == "mismatch":
            loc_penalty -= 15
            loc_flags.append("gps_claimed_location_mismatch")
        elif location_match_level in ("exact", "neighborhood"):
            # Bonus for precise matching location claim
            score += 5
            loc_flags.append("location_claim_corroborated")

        score += loc_penalty
        breakdown.location_penalty = loc_penalty
        breakdown.location_flags = loc_flags

        # ── 5. Provenance Signals (from Media Forensics + Nonce) ──
        provenance_pts = 0
        provenance_flags: List[str] = []

        if not has_media or media_source in ("no_media", "none"):
            # Fair scoring: no media submitted -> no provenance penalty
            provenance_flags.append("no_media_narrative_mode")
        elif media_source == "live_camera":
            provenance_pts += 10
            provenance_flags.append("live_camera_nonce_verified")
        elif media_source == "gallery_unverified":
            provenance_pts -= 10
            provenance_flags.append("gallery_upload_unverified")

        if has_media and flag_location_spoof:
            provenance_pts -= 15
            provenance_flags.append("exif_gps_spoof_detected")

        if has_media and phash_duplicate_found:
            provenance_pts -= 20
            provenance_flags.append("perceptual_hash_duplicate_detected")

        score += provenance_pts
        breakdown.provenance_points = provenance_pts
        breakdown.provenance_flags = provenance_flags

        # ── 6. Grounding Boost (from Asymmetric Grounding Engine) ──
        # NOTE: grounding_boost is ALWAYS >= 0 (asymmetric design)
        clamped_boost = max(0, min(30, grounding_boost))
        score += clamped_boost
        breakdown.grounding_boost = clamped_boost
        breakdown.grounding_label = grounding_label

        # ── 7. Cross-Modal Alignment (from Gemini structured extraction) ──
        cross_pts = 0
        cross_flags: List[str] = []

        voice_matches = cross_modal_alignment.get("voice_transcript_matches_visuals")
        if voice_matches is True:
            cross_pts += 5
            cross_flags.append("voice_visual_corroborated")
        elif voice_matches is False:
            cross_pts -= 10
            cross_flags.append("voice_visual_discrepancy")
            discrepancy = cross_modal_alignment.get("discrepancy_explanation")
            if discrepancy:
                cross_flags.append(f"discrepancy: {str(discrepancy)[:100]}")
        elif not has_media and detected_hazards:
            # Corroborated text/voice claim without visual discrepancy
            cross_pts += 5
            cross_flags.append("narrative_hazard_aligned")

        score += cross_pts
        breakdown.cross_modal_points = cross_pts
        breakdown.cross_modal_flags = cross_flags

        # ── 8. Clamp to [0, 100] ──
        breakdown.score_before_clamp = score
        score = max(0, min(100, score))
        breakdown.final_score = score

        # ── 8. Vulnerability Classification ──
        has_authenticity_red_flags = len(authenticity_flags) > 0 or phash_duplicate_found
        
        if score >= 75:
            vulnerability = "critical"
        elif score >= 55:
            vulnerability = "high"
        elif score >= 35:
            vulnerability = "medium"
        elif not has_authenticity_red_flags:
            # Low score but no red flags → needs human review (fail-open)
            vulnerability = "requires_human_triage"
        else:
            vulnerability = "low"

        # ── 9. Generate Recommendation ──
        recommendation = self._generate_recommendation(vulnerability, detected_hazards)

        # ── 10. Generate Concise Report ──
        concise_report = self._generate_concise_report(
            score=score,
            vulnerability=vulnerability,
            location_name=location_name,
            breakdown=breakdown,
            detected_hazards=detected_hazards,
            has_media=has_media,
        )

        return RubricResult(
            verification_score=score,
            vulnerability_level=vulnerability,
            rubric_breakdown=breakdown.model_dump(),
            recommendation=recommendation,
            concise_report=concise_report,
        )

    def _generate_recommendation(self, vulnerability: str, detected_hazards: List[str]) -> str:
        """Generate actionable dispatch recommendation based on vulnerability level."""
        hazard_str = ", ".join(detected_hazards[:4]) if detected_hazards else "unspecified hazards"

        recommendations = {
            "critical": (
                f"IMMEDIATE DISPATCH REQUIRED: Life-safety threat verified ({hazard_str}). "
                f"Deploy emergency rescue team with specialized equipment and medical personnel."
            ),
            "high": (
                f"PRIORITY DISPATCH: Urgent response required ({hazard_str}). "
                f"Deploy rescue and evacuation assets to the affected area."
            ),
            "medium": (
                f"STANDARD RELIEF DISPATCH: Deploy field assessment and supply distribution unit. "
                f"Detected concerns: {hazard_str}."
            ),
            "requires_human_triage": (
                f"HUMAN TRIAGE REQUIRED: AI verification produced low confidence. "
                f"Report is NOT rejected — flagged for manual coordinator review. "
                f"Possible concerns: {hazard_str}."
            ),
            "low": (
                f"MONITORING QUEUE: Route to local municipal support; continuous monitoring advised. "
                f"Authenticity concerns detected alongside: {hazard_str}."
            ),
        }

        return recommendations.get(vulnerability, recommendations["requires_human_triage"])

    def _generate_concise_report(
        self,
        score: int,
        vulnerability: str,
        location_name: str,
        breakdown: RubricBreakdown,
        detected_hazards: List[str],
        has_media: bool,
    ) -> str:
        """Generate a structured concise verification report."""
        hazard_str = ", ".join(detected_hazards[:4]) if detected_hazards else "None detected"

        media_status = "Live Camera (Nonce Verified)" if "live_camera_nonce_verified" in breakdown.provenance_flags else "Gallery Upload"
        if not has_media:
            media_status = "No visual media provided"

        flags_summary = []
        if breakdown.authenticity_flags:
            flags_summary.append(f"⚠️ Authenticity: {', '.join(breakdown.authenticity_flags)}")
        prov_warnings = [f for f in breakdown.provenance_flags if f != "no_media_narrative_mode"]
        if prov_warnings:
            flags_summary.extend([f"🔒 {f}" for f in prov_warnings])
        if breakdown.location_flags:
            flags_summary.append(f"📍 {', '.join(breakdown.location_flags)}")

        report_lines = [
            f"ReliefPulse Verification Summary [{vulnerability.upper()} PRIORITY | Score: {score}/100]",
            f"Location: {location_name}",
            f"Primary Hazards: {hazard_str}",
            f"Hazard Severity: {breakdown.hazard_severity_input.replace('_', ' ').title()}",
            f"Environmental Grounding: {breakdown.grounding_label.replace('_', ' ').title()}",
            f"Evidence Capture: {media_status}",
        ]

        if flags_summary:
            report_lines.append(f"Field Telemetry Flags: {' | '.join(flags_summary[:3])}")

        return "\n".join(report_lines)


# Module-level singleton
rubric_scorer = RubricScorer()
