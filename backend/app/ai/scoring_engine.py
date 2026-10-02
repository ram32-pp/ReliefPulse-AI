r"""
Deterministic Rubric & 5-Layer Multi-Factor Scoring Engine for ReliefPulse-AI.

5-Layer Architecture:
  Layer 1: Hardware & Network Attestation (DeviceCheck / Play Integrity / IP-GPS / Tor / VPN)
  Layer 2: Spatiotemporal Multi-Witness Consensus (Cluster Density Cd = ln(1 + N_unique))
  Layer 3: Visual & Media Forensics Engine (pHash / Recycled Archives / Diffusion AI detection)
  Layer 4: Multi-Modal Semantic Consistency (Spectrogram energy / DEM Topography sanity)
  Layer 5: Bayesian Risk & Uncertainty Classifier (Three-Tier Routing: VERIFIED / SUSPECTED / FLAGGED)

Formula:
  S = clamp( \sum w_i F_i + Bonus_cluster - Penalty_tamper - Penalty_evidence_gap, 0, 100 )
    w_acoustic      = 0.25 (Voice stress + disaster acoustic sound detection)
    w_semantic      = 0.25 (Multi-modal detail specificity, medical vulnerability, exact headcount)
    w_cluster       = 0.25 (Spatial density / independent multi-device reports in 500m radius)
    w_environmental = 0.15 (Real-time radar rainfall, USGS seismic, flood telemetry)
    w_device        = 0.10 (Hardware attestation and non-VPN IP-GPS terrestrial match)

Three-Tier Routing:
  Score 80 - 100 : VERIFIED_EMERGENCY     -> Immediate Dispatch Advice
  Score 35 - 79  : SUSPECTED_UNCONFIRMED  -> Rapid Callback Queue (Automated SMS/IVR verification)
  Score 0  - 34  : FLAGGED_OR_PRANK       -> Quarantined to Coordinator Audit View

CRITICAL DESIGN FIX (v5.0):
  - Legacy fallback REMOVED. All scoring now uses the 5-layer multi-factor formula.
  - Asymmetric baselines: absence of evidence = 0 (not neutral passing grades).
  - Evidence quality penalty: text-only reports without audio/visual/swarm corroboration
    are capped at SUSPECTED_UNCONFIRMED regardless of score.
  - Text-only distress capped at "elevated" (only audio can confirm "critical").
"""

import math
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field


class DeterministicScoreBreakdown(BaseModel):
    """Auditable mathematical breakdown of the deterministic verification score."""
    # 5-Layer Multi-Factor Components (primary scoring system)
    f_acoustic: float = 0.0
    f_semantic: float = 0.0
    f_cluster: float = 0.0
    f_environmental: float = 0.0
    f_device: float = 50.0
    bonus_cluster: float = 0.0
    penalty_tamper: float = 0.0
    penalty_evidence_gap: float = 0.0
    cluster_density_factor: float = 0.0
    triage_tier: str = "SUSPECTED_UNCONFIRMED"

    # Evidence quality tracking
    has_audio_evidence: bool = False
    has_visual_evidence: bool = False
    has_swarm_corroboration: bool = False
    has_grounding_match: bool = False
    evidence_modalities_count: int = 0

    # Component detail for audit trail
    speaker_distress_pts: int = 0
    specific_details_pts: int = 0
    acoustic_cues_pts: int = 0
    consistency_score: int = 0
    grounding_score: int = 0
    cluster_score: int = 0

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

    # 5-Layer Extensions
    triage_tier: Literal["VERIFIED_EMERGENCY", "SUSPECTED_UNCONFIRMED", "FLAGGED_OR_PRANK"] = "SUSPECTED_UNCONFIRMED"
    cluster_density_factor: float = 0.0
    bonus_cluster: float = 0.0
    penalty_tamper: float = 0.0
    device_integrity_score: int = 50


class DeterministicScoringEngine:
    """
    Pure Python deterministic scoring engine implementing the 5-layer emergency verification architecture.
    Zero LLM score drift. Zero hallucinations.

    v5.0 CRITICAL FIXES:
    - Always uses 5-layer formula (legacy fallback removed).
    - Asymmetric baselines: no evidence = 0 score for that axis (not inflated neutral).
    - Evidence-quality gating: text-only reports capped at SUSPECTED_UNCONFIRMED.
    - Text-only distress capped at "elevated" (critical requires audio confirmation).
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
        # 5-Layer Explicit Factor Overrides / Inputs
        f_acoustic_override: Optional[float] = None,
        f_semantic_override: Optional[float] = None,
        f_cluster_override: Optional[float] = None,
        f_environmental_override: Optional[float] = None,
        f_device_override: Optional[float] = None,
        cluster_density_factor: Optional[float] = None,
        bonus_cluster_override: Optional[float] = None,
        penalty_tamper_override: Optional[float] = None,
        # Forensic & Attestation Flags
        is_recycled_archive: bool = False,
        is_diffusion_generated: bool = False,
        is_vpn_or_tor: bool = False,
        is_emulator: bool = False,
        elevation_anomaly: bool = False,
        device_attestation_passed: bool = True,
        ip_gps_distance_km: Optional[float] = None,
        headcount: int = 1,
        vulnerable_groups_count: int = 0,
        # NEW: Evidence modality flags (v5.0)
        has_audio_evidence: bool = False,
        has_visual_evidence: bool = False,
        is_text_only: bool = False,
    ) -> DeterministicScoreResult:
        acoustic_cues = acoustic_cues or []
        detected_hazards = detected_hazards or []
        flags: List[str] = []

        # ── Determine evidence modalities present ──
        # Infer is_text_only if not explicitly set
        if not has_audio_evidence and not has_visual_evidence:
            is_text_only = True

        evidence_modalities = 0
        if has_audio_evidence:
            evidence_modalities += 1
        if has_visual_evidence:
            evidence_modalities += 1
        if has_text_content:
            evidence_modalities += 1

        has_swarm = is_cluster_corroborated or corroborating_reports_count >= 2
        has_grounding = is_authoritative_grounded or grounding_status == "authoritative_match"

        if has_swarm:
            evidence_modalities += 1
        if has_grounding:
            evidence_modalities += 1

        # ── 1. Distress Level Normalization ──
        # FIX: Text-only reports cap at "elevated". Only audio can confirm "critical".
        speaker_level = (speaker_distress_level or "calm").lower().strip()
        if is_text_only and speaker_level == "critical":
            speaker_level = "elevated"
            flags.append("distress_downgraded_text_only(critical->elevated)")

        speaker_pts = 0
        if speaker_level == "critical":
            speaker_pts = 15
            flags.append("distress_critical_audio_confirmed")
        elif speaker_level == "elevated":
            speaker_pts = 10
            flags.append("distress_elevated")
        elif speaker_level == "calm":
            speaker_pts = 3
        else:  # inaudible
            speaker_pts = 0

        details_pts = 15 if specific_details_provided else 0
        if specific_details_provided:
            flags.append("specific_details_present")

        cues_pts = 10 if len(acoustic_cues) > 0 else 0
        if cues_pts > 0:
            flags.append(f"acoustic_cues_detected({len(acoustic_cues)})")

        acoustic_semantic_score = min(40, speaker_pts + details_pts + cues_pts)

        # FIX: text_audio_alignment only counts if audio was actually present
        if has_audio_evidence and text_audio_alignment and not has_contradiction:
            consistency_score = 20
            flags.append("cross_modal_aligned_audio_verified")
        elif has_audio_evidence and (not text_audio_alignment or has_contradiction):
            consistency_score = 0
            flags.append("cross_modal_discrepancy")
        else:
            # No audio → alignment is UNVERIFIED (not assumed true)
            consistency_score = 5
            flags.append("cross_modal_unverified_no_audio")

        if has_grounding:
            grounding_score = 20
            effective_grounding_status = "authoritative_match"
            flags.append("authoritative_grounding_hit")
        else:
            grounding_score = 5  # Reduced from 10 — neutral is lower
            effective_grounding_status = "unreported_localized_incident"
            flags.append("grounding_neutral_baseline")

        if has_swarm:
            cluster_score = 20
            flags.append(f"cluster_corroborated({corroborating_reports_count}_nearby)")
        else:
            cluster_score = 0  # FIX: Solo report = 0 cluster credit (was 5)
            flags.append("cluster_isolated_no_corroboration")

        # ── 2. 5-Layer Multi-Factor Computation (ALWAYS used, no legacy fallback) ──

        # F_acoustic (w = 0.25): Voice stress + acoustic sound detection (0-100)
        if f_acoustic_override is not None:
            f_acoustic = float(f_acoustic_override)
        else:
            if has_audio_evidence:
                # Audio present: full acoustic scoring
                base_distress = 70.0 if speaker_level == "critical" else (50.0 if speaker_level == "elevated" else (15.0 if speaker_level == "calm" else 0.0))
                cue_bonus = min(30.0, len(acoustic_cues) * 15.0)
                f_acoustic = min(100.0, base_distress + cue_bonus)
            else:
                # FIX: Text-only — acoustic score from text keyword extraction only (much lower)
                # Text can hint at distress but cannot confirm acoustic reality
                base_distress = 30.0 if speaker_level == "elevated" else (10.0 if speaker_level == "calm" else 0.0)
                # Text-derived "cues" (keyword matches) get reduced weight
                cue_bonus = min(15.0, len(acoustic_cues) * 5.0)
                f_acoustic = min(50.0, base_distress + cue_bonus)  # Capped at 50 for text-only
                flags.append("acoustic_text_only_cap_50")

        # F_semantic (w = 0.25): Detail specificity + consistency + headcount/vulnerability (0-100)
        if f_semantic_override is not None:
            f_semantic = float(f_semantic_override)
        else:
            det_val = 35.0 if specific_details_provided else 5.0
            # FIX: Alignment only counts when verified by actual audio cross-check
            if has_audio_evidence:
                align_val = 35.0 if (text_audio_alignment and not has_contradiction) else 0.0
            else:
                align_val = 10.0  # Baseline for text-only (was 40 — massive inflation)
            vuln_val = 20.0 if (headcount > 1 or vulnerable_groups_count > 0 or len(detected_hazards) >= 2) else 5.0
            f_semantic = min(100.0, det_val + align_val + vuln_val)

        # F_cluster (w = 0.25): Swarm corroboration (0-100)
        # FIX: Solo report = 0 (was 25). The whole point of cluster scoring is independent corroboration.
        if f_cluster_override is not None:
            f_cluster = float(f_cluster_override)
        else:
            if is_cluster_corroborated or corroborating_reports_count >= 3:
                f_cluster = 100.0
            elif corroborating_reports_count == 2:
                f_cluster = 75.0
            elif corroborating_reports_count == 1:
                f_cluster = 35.0
            else:
                f_cluster = 0.0  # FIX: Solo = 0 (was 25)
                flags.append("cluster_zero_no_corroboration")

        # F_environmental (w = 0.15): Grounding & Environmental telemetry (0-100)
        # FIX: Asymmetric design means absence = 0, presence = boost. 50 was NOT neutral.
        if f_environmental_override is not None:
            f_environmental = float(f_environmental_override)
        else:
            if has_grounding:
                f_environmental = 100.0
                flags.append("environmental_authority_confirmed")
            else:
                # FIX: True asymmetric neutral = 0, not 50
                f_environmental = 0.0
                flags.append("environmental_no_match_neutral_zero")

        # F_device (w = 0.10): Hardware attestation and non-VPN IP-GPS match (0-100)
        # FIX: No attestation data = 50 (uncertain), not 100 (perfect)
        if f_device_override is not None:
            f_device = float(f_device_override)
        else:
            if device_attestation_passed and not is_emulator and not is_vpn_or_tor:
                # Check if we actually have attestation data or just defaults
                has_real_attestation = (ip_gps_distance_km is not None) or is_emulator or is_vpn_or_tor or not device_attestation_passed
                if has_real_attestation:
                    dev_score = 100.0  # Verified clean device
                    flags.append("device_attestation_verified")
                else:
                    dev_score = 50.0  # FIX: No data = uncertain (was 100)
                    flags.append("device_attestation_no_data_baseline")
            else:
                dev_score = 100.0
                if is_emulator:
                    dev_score -= 50.0
                    flags.append("device_emulator_detected")
                if not device_attestation_passed:
                    dev_score -= 30.0
                    flags.append("device_attestation_unverified")
                if is_vpn_or_tor:
                    dev_score -= 40.0
                    flags.append("network_vpn_or_tor_detected")
                if ip_gps_distance_km is not None and ip_gps_distance_km > 50.0:
                    dev_score -= 35.0
                    flags.append(f"ip_gps_distance_exceeded({ip_gps_distance_km:.1f}km)")
            f_device = max(0.0, dev_score)

        # Cluster Density Factor Cd = ln(1 + N_unique_devices)
        if cluster_density_factor is None:
            cluster_density_factor = math.log(1.0 + max(0, corroborating_reports_count))

        # Bonus_cluster = heavy multiplier based on swarm co-location
        if bonus_cluster_override is not None:
            bonus_cluster = float(bonus_cluster_override)
        else:
            # FIX: Only award cluster bonus when there IS actual swarm consensus
            if corroborating_reports_count >= 2:
                bonus_cluster = min(25.0, cluster_density_factor * 12.0)
            else:
                bonus_cluster = 0.0  # FIX: No solo-report bonus (was ln(2)*12 ≈ 8.3)

        # Penalty_tamper: Recycled image, diffusion AI, synthetic audio, or elevation anomaly
        if penalty_tamper_override is not None:
            penalty_tamper = float(penalty_tamper_override)
        else:
            penalty_tamper = 0.0
            if is_recycled_archive:
                penalty_tamper += 35.0
                flags.append("tamper_recycled_disaster_archive")
            if is_diffusion_generated:
                penalty_tamper += 50.0
                flags.append("tamper_diffusion_ai_mockup")
            if suspected_prank_or_synthetic:
                penalty_tamper += 50.0
                flags.append("tamper_synthetic_voice_or_prank_payload")
            if elevation_anomaly:
                penalty_tamper += 30.0
                flags.append("tamper_elevation_anomaly_ridge_flood")
            if is_emulator and is_vpn_or_tor:
                penalty_tamper += 30.0
                flags.append("tamper_sybil_emulator_vpn_combo")

        # NEW: Evidence gap penalty — penalizes reports lacking multi-modal corroboration
        # Asymmetric: grounded reports get reduced penalty (confirmed disaster → plausible reporter)
        penalty_evidence_gap = 0.0
        if is_text_only and not has_swarm and not has_grounding:
            # Text-only, solo, ungrounded report: highest evidence gap penalty
            penalty_evidence_gap = 15.0
            flags.append("evidence_gap_text_only_solo_ungrounded")
        elif is_text_only and not has_swarm and has_grounding:
            # Text-only, solo, but grounded by authoritative source (e.g., USGS confirms earthquake)
            # Reduced penalty: disaster is confirmed, reporter plausibility is higher
            penalty_evidence_gap = 5.0
            flags.append("evidence_gap_text_only_grounded_reduced")
        elif is_text_only and has_swarm:
            # Text-only but multiple witnesses — low penalty
            penalty_evidence_gap = 3.0
            flags.append("evidence_gap_text_only_swarm_corroborated")
        elif not has_audio_evidence and not has_visual_evidence and has_swarm:
            penalty_evidence_gap = 0.0  # Swarm corroboration alone is strong evidence

        # ── Weighted multi-factor formula (ALWAYS used — no legacy fallback) ──
        # S = clamp( sum(w_i * F_i) + Bonus_cluster - Penalty_tamper - Penalty_evidence_gap, 0, 100 )
        weighted_sum = (
            0.25 * f_acoustic +
            0.25 * f_semantic +
            0.25 * f_cluster +
            0.15 * f_environmental +
            0.10 * f_device
        )
        calculated_score = int(round(max(0.0, min(100.0,
            weighted_sum + bonus_cluster - penalty_tamper - penalty_evidence_gap
        ))))

        override_applied: Optional[str] = None
        vulnerability_level: str = "medium"
        triage_tier: Literal["VERIFIED_EMERGENCY", "SUSPECTED_UNCONFIRMED", "FLAGGED_OR_PRANK"] = "SUSPECTED_UNCONFIRMED"

        # ── Hard Security Overrides ──
        if suspected_prank_or_synthetic or is_diffusion_generated or is_recycled_archive:
            final_score = 10
            vulnerability_level = "false_or_prank"
            triage_tier = "FLAGGED_OR_PRANK"
            override_applied = "suspected_prank_or_synthetic"
            flags.append("SECURITY_OVERRIDE_PRANK_CLAMP")
        elif (is_audio_silent_or_corrupted or speaker_level == "inaudible") and not has_text_content:
            final_score = 0
            vulnerability_level = "requires_human_triage"
            triage_tier = "SUSPECTED_UNCONFIRMED"
            override_applied = "silent_audio_empty_text"
            flags.append("SECURITY_OVERRIDE_SILENT_EMPTY")
        else:
            final_score = calculated_score

            # ── Evidence-Gated Three-Tier Routing ──
            # FIX: VERIFIED_EMERGENCY requires minimum evidence threshold
            # A text-only solo report can NEVER reach VERIFIED_EMERGENCY regardless of score.
            min_evidence_for_verified = (
                has_audio_evidence or has_visual_evidence or has_swarm or has_grounding
            )

            if final_score >= 80 and min_evidence_for_verified:
                triage_tier = "VERIFIED_EMERGENCY"
                vulnerability_level = "critical"
            elif final_score >= 80 and not min_evidence_for_verified:
                # High score but text-only solo — cap at SUSPECTED_UNCONFIRMED
                triage_tier = "SUSPECTED_UNCONFIRMED"
                vulnerability_level = "critical"
                flags.append("EVIDENCE_GATE_text_only_capped_at_suspected")
            elif final_score >= 35:
                triage_tier = "SUSPECTED_UNCONFIRMED"
                vulnerability_level = "high" if final_score >= 55 else "medium"
            else:
                triage_tier = "FLAGGED_OR_PRANK"
                vulnerability_level = "low"

        breakdown = DeterministicScoreBreakdown(
            f_acoustic=round(f_acoustic, 1),
            f_semantic=round(f_semantic, 1),
            f_cluster=round(f_cluster, 1),
            f_environmental=round(f_environmental, 1),
            f_device=round(f_device, 1),
            bonus_cluster=round(bonus_cluster, 1),
            penalty_tamper=round(penalty_tamper, 1),
            penalty_evidence_gap=round(penalty_evidence_gap, 1),
            cluster_density_factor=round(cluster_density_factor, 3),
            triage_tier=triage_tier,
            has_audio_evidence=has_audio_evidence,
            has_visual_evidence=has_visual_evidence,
            has_swarm_corroboration=has_swarm,
            has_grounding_match=has_grounding,
            evidence_modalities_count=evidence_modalities,
            speaker_distress_pts=speaker_pts,
            specific_details_pts=details_pts,
            acoustic_cues_pts=cues_pts,
            consistency_score=consistency_score,
            grounding_score=grounding_score,
            cluster_score=cluster_score,
            score_before_override=calculated_score,
            final_score=final_score,
            security_override_applied=override_applied,
            flags=flags,
        )

        recommendation = self._generate_recommendation(triage_tier, vulnerability_level, detected_hazards)
        concise_report = self._generate_concise_report(
            score=final_score,
            triage_tier=triage_tier,
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
            triage_tier=triage_tier,
            cluster_density_factor=round(cluster_density_factor, 3),
            bonus_cluster=round(bonus_cluster, 1),
            penalty_tamper=round(penalty_tamper, 1),
            device_integrity_score=int(round(f_device)),
        )

    def _generate_recommendation(
        self,
        triage_tier: str,
        vulnerability: str,
        detected_hazards: List[str]
    ) -> str:
        hazard_str = ", ".join(detected_hazards[:3]) if detected_hazards else "disaster conditions"
        if triage_tier == "VERIFIED_EMERGENCY":
            return f"VERIFIED EMERGENCY (Score 80-100): Immediate dispatch advice. Deploy field rescue team ({hazard_str})."
        elif triage_tier == "SUSPECTED_UNCONFIRMED":
            return f"SUSPECTED UNCONFIRMED (Score 35-79): Routed to Rapid Callback Queue. Trigger automated SMS/IVR verification."
        else:
            return f"FLAGGED OR PRANK (Score 0-34): Quarantined to audit view. Immutable audit log preserved, hidden from dispatch queue."

    def _generate_concise_report(
        self,
        score: int,
        triage_tier: str,
        vulnerability: str,
        location_name: str,
        breakdown: DeterministicScoreBreakdown,
        detected_hazards: List[str],
    ) -> str:
        hazards = ", ".join([h.replace('_', ' ').title() for h in detected_hazards]) if detected_hazards else "General Emergency"
        cluster_desc = (
            f"Corroborated by {breakdown.cluster_score} nearby incident reports (Cd={breakdown.cluster_density_factor:.2f})"
            if breakdown.has_swarm_corroboration
            else "Single unverified distress signal (no independent corroboration)"
        )
        grounding_desc = "Authoritative environmental match" if breakdown.has_grounding_match else "No authoritative grounding match"
        distress_desc = "Audio-Confirmed Distress" if breakdown.has_audio_evidence else "Text-Only Distress Claim"

        evidence_str = []
        if breakdown.has_audio_evidence:
            evidence_str.append("Audio")
        if breakdown.has_visual_evidence:
            evidence_str.append("Visual")
        if breakdown.has_swarm_corroboration:
            evidence_str.append("Swarm")
        if breakdown.has_grounding_match:
            evidence_str.append("Grounded")
        if not evidence_str:
            evidence_str.append("Text-Only")
        evidence_desc = " + ".join(evidence_str)

        lines = [
            f"Emergency Triage Summary [Tier: {triage_tier} | Score: {score}/100 | Level: {vulnerability.upper()}]",
            f"Location: {location_name}",
            f"Primary Hazards: {hazards}",
            f"Distress Status: {distress_desc}",
            f"Evidence Modalities: {evidence_desc} ({breakdown.evidence_modalities_count} sources)",
            f"Corroboration: {cluster_desc}",
            f"Grounding Status: {grounding_desc}",
            f"5-Layer Multi-Factor: Acoustic={breakdown.f_acoustic}, Semantic={breakdown.f_semantic}, Cluster={breakdown.f_cluster}, Env={breakdown.f_environmental}, Device={breakdown.f_device} (Bonus=+{breakdown.bonus_cluster}, Penalty_tamper=-{breakdown.penalty_tamper}, Penalty_evidence=-{breakdown.penalty_evidence_gap})",
        ]
        if breakdown.security_override_applied:
            lines.append(f"Audit Flag: {breakdown.security_override_applied.replace('_', ' ').title()}")
        return "\n".join(lines)


# Singleton
scoring_engine = DeterministicScoringEngine()
