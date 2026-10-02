"""
Emergency Voice, Text, and Location Verification Pipeline.

DESIGN INVARIANTS:
  1. Low-bandwidth, high-reliability architecture: Deprecates visual/video ingestion
     in favor of voice notes (<100KB), text, and GPS coordinates.
  2. Gemini strictly performs structured feature extraction (transcription, acoustic cues,
     semantic distress, cross-modal alignment).
  3. Deterministic scoring is delegated to DeterministicScoringEngine (zero LLM drift).
  4. Pipeline stages run in parallel via asyncio.gather() for speed (<1-2s verification).
  5. Fail-Open Humanitarian Principle: Reports are NEVER auto-rejected on timeout/error.
"""

import math
import json
import asyncio
from typing import Any, Optional, Dict, List, Tuple, Literal
from datetime import datetime, timezone, timedelta

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.config import settings
from app.ai.grounding_engine import grounding_engine, GroundingResult
from app.ai.scoring_engine import scoring_engine, DeterministicScoreResult
from app.db.database import async_session_maker



# ── Strict Pydantic Schema for Gemini Structured Extraction ──────
class VoiceTextVerificationExtraction(BaseModel):
    transcript: str = Field(default="", description="Verbatim transcription of the voice note or cleaned text")
    english_translation: str = Field(default="", description="Fluent, accurate English translation of what the caller is communicating and requesting")
    urdu_translation: str = Field(default="", description="Accurate Urdu script translation of the distress communication")
    situation_summary: str = Field(default="", description="Clear, operational summary of the emergency situation for rescue dispatchers")
    headcount: int = Field(default=1, description="Estimated number of affected individuals")
    vulnerable_groups: List[Any] = Field(default_factory=list, description="Vulnerable individuals detected (infants, elderly, pregnant, injured, trapped)")
    detected_hazards: List[str] = Field(default_factory=list, description="Explicit hazards mentioned (flood, collapse, fire, trapped, injury)")
    acoustic_cues: List[str] = Field(default_factory=list, description="Background sounds detected: sirens, rushing water, alarms, crying, etc.")
    speaker_distress_level: Literal["critical", "elevated", "calm", "inaudible"] = "calm"
    specific_details_provided: bool = Field(default=False, description="True if landmark, street, floor, or victim counts are named")
    text_audio_alignment: bool = Field(default=True, description="True if typed text and spoken audio match in intent and scope")
    inconsistency_notes: str = Field(default="", description="Notes on contradictions between spoken audio and typed text")
    suspected_prank_or_synthetic: bool = Field(default=False, description="True if robotic TTS, parody audio, or non-emergency spam")


def _haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Great-Circle distance between two coordinates in meters."""
    R = 6371000.0  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


class EmergencyVerificationPipeline:
    """
    Asynchronous 5-Layer Emergency Verification Pipeline.

    Layer 1: Hardware & Network Attestation (Play Integrity / DeviceCheck / Non-VPN IP-GPS match)
    Layer 2: Spatiotemporal Multi-Witness Consensus (500m / 15m radius, Cluster Density Cd = ln(1 + N_unique))
    Layer 3: Visual & Media Forensics Engine (pHash archive dedup, EXIF lens noise, diffusion AI detection)
    Layer 4: Multi-Modal Semantic Consistency (Spectrogram energy vs. transcript, DEM topographic elevation sanity)
    Layer 5: Bayesian Risk & Uncertainty Classifier (Three-Tier Routing: VERIFIED_EMERGENCY, SUSPECTED_UNCONFIRMED, FLAGGED_OR_PRANK)
    """

    def __init__(self):
        self.api_key = settings.gemini_api_key.strip() if settings.gemini_api_key else ""
        self.client = (
            genai.Client(api_key=self.api_key)
            if self.api_key and self.api_key != "your_gemini_api_key"
            else None
        )
        self.model = settings.gemini_model or "gemini-2.5-flash"
        self.timeout = settings.verification_timeout_seconds

    async def run_full_pipeline(
        self,
        location_name: str,
        gps_coords: Optional[Tuple[float, float]] = None,
        text_message: Optional[str] = None,
        audio_bytes: Optional[bytes] = None,
        audio_mime_type: str = "audio/webm",
        audio_transcript: Optional[str] = None,
        hazard_tags: Optional[List[str]] = None,
        report_id: Optional[Any] = None,
        device_info: Optional[Dict[str, Any]] = None,
        client_ip: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        video_bytes: Optional[bytes] = None,
        capture_nonce: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute the complete parallel 5-layer verification pipeline with fail-open timeout protection.
        """
        try:
            return await asyncio.wait_for(
                self._run_stages(
                    location_name=location_name,
                    gps_coords=gps_coords,
                    text_message=text_message,
                    audio_bytes=audio_bytes,
                    audio_mime_type=audio_mime_type,
                    audio_transcript=audio_transcript,
                    hazard_tags=hazard_tags,
                    report_id=report_id,
                    device_info=device_info,
                    client_ip=client_ip,
                    image_bytes=image_bytes,
                    video_bytes=video_bytes,
                    capture_nonce=capture_nonce,
                ),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            print(f"[VerificationPipeline] Timeout ({self.timeout}s) exceeded — applying fail-open")
            return self._fail_open_result(location_name, text_message, reason="Pipeline timeout exceeded")
        except Exception as e:
            print(f"[VerificationPipeline] Pipeline error ({e}) — applying fail-open")
            return self._fail_open_result(location_name, text_message, reason=f"Pipeline exception: {str(e)}")

    async def _run_stages(
        self,
        location_name: str,
        gps_coords: Optional[Tuple[float, float]],
        text_message: Optional[str],
        audio_bytes: Optional[bytes],
        audio_mime_type: str,
        audio_transcript: Optional[str],
        hazard_tags: Optional[List[str]],
        report_id: Optional[Any],
        device_info: Optional[Dict[str, Any]] = None,
        client_ip: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        video_bytes: Optional[bytes] = None,
        capture_nonce: Optional[str] = None,
    ) -> Dict[str, Any]:
        hazard_tags = hazard_tags or []
        hazard_context = " ".join(hazard_tags)
        if text_message:
            hazard_context = f"{hazard_context} {text_message}".strip()

        lat = gps_coords[0] if gps_coords else None
        lng = gps_coords[1] if gps_coords else None

        # ── Run all 5 Layers + LLM Extraction concurrently ──
        extraction_task = self._extract_voice_and_text(
            audio_bytes=audio_bytes,
            audio_mime_type=audio_mime_type,
            text_message=text_message,
            audio_transcript=audio_transcript,
            hazard_tags=hazard_tags,
            location_name=location_name,
        )
        from app.services.hardware_attestation_service import hardware_attestation_service
        from app.services.swarm_consensus_service import swarm_consensus_service
        from app.services.media_forensics_service import media_forensics_service
        from app.services.semantic_consistency_service import semantic_consistency_service

        grounding_task = grounding_engine.run_grounding(
            location_name=location_name,
            gps_coords=gps_coords,
            hazard_context=hazard_context,
        )
        clustering_task = swarm_consensus_service.evaluate_spatiotemporal_consensus(
            lat=lat,
            lng=lng,
            radius_meters=500.0,
            time_window_minutes=15,
            exclude_report_id=report_id,
        )
        hardware_task = asyncio.to_thread(
            hardware_attestation_service.evaluate_hardware_and_network,
            device_info=device_info,
            client_ip=client_ip,
            reported_lat=lat,
            reported_lng=lng,
        )
        visual_task = media_forensics_service.run_full_forensics(
            image_bytes=image_bytes,
            video_bytes=video_bytes,
            device_lat=lat,
            device_lng=lng,
            nonce_validated=bool(capture_nonce),
        )
        semantic_task = semantic_consistency_service.evaluate_multimodal_consistency(
            audio_bytes=audio_bytes,
            audio_mime_type=audio_mime_type,
            claimed_transcript=text_message or audio_transcript or "",
            claimed_hazards=hazard_tags,
            gps_coords=gps_coords,
        )

        extraction, grounding_res, cluster_info, hw_info, visual_info, sem_info = await asyncio.gather(
            extraction_task, grounding_task, clustering_task, hardware_task, visual_task, semantic_task, return_exceptions=False
        )

        # ── Phase 3 Asymmetric Grounding Evaluation ──
        is_grounded = grounding_res.grounding_boost > 0 or grounding_res.sources_matched > 0
        grounding_status = "authoritative_match" if is_grounded else "unreported_localized_incident"

        # ── Layer 2 Swarm Consensus Evaluation ──
        is_cluster_corroborated = cluster_info.get("corroborated", False)
        corroborating_count = cluster_info.get("unique_devices_count", 0)
        cluster_id = cluster_info.get("cluster_id")
        cluster_density_factor = cluster_info.get("cluster_density_factor", 0.0)
        cluster_bonus = cluster_info.get("cluster_bonus", 0.0)

        # ── Layer 1 Hardware & Network Attestation ──
        is_emulator = hw_info.get("is_emulator", False)
        is_vpn_or_tor = hw_info.get("is_vpn_or_tor", False)
        device_attestation_passed = hw_info.get("device_attestation_passed", True)
        ip_gps_distance_km = hw_info.get("ip_gps_distance_km")

        # ── Layer 3 Visual & Media Forensics ──
        is_recycled_archive = visual_info.get("is_recycled_archive", False)
        is_diffusion_generated = visual_info.get("is_diffusion_generated", False)

        # ── Layer 4 Semantic & DEM Consistency ──
        elevation_anomaly = sem_info.get("elevation_anomaly", False)

        # Check silent audio / empty input
        has_text = bool((text_message and text_message.strip()) or (extraction.transcript and extraction.transcript.strip()))
        is_silent = bool(audio_bytes and len(audio_bytes) < 100) or (extraction.speaker_distress_level == "inaudible" and not extraction.transcript)

        # ── Determine evidence modalities ──
        has_real_audio = bool(audio_bytes and len(audio_bytes) >= 100)
        has_real_visual = bool(image_bytes or video_bytes)
        is_text_only_report = not has_real_audio and not has_real_visual

        # FIX: When no audio is present, cross-modal alignment is unverified (not assumed True)
        effective_text_audio_alignment = extraction.text_audio_alignment if has_real_audio else False

        # ── Layer 5: Deterministic Scoring Engine with 5-Layer Multi-Factor Formulation ──
        score_res: DeterministicScoreResult = scoring_engine.compute_score(
            speaker_distress_level=extraction.speaker_distress_level,
            specific_details_provided=extraction.specific_details_provided,
            acoustic_cues=extraction.acoustic_cues,
            text_audio_alignment=effective_text_audio_alignment,
            has_contradiction=bool(extraction.inconsistency_notes),
            is_authoritative_grounded=is_grounded,
            grounding_status=grounding_status,
            is_cluster_corroborated=is_cluster_corroborated,
            corroborating_reports_count=corroborating_count,
            suspected_prank_or_synthetic=extraction.suspected_prank_or_synthetic,
            is_audio_silent_or_corrupted=is_silent,
            has_text_content=has_text,
            location_name=location_name,
            detected_hazards=extraction.detected_hazards or hazard_tags,
            # 5-Layer Multi-Factor & Forensic inputs
            cluster_density_factor=cluster_density_factor,
            bonus_cluster_override=cluster_bonus if cluster_bonus > 0 else None,
            is_recycled_archive=is_recycled_archive,
            is_diffusion_generated=is_diffusion_generated,
            is_vpn_or_tor=is_vpn_or_tor,
            is_emulator=is_emulator,
            elevation_anomaly=elevation_anomaly,
            device_attestation_passed=device_attestation_passed,
            ip_gps_distance_km=ip_gps_distance_km,
            headcount=extraction.headcount,
            vulnerable_groups_count=len(extraction.vulnerable_groups),
            # NEW v5.0: Evidence modality flags
            has_audio_evidence=has_real_audio,
            has_visual_evidence=has_real_visual,
            is_text_only=is_text_only_report,
        )

        parsed_transcript = extraction.transcript or text_message or ""

        # Comprehensive 5-Layer Breakdown Dictionary
        breakdown_5layer = {
            "layer_1_hardware_attestation": hw_info,
            "layer_2_swarm_consensus": cluster_info,
            "layer_3_visual_forensics": visual_info,
            "layer_4_semantic_consistency": sem_info,
            "layer_5_bayesian_classifier": {
                "triage_tier": score_res.triage_tier,
                "verification_score": score_res.verification_score,
                "cluster_density_factor": score_res.cluster_density_factor,
                "bonus_cluster": score_res.bonus_cluster,
                "penalty_tamper": score_res.penalty_tamper,
                "breakdown": score_res.breakdown,
            },
        }

        return {
            "is_verified": score_res.verification_score >= 80 or (score_res.triage_tier == "VERIFIED_EMERGENCY"),
            "verification_score": score_res.verification_score,
            "vulnerability_level": score_res.vulnerability_level,
            "triage_tier": score_res.triage_tier,
            "cluster_density_factor": score_res.cluster_density_factor,
            "bonus_cluster": score_res.bonus_cluster,
            "penalty_tamper": score_res.penalty_tamper,
            "device_integrity_score": score_res.device_integrity_score,
            "semantic_score": score_res.semantic_score,
            "consistency_score": score_res.consistency_score,
            "grounding_score": score_res.grounding_score,
            "cluster_score": score_res.cluster_score,
            "grounding_status": grounding_status,
            "grounding_label": grounding_status,
            "cluster_id": cluster_id,
            "voice_transcript": parsed_transcript,
            "parsed_text": parsed_transcript,
            "english_translation": extraction.english_translation or parsed_transcript,
            "urdu_translation": extraction.urdu_translation or parsed_transcript,
            "situation_summary": extraction.situation_summary,
            "headcount": extraction.headcount,
            "vulnerable_groups": extraction.vulnerable_groups,
            "acoustic_distress_level": extraction.speaker_distress_level,
            "detected_hazards": extraction.detected_hazards,
            "acoustic_cues": extraction.acoustic_cues,
            "rubric_breakdown": score_res.breakdown,
            "recommendation": score_res.recommendation,
            "concise_report": score_res.concise_report,
            "grounding_summary": grounding_res.combined_summary,
            "verification_breakdown_5layer": breakdown_5layer,
            "ai_verification_report": {
                "verification_score": score_res.verification_score,
                "vulnerability_level": score_res.vulnerability_level,
                "triage_tier": score_res.triage_tier,
                "cluster_density_factor": score_res.cluster_density_factor,
                "extraction": extraction.model_dump(),
                "grounding": {
                    "status": grounding_status,
                    "summary": grounding_res.combined_summary,
                    "score": score_res.grounding_score,
                },
                "clustering": {
                    "cluster_id": cluster_id,
                    "corroborated": is_cluster_corroborated,
                    "nearby_reports_count": corroborating_count,
                    "cluster_density_factor": cluster_density_factor,
                    "cluster_bonus": cluster_bonus,
                    "score": score_res.cluster_score,
                },
                "hardware_attestation": hw_info,
                "visual_forensics": visual_info,
                "semantic_consistency": sem_info,
                "breakdown": score_res.breakdown,
                "breakdown_5layer": breakdown_5layer,
            },
        }

    async def _extract_voice_and_text(
        self,
        audio_bytes: Optional[bytes],
        audio_mime_type: str,
        text_message: Optional[str],
        audio_transcript: Optional[str],
        hazard_tags: List[str],
        location_name: Optional[str] = None,
    ) -> VoiceTextVerificationExtraction:
        # Multi-Dialect Rescue Triage & Forensic Verification Engine (v4.2-Production)
        from app.ai.triage_engine import process_emergency_broadcast

        # Silent or empty audio check
        if audio_bytes and len(audio_bytes) < 100 and not text_message:
            return VoiceTextVerificationExtraction(
                transcript="",
                english_translation="No intelligible distress audio recorded.",
                urdu_translation="صوتی پیغام موصول نہیں ہوا۔",
                situation_summary=f"Empty audio distress note received from {location_name or 'incident site'}.",
                headcount=1,
                vulnerable_groups=[],
                detected_hazards=[],
                acoustic_cues=[],
                speaker_distress_level="inaudible",
                specific_details_provided=False,
                text_audio_alignment=True,
                suspected_prank_or_synthetic=False,
            )

        master_payload = await process_emergency_broadcast(
            distress_content=text_message or audio_transcript or "",
            audio_bytes=audio_bytes,
            audio_mime_type=audio_mime_type,
            location_hint=location_name,
            hazard_tags=hazard_tags,
        )

        demo = master_payload.headcount_matrix.demographic_breakdown
        vuln = []
        if demo.infants_and_children > 0:
            vuln.append({"type": "infants_and_children", "count": demo.infants_and_children})
        if demo.elderly_individuals > 0:
            vuln.append({"type": "elderly", "count": demo.elderly_individuals})
        if demo.pregnant_women > 0:
            vuln.append({"type": "pregnant", "count": demo.pregnant_women})
        if demo.critically_injured_or_sick > 0:
            vuln.append({"type": "injured_or_sick", "count": demo.critically_injured_or_sick})

        # FIX v5.0: Map distress level with nuance instead of always returning critical/elevated.
        # Allow 'calm' for reports without strong distress indicators.
        urgency = master_payload.triage_scoring.urgency_level
        if urgency == "CRITICAL":
            mapped_distress = "critical"
        elif urgency in ("HIGH", "ELEVATED"):
            mapped_distress = "elevated"
        elif urgency in ("MEDIUM", "STANDARD"):
            mapped_distress = "calm"  # FIX: Allow calm for medium urgency
        else:
            mapped_distress = "calm"

        # FIX: specific_details_provided should require real granularity
        # Generic locations like 'Lahore' don't count — need streets, blocks, floor numbers
        landmarks = master_payload.spatial_and_tactical_intelligence.reported_landmarks
        has_real_details = len(landmarks) >= 2 or any(
            kw in str(landmarks).lower() for kw in [
                "street", "block", "sector", "gali", "road", "floor", "house",
                "chhat", "roof", "hospital", "school", "mohalla", "colony",
                "apartment", "flat", "building", "bazaar", "chowk",
            ]
        )

        return VoiceTextVerificationExtraction(
            transcript=master_payload.standardized_english_intelligence.verbatim_clean_translation,
            english_translation=master_payload.standardized_english_intelligence.verbatim_clean_translation,
            urdu_translation=master_payload.standardized_english_intelligence.verbatim_clean_translation,
            situation_summary=master_payload.standardized_english_intelligence.short_incident_summary,
            headcount=master_payload.headcount_matrix.total_estimated_victims,
            vulnerable_groups=vuln,
            detected_hazards=[master_payload.triage_scoring.primary_hazard_classification] + master_payload.triage_scoring.secondary_hazards,
            acoustic_cues=master_payload.forensic_verification.forensic_flags,
            speaker_distress_level=mapped_distress,
            specific_details_provided=has_real_details,
            text_audio_alignment=bool(audio_bytes and len(audio_bytes) >= 100),  # FIX: Only true when audio exists
            inconsistency_notes="",
            suspected_prank_or_synthetic=master_payload.forensic_verification.adversarial_prank_detected,
        )

    def _extract_from_text_heuristic(self, text: str, hazard_tags: List[str], location_name: Optional[str] = None) -> VoiceTextVerificationExtraction:
        """Heuristic extractor for testing and offline scenarios."""
        from app.ai.gemini_client import GeminiClient
        synth = GeminiClient._heuristic_fallback_extraction(text, location_context=location_name)

        t_lower = text.lower()

        # Check prank indicators
        is_prank = any(term in t_lower for term in ["prank", "joke", "rickroll", "comedy", "fake sos", "testing 123"])

        # Detect acoustic cues from text mentions
        cues = []
        if any(w in t_lower for w in ["siren", "ambulance", "police", "alarm", "horn"]):
            cues.append("sirens")
        if any(w in t_lower for w in ["water", "flood", "rushing", "gushing", "waves", "paani"]):
            cues.append("rushing_water")
        if any(w in t_lower for w in ["crying", "screaming", "cheekh", "rona", "shouting", "screams"]):
            cues.append("crying_or_screaming")
        if any(w in t_lower for w in ["explosion", "blast", "collapse", "dhamaka", "gir gaya"]):
            cues.append("collapse_impact")

        # Detect hazards
        hazards = list(hazard_tags)
        for h in ["flood", "collapse", "fire", "trapped", "injury", "medical", "earthquake", "water"]:
            if h in t_lower and h not in hazards:
                hazards.append(h)
        synth_hz = synth.get("hazard_type")
        if synth_hz and synth_hz != "unclear" and synth_hz not in hazards:
            hazards.append(synth_hz)

        # Distress level
        if any(w in t_lower for w in ["help", "madad", "bachao", "dying", "urgent", "critical", "drowning", "mar rahe"]):
            distress = "critical"
        elif any(w in t_lower for w in ["stuck", "phanse", "rising", "damage", "danger", "khatra"]):
            distress = "elevated"
        elif not text:
            distress = "inaudible"
        else:
            distress = "calm"

        # Specific details provided
        has_details = any(char.isdigit() for char in text) or any(w in t_lower for w in ["street", "block", "sector", "gali", "road", "floor", "house", "chhat", "roof", "hospital", "school"])

        return VoiceTextVerificationExtraction(
            transcript=synth.get("parsed_text") or text,
            english_translation=synth.get("english_translation") or text,
            urdu_translation=synth.get("urdu_translation") or text,
            situation_summary=synth.get("situation_summary") or f"Emergency distress reported: {text}",
            headcount=synth.get("headcount") or 1,
            vulnerable_groups=synth.get("vulnerable_groups") or [],
            detected_hazards=hazards,
            acoustic_cues=cues,
            speaker_distress_level=distress,
            specific_details_provided=has_details,
            text_audio_alignment=True,
            suspected_prank_or_synthetic=is_prank,
        )

    async def _check_spatiotemporal_cluster(
        self,
        gps_coords: Optional[Tuple[float, float]],
        hazard_tags: List[str],
        report_id: Optional[Any],
    ) -> Dict[str, Any]:
        """
        Phase 4: Spatiotemporal Incident Clustering.
        Query reports within 500m radius over the last 45 minutes.
        If >= 2 independent reports share matching hazard keywords, escalate cluster score to 100%.
        """
        if not gps_coords:
            return {"corroborated": False, "count": 0, "cluster_id": None}

        lat, lon = gps_coords
        time_window = datetime.now(timezone.utc) - timedelta(minutes=45)

        corroborating_count = 0
        matching_cluster_id = None

        try:
            from app.models.report import Report
            async with async_session_maker() as session:
                # Select recent reports within the 45 minute window
                stmt = select(Report).where(
                    Report.created_at >= time_window
                )
                if report_id:
                    stmt = stmt.where(Report.id != report_id)

                res = await session.execute(stmt)
                recent_reports = res.scalars().all()

                hazard_keywords = {h.lower().strip() for h in hazard_tags}
                # Also include broad disaster terms
                for kw in ["flood", "fire", "collapse", "water", "medical"]:
                    if any(kw in h for h in hazard_keywords):
                        hazard_keywords.add(kw)

                for r in recent_reports:
                    r_lat, r_lon = None, None
                    # Try reading gps_location geometry or extraction
                    if r.gps_location:
                        try:
                            from geoalchemy2.shape import to_shape
                            pt = to_shape(r.gps_location)
                            r_lat, r_lon = pt.y, pt.x
                        except Exception:
                            pass

                    if r_lat is not None and r_lon is not None:
                        dist = _haversine_distance_meters(lat, lon, r_lat, r_lon)
                        if dist <= 500.0:
                            # Check hazard keyword match
                            r_hazards = ""
                            if r.ai_extraction and isinstance(r.ai_extraction, dict):
                                r_hazards = str(r.ai_extraction.get("detected_hazards", "")) + " " + str(r.ai_extraction.get("hazard_type", ""))
                            if r.raw_input:
                                r_hazards += " " + r.raw_input
                            if r.parsed_text:
                                r_hazards += " " + r.parsed_text

                            r_hazards_lower = r_hazards.lower()
                            has_match = any(hk in r_hazards_lower for hk in hazard_keywords) if hazard_keywords else True
                            if has_match:
                                corroborating_count += 1
                                if getattr(r, "cluster_id", None):
                                    matching_cluster_id = r.cluster_id

            is_corroborated = corroborating_count >= 2
            final_cluster_id = matching_cluster_id or (f"cluster_{report_id.hex[:8]}" if is_corroborated and report_id else None)

            return {
                "corroborated": is_corroborated,
                "count": corroborating_count,
                "cluster_id": final_cluster_id,
            }

        except Exception as e:
            print(f"[VerificationPipeline] Cluster query warning ({e}); continuing with baseline.")
            return {"corroborated": False, "count": 0, "cluster_id": None}

    def _fail_open_result(self, location_name: str, text_message: Optional[str] = None, reason: Optional[str] = None) -> Dict[str, Any]:
        """Fail-open fallback ensures humanitarian reports are never auto-rejected."""
        if reason is None and text_message and ("timeout" in text_message.lower() or "exception" in text_message.lower() or "fail" in text_message.lower() or "pipeline" in text_message.lower()):
            reason = text_message
            text_message = ""
        reason = reason or "Fail-open safety protocol activated"

        score_res = scoring_engine.compute_score(
            speaker_distress_level="elevated",
            specific_details_provided=bool(text_message),
            is_authoritative_grounded=False,
            grounding_status="unreported_localized_incident",
            is_cluster_corroborated=False,
            has_text_content=bool(text_message),
            location_name=location_name,
        )

        return {
            "is_verified": False,
            "verification_score": 40,
            "vulnerability_level": "requires_human_triage",
            "triage_tier": "SUSPECTED_UNCONFIRMED",
            "cluster_density_factor": 0.0,
            "bonus_cluster": 0.0,
            "penalty_tamper": 0.0,
            "device_integrity_score": 100,
            "semantic_score": score_res.semantic_score,
            "consistency_score": score_res.consistency_score,
            "grounding_score": 10,
            "cluster_score": 5,
            "grounding_status": "unreported_localized_incident",
            "grounding_label": "unreported_localized_incident",
            "cluster_id": None,
            "voice_transcript": text_message or "",
            "parsed_text": text_message or "",
            "english_translation": text_message or "Emergency relief assistance requested.",
            "urdu_translation": f"{location_name} میں ایمرجنسی، فوری مدد درکار ہے۔",
            "situation_summary": f"Emergency distress alert at {location_name}. {reason}",
            "headcount": 1,
            "vulnerable_groups": [],
            "acoustic_distress_level": "elevated",
            "detected_hazards": ["general_emergency"],
            "acoustic_cues": [],
            "rubric_breakdown": score_res.breakdown,
            "recommendation": f"FAIL-OPEN TRIAGE: {reason}. Escalated to Rapid Callback Queue for manual dispatch.",
            "concise_report": f"ReliefPulse Fail-Open Triage [Score: 40/100 | SUSPECTED_UNCONFIRMED]\nReason: {reason}. This emergency report has NOT been rejected.",
            "stage_1_location": {"status": "unreported_localized_incident", "score": 10},
            "stage_2_visual": {"status": "no_visual_required", "score": 10},
            "stage_3_intent": {"status": "fail_open_baseline", "score": 10},
            "stage_4_provenance": {"status": "verified_channel", "score": 10},
            "verification_breakdown_5layer": {
                "layer_1_hardware_attestation": {"device_integrity_score": 100, "status": "fail_open"},
                "layer_2_swarm_consensus": {"cluster_density_factor": 0.0, "status": "fail_open"},
                "layer_3_visual_forensics": {"visual_score": 100, "status": "fail_open"},
                "layer_4_semantic_consistency": {"consistency_score": 100, "status": "fail_open"},
                "layer_5_bayesian_classifier": {"triage_tier": "SUSPECTED_UNCONFIRMED", "score": 40},
            },
            "ai_verification_report": {
                "fail_open": True,
                "reason": reason,
                "triage_tier": "SUSPECTED_UNCONFIRMED",
                "breakdown": score_res.breakdown,
            },
        }


# Singleton instance
verification_pipeline = EmergencyVerificationPipeline()
