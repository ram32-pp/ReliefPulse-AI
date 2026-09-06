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
    Asynchronous 4-Phase Voice + Text + Location Verification Pipeline.
    
    Phase 1 & 2: Audio Ingestion, Acoustic Distress Analysis & Cross-Modal Consistency
    Phase 3: Asymmetric Location & Environmental Grounding (USGS + Weather + Google Search)
    Phase 4: Spatiotemporal Cluster Corroboration (500m / 45min radius)
    Scoring: Pure Deterministic Rubric Scoring Engine (0-100)
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
    ) -> Dict[str, Any]:
        """
        Execute the complete parallel verification pipeline with fail-open timeout protection.
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
    ) -> Dict[str, Any]:
        hazard_tags = hazard_tags or []
        hazard_context = " ".join(hazard_tags)
        if text_message:
            hazard_context = f"{hazard_context} {text_message}".strip()

        # Run Phase 1&2 (Voice/Text Extraction), Phase 3 (Grounding), and Phase 4 (Clustering) in parallel
        extraction_task = self._extract_voice_and_text(
            audio_bytes=audio_bytes,
            audio_mime_type=audio_mime_type,
            text_message=text_message,
            audio_transcript=audio_transcript,
            hazard_tags=hazard_tags,
            location_name=location_name,
        )
        grounding_task = grounding_engine.run_grounding(
            location_name=location_name,
            gps_coords=gps_coords,
            hazard_context=hazard_context,
        )
        clustering_task = self._check_spatiotemporal_cluster(
            gps_coords=gps_coords,
            hazard_tags=hazard_tags,
            report_id=report_id,
        )

        extraction, grounding_res, cluster_info = await asyncio.gather(
            extraction_task, grounding_task, clustering_task, return_exceptions=False
        )

        # ── Phase 3 Asymmetric Grounding Evaluation ──
        is_grounded = grounding_res.grounding_boost > 0 or grounding_res.sources_matched > 0
        grounding_status = "authoritative_match" if is_grounded else "unreported_localized_incident"

        # ── Phase 4 Spatiotemporal Clustering Evaluation ──
        is_cluster_corroborated = cluster_info.get("corroborated", False)
        corroborating_count = cluster_info.get("count", 0)
        cluster_id = cluster_info.get("cluster_id")

        # Check silent audio / empty input
        has_text = bool((text_message and text_message.strip()) or (extraction.transcript and extraction.transcript.strip()))
        is_silent = bool(audio_bytes and len(audio_bytes) < 100) or (extraction.speaker_distress_level == "inaudible" and not extraction.transcript)

        # ── Deterministic Scoring Engine ──
        score_res: DeterministicScoreResult = scoring_engine.compute_score(
            speaker_distress_level=extraction.speaker_distress_level,
            specific_details_provided=extraction.specific_details_provided,
            acoustic_cues=extraction.acoustic_cues,
            text_audio_alignment=extraction.text_audio_alignment,
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
        )

        parsed_transcript = extraction.transcript or text_message or ""

        return {
            "is_verified": score_res.verification_score >= 55,
            "verification_score": score_res.verification_score,
            "vulnerability_level": score_res.vulnerability_level,
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
            "ai_verification_report": {
                "verification_score": score_res.verification_score,
                "vulnerability_level": score_res.vulnerability_level,
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
                    "score": score_res.cluster_score,
                },
                "breakdown": score_res.breakdown,
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
        """
        Phases 1 & 2: Gemini Audio Processing + Cross-Modal Consistency Check.
        """
        # If pre-extracted transcript provided and no audio
        if not audio_bytes and (audio_transcript or text_message):
            return self._extract_from_text_heuristic(text_message or audio_transcript or "", hazard_tags, location_name=location_name)

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

        # Call Gemini if client is configured
        if self.client and audio_bytes:
            try:
                system_instruction = (
                    "You are the Voice & Text Emergency Verification Engine for ReliefPulse-AI. "
                    "Analyze the emergency distress audio recording and cross-reference with any user typed text and hazard badges. "
                    "1. Transcribe the audio note verbatim in 'transcript'.\n"
                    "2. Provide a fluent, accurate English translation in 'english_translation' (e.g. translating Roman Urdu/Urdu speech into clear English distress statements).\n"
                    "3. Provide an accurate Urdu script translation in 'urdu_translation'.\n"
                    "4. Write an operational, concise situation summary in 'situation_summary' stating what happened, location, victims, and urgent assistance needed.\n"
                    "5. Estimate headcount (integer) and extract any vulnerable groups (infants, elderly, pregnant, injured, trapped).\n"
                    "6. Detect background acoustic distress cues (sirens, rushing water, alarms, crying, screaming, building creaking).\n"
                    "7. Assess speaker distress level ('critical', 'elevated', 'calm', or 'inaudible').\n"
                    "8. Check if spoken audio aligns with typed text.\n"
                    "9. Detect if audio is synthetic TTS, comedy/music prank, or spam.\n"
                    "Output STRICTLY according to the VoiceTextVerificationExtraction JSON schema."
                )

                contents: List[Any] = [
                    types.Part.from_bytes(data=audio_bytes, mime_type=audio_mime_type),
                ]
                prompt_text = f"User typed text: {text_message or 'None'}\nReported location: {location_name or 'Unknown'}\nSelected hazard badges: {', '.join(hazard_tags) if hazard_tags else 'None'}"
                contents.append(prompt_text)

                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=VoiceTextVerificationExtraction,
                        temperature=0.1,
                    ),
                )

                if response and response.text:
                    data = json.loads(response.text)
                    return VoiceTextVerificationExtraction(**data)

            except Exception as e:
                print(f"[VerificationPipeline] Gemini Voice Extraction call failed: {e}. Falling back to heuristic extraction.")

        # Offline / Test / Heuristic Fallback
        return self._extract_from_text_heuristic(text_message or audio_transcript or "", hazard_tags, location_name=location_name)

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
            "recommendation": f"FAIL-OPEN TRIAGE: {reason}. Escalated to coordinator for manual dispatch.",
            "concise_report": f"ReliefPulse Fail-Open Triage [Score: 40/100 | REQUIRES_HUMAN_TRIAGE]\nReason: {reason}. This emergency report has NOT been rejected.",
            "stage_1_location": {"status": "unreported_localized_incident", "score": 10},
            "stage_2_visual": {"status": "no_visual_required", "score": 10},
            "stage_3_intent": {"status": "fail_open_baseline", "score": 10},
            "stage_4_provenance": {"status": "verified_channel", "score": 10},
            "ai_verification_report": {
                "fail_open": True,
                "reason": reason,
                "breakdown": score_res.breakdown,
            },
        }


# Singleton instance
verification_pipeline = EmergencyVerificationPipeline()
