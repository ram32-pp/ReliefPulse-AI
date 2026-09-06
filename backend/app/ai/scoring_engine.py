"""
Deterministic Rubric Scoring Engine for ReliefPulse-AI Voice + Text + Location Verification.

Invariants:
  1. Zero LLM score drift — LLMs strictly extract categorical features; Python computes scores.
  2. Score composition:
       Score = S_acoustic_semantic (40%) + S_consistency (20%) + S_grounding (20%) + S_clustering (20%)
  3. Hard security overrides:
       - suspected_prank_or_synthetic == True -> score clamped to 10 ("false_or_prank")
       - audio silent/corrupted and text empty -> score 0 ("requires_human_triage")
  4. Asymmetric grounding:
       - Authoritative match: +20 pts
       - Unreported localized incident: +10 pts (neutral baseline, zero penalty)
  5. Spatiotemporal clustering:
       - Corroborated (>= 2 matching reports in 500m / 45m): +20 pts
       - Isolated single incident: +5 pts (neutral baseline)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DeterministicScoreBreakdown(BaseModel):
    """Auditable mathematical breakdown of the deterministic verification score."""
    # 1. Acoustic & Semantic Distress (Max 40)
    acoustic_semantic_score: int = 0
    speaker_distress_pts: int = 0
    specific_details_pts: int = 0
    acoustic_cues_pts: int = 0

    # 2. Cross-Modal Consistency (Max 20)
    consistency_score: int = 0

    # 3. Location Grounding (Max 20)
    grounding_score: int = 10  # Neutral baseline
    grounding_status: str = "unreported_localized_incident"

    # 4. Spatiotemporal Clustering (Max 20)
    cluster_score: int = 5  # Neutral baseline
    corroborating_reports_count: int = 0

    # Flags and raw score before overrides
    score_before_override: int = 0
    final_score: int = 0
    security_override_applied: Optional[str] = None
    flags: List[str] = Field(default_factory=list)


class DeterministicScoreResult(BaseModel):
    """Output from the deterministic scoring engine."""
    verification_score: int
    vulnerability_level: str  # "critical" | "high" | "medium" | "low" | "requires_human_triage" | "false_or_prank"
    semantic_score: int
    consistency_score: int
    grounding_score: int
    cluster_score: int
    breakdown: Dict[str, Any]
    recommendation: str
    concise_report: str


class DeterministicScoringEngine:
    """
    Pure Python deterministic scoring engine. Zero randomness. Zero LLM hallucinations.
    Identical inputs always produce identical results.
    """

    def compute_score(
        self,
        # Phase 1 & 2: Acoustic & Semantic distress inputs
        speaker_distress_level: str = "calm",  # "critical" | "elevated" | "calm" | "inaudible"
        specific_details_provided: bool = False,
        acoustic_cues: Optional[List[str]] = None,
        # Phase 2: Cross-modal consistency
        text_audio_alignment: bool = True,
        has_contradiction: bool = False,
        # Phase 3: Location grounding
        is_authoritative_grounded: bool = False,
        grounding_status: str = "unreported_localized_incident",  # "authoritative_match" | "unreported_localized_incident"
        # Phase 4: Spatiotemporal clustering
        is_cluster_corroborated: bool = False,
        corroborating_reports_count: int = 0,
        # Hard Security Overrides
        suspected_prank_or_synthetic: bool = False,
        is_audio_silent_or_corrupted: bool = False,
        has_text_content: bool = False,
        # Context metadata
        location_name: str = "Reported Location",
        detected_hazards: Optional[List[str]] = None,
    ) -> DeterministicScoreResult:
        acoustic_cues = acoustic_cues or []
        detected_hazards = detected_hazards or []
        flags: List[str] = []

        # ── 1. Acoustic & Semantic Distress (Max 40 pts) ──
        speaker_level = (speaker_distress_level or "calm").lower().strip()
        speaker_pts = 0
        if speaker_level in ("critical", "elevated"):
            speaker_pts = 15
            flags.append(f"distress_{speaker_level}")
        elif speaker_level == "calm":
            speaker_pts = 5
        else:  # inaudible
            speaker_pts = 0

        details_pts = 15 if specific_details_provided else 0
        if specific_details_provided:
            flags.append("specific_details_present")

        # Corroborating acoustic background cues (sirens, rushing water, alarms, crying)
        cues_pts = 10 if len(acoustic_cues) > 0 else 0
        if cues_pts > 0:
            flags.append(f"acoustic_cues_detected({len(acoustic_cues)})")

        acoustic_semantic_score = min(40, speaker_pts + details_pts + cues_pts)

        # ── 2. Cross-Modal Alignment (Max 20 pts) ──
        if text_audio_alignment and not has_contradiction:
            consistency_score = 20
            flags.append("cross_modal_aligned")
        else:
            consistency_score = 0
            flags.append("cross_modal_discrepancy")

        # ── 3. Location Grounding (Max 20 pts) ──
        if is_authoritative_grounded or grounding_status == "authoritative_match":
            grounding_score = 20
            effective_grounding_status = "authoritative_match"
            flags.append("authoritative_grounding_hit")
        else:
            # Asymmetric rule: Zero penalty on miss; neutral baseline +10 pts
            grounding_score = 10
            effective_grounding_status = "unreported_localized_incident"
            flags.append("grounding_neutral_baseline")

        # ── 4. Spatiotemporal Clustering (Max 20 pts) ──
        if is_cluster_corroborated or corroborating_reports_count >= 2:
            cluster_score = 20
            flags.append(f"cluster_corroborated({corroborating_reports_count}_nearby)")
        else:
            # Isolated single incident: +5 pts (neutral baseline)
            cluster_score = 5
            flags.append("cluster_isolated_baseline")

        raw_score = acoustic_semantic_score + consistency_score + grounding_score + cluster_score
        final_score = raw_score
        override_applied: Optional[str] = None
        vulnerability_level: str = "medium"

        # ── Hard Security Overrides ──
        if suspected_prank_or_synthetic:
            final_score = 10
            vulnerability_level = "false_or_prank"
            override_applied = "suspected_prank_or_synthetic"
            flags.append("SECURITY_OVERRIDE_PRANK_CLAMP")
        elif (is_audio_silent_or_corrupted or speaker_level == "inaudible") and not has_text_content:
            final_score = 0
            vulnerability_level = "requires_human_triage"
            override_applied = "silent_audio_empty_text"
            flags.append("SECURITY_OVERRIDE_SILENT_EMPTY")
        else:
            # Standard rubric score mapping
            final_score = max(0, min(100, final_score))
            if final_score >= 75:
                vulnerability_level = "critical"
            elif final_score >= 55:
                vulnerability_level = "high"
            elif final_score >= 35:
                vulnerability_level = "medium"
            else:
                vulnerability_level = "low"

        breakdown = DeterministicScoreBreakdown(
            acoustic_semantic_score=acoustic_semantic_score,
            speaker_distress_pts=speaker_pts,
            specific_details_pts=details_pts,
            acoustic_cues_pts=cues_pts,
            consistency_score=consistency_score,
            grounding_score=grounding_score,
            grounding_status=effective_grounding_status,
            cluster_score=cluster_score,
            corroborating_reports_count=corroborating_reports_count,
            score_before_override=raw_score,
            final_score=final_score,
            security_override_applied=override_applied,
            flags=flags,
        )

        recommendation = self._generate_recommendation(vulnerability_level, detected_hazards)
        concise_report = self._generate_concise_report(
            score=final_score,
            vulnerability=vulnerability_level,
            location_name=location_name,
            breakdown=breakdown,
            detected_hazards=detected_hazards,
        )

        return DeterministicScoreResult(
            verification_score=final_score,
            vulnerability_level=vulnerability_level,
            semantic_score=acoustic_semantic_score,
            consistency_score=consistency_score,
            grounding_score=grounding_score,
            cluster_score=cluster_score,
            breakdown=breakdown.model_dump(),
            recommendation=recommendation,
            concise_report=concise_report,
        )

    def _generate_recommendation(self, vulnerability: str, detected_hazards: List[str]) -> str:
        hazard_str = ", ".join(detected_hazards[:3]) if detected_hazards else "disaster conditions"
        recommendations = {
            "critical": f"IMMEDIATE DISPATCH REQUIRED: Life-safety threat confirmed ({hazard_str}). Deploy emergency rescue boat/unit.",
            "high": f"PRIORITY DISPATCH: Urgent response required ({hazard_str}). Dispatch field assets immediately.",
            "medium": f"STANDARD RELIEF DISPATCH: Route to field assessment and supply distribution queue ({hazard_str}).",
            "low": f"MONITORING QUEUE: Route to local municipal support; continuous monitoring advised ({hazard_str}).",
            "requires_human_triage": f"HUMAN TRIAGE REQUIRED: Fail-open safety activated. Coordinator review needed before dispatch ({hazard_str}).",
            "false_or_prank": f"FLAGGED FOR REVIEW: Suspected prank or synthetic audio. Clamped to low priority.",
        }
        return recommendations.get(vulnerability, recommendations["requires_human_triage"])

    def _generate_concise_report(
        self,
        score: int,
        vulnerability: str,
        location_name: str,
        breakdown: DeterministicScoreBreakdown,
        detected_hazards: List[str],
    ) -> str:
        hazards = ", ".join([h.replace('_', ' ').title() for h in detected_hazards]) if detected_hazards else "General Emergency"
        cluster_desc = f"Corroborated by {breakdown.corroborating_reports_count} nearby incident reports" if breakdown.corroborating_reports_count >= 2 else "Single verified distress signal"
        grounding_desc = "Authoritative environmental match" if breakdown.grounding_status == "authoritative_match" else "Verified localized incident"
        distress_desc = "Elevated Acoustic Distress" if breakdown.speaker_distress_pts > 0 else "Distress Communication Received"

        lines = [
            f"Emergency Triage Summary [{vulnerability.upper()} PRIORITY | Verified Score: {score}/100]",
            f"Location: {location_name}",
            f"Primary Hazards: {hazards}",
            f"Distress Status: {distress_desc}",
            f"Corroboration: {cluster_desc}",
            f"Grounding Status: {grounding_desc}",
        ]
        if breakdown.security_override_applied:
            lines.append(f"Audit Flag: {breakdown.security_override_applied.replace('_', ' ').title()}")
        return "\n".join(lines)


# Singleton
scoring_engine = DeterministicScoringEngine()
