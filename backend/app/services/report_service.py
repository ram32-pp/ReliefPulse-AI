import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.report import Report
from app.api.schemas import ReportCreate
from app.ai.verification_pipeline import verification_pipeline
from app.db.database import async_session_maker


async def _run_verification_background(
    report_id: uuid.UUID,
    location_name: str,
    gps_tuple: Optional[Tuple[float, float]],
    text_input: Optional[str],
    audio_bytes: Optional[bytes],
    audio_mime_type: str,
    quick_hazard_tags: Optional[List[str]],
    device_info: Optional[Dict[str, Any]] = None,
    client_ip: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
    video_bytes: Optional[bytes] = None,
    capture_nonce: Optional[str] = None,
):
    """
    Background Task: Asynchronous 5-Layer Emergency Verification Pipeline.
    Runs in background so citizen receives a fast-path (<300ms) response.
    Never auto-rejects; on error/timeout applies fail-open.
    """
    try:
        # Run parallel multi-stage 5-layer verification pipeline
        verification_result = await verification_pipeline.run_full_pipeline(
            location_name=location_name,
            gps_coords=gps_tuple,
            text_message=text_input,
            audio_bytes=audio_bytes,
            audio_mime_type=audio_mime_type,
            hazard_tags=quick_hazard_tags,
            report_id=report_id,
            device_info=device_info,
            client_ip=client_ip,
            image_bytes=image_bytes,
            video_bytes=video_bytes,
            capture_nonce=capture_nonce,
        )

        v_score = verification_result.get("verification_score", 40)
        v_level = verification_result.get("vulnerability_level", "requires_human_triage")
        triage_tier = (verification_result.get("triage_tier") or "SUSPECTED_UNCONFIRMED").upper()
        is_verified = verification_result.get("is_verified", False)

        final_status = "pending_audit"

        # Update report record in DB
        async with async_session_maker() as session:
            stmt = select(Report).where(Report.id == report_id)
            res = await session.execute(stmt)
            rep = res.scalars().first()
            if rep:
                rep.verification_score = v_score
                rep.vulnerability_level = v_level
                rep.confidence_score = v_score / 100.0
                rep.triage_tier = triage_tier.lower()
                rep.cluster_density_factor = verification_result.get("cluster_density_factor", 0.0)
                rep.device_integrity_score = verification_result.get("device_integrity_score", 100)
                rep.media_forensics_score = verification_result.get("visual_score", 100)
                rep.semantic_consistency_score = verification_result.get("consistency_score", 100)
                rep.tamper_penalty = int(verification_result.get("penalty_tamper", 0))
                rep.verification_breakdown_5layer = verification_result.get("verification_breakdown_5layer")

                rep.semantic_score = verification_result.get("semantic_score", 0)
                rep.consistency_score = verification_result.get("consistency_score", 0)
                rep.grounding_score = verification_result.get("grounding_score", 10)
                rep.cluster_score = verification_result.get("cluster_score", 5)
                rep.grounding_status = verification_result.get("grounding_status", "unreported_localized_incident")
                rep.grounding_label = verification_result.get("grounding_status", "unreported_localized_incident")
                rep.cluster_id = verification_result.get("cluster_id")
                rep.voice_transcript = verification_result.get("voice_transcript")
                rep.acoustic_distress_level = verification_result.get("acoustic_distress_level")
                rep.ai_verification_report = verification_result
                rep.rubric_breakdown = verification_result.get("rubric_breakdown")
                rep.anomaly_flags = (verification_result.get("rubric_breakdown") or {}).get("flags", [])

                if not rep.parsed_text and verification_result.get("parsed_text"):
                    rep.parsed_text = verification_result["parsed_text"]

                # Extract hazards and headcount
                detected_hazards = verification_result.get("detected_hazards", []) or (quick_hazard_tags or ["general_emergency"])
                primary_hazard = detected_hazards[0] if detected_hazards else "general_emergency"

                existing_ext = rep.ai_extraction or {}
                eng_trans = verification_result.get("english_translation") or existing_ext.get("english_translation")
                urdu_trans = verification_result.get("urdu_translation") or existing_ext.get("urdu_translation")
                sit_summary = verification_result.get("situation_summary") or existing_ext.get("situation_summary")
                h_count = verification_result.get("headcount") or existing_ext.get("headcount") or 1
                vuln_groups = verification_result.get("vulnerable_groups") or existing_ext.get("vulnerable_groups") or []

                verif_ext = {
                    "hazard_type": primary_hazard,
                    "detected_hazards": detected_hazards,
                    "parsed_text": rep.parsed_text or rep.voice_transcript,
                    "situation_summary": (
                        sit_summary
                        or f"{primary_hazard.replace('_', ' ').title()} emergency reported at {rep.extracted_location_name or 'the scene'}."
                    ),
                    "english_translation": eng_trans,
                    "urdu_translation": urdu_trans,
                    "caller_statement": rep.parsed_text or rep.voice_transcript or rep.raw_input,
                    "headcount": h_count,
                    "vulnerable_groups": vuln_groups,
                    "acoustic_cues": verification_result.get("acoustic_cues", []),
                    "speaker_distress_level": rep.acoustic_distress_level,
                    "verification_score": v_score,
                    "vulnerability_level": v_level,
                    "triage_tier": triage_tier,
                    "cluster_density_factor": rep.cluster_density_factor,
                }
                rep.ai_extraction = {**existing_ext, **verif_ext}

                # ── Three-Tier Routing Decision ──
                # 80 – 100: VERIFIED_EMERGENCY -> Direct route to active coordinator queue with immediate dispatch advice
                # 35 – 79:  SUSPECTED_UNCONFIRMED -> Routed to Rapid Callback Queue (Automated SMS/IVR verification)
                # 0  – 34:  FLAGGED_OR_PRANK -> Quarantined to coordinator audit view (completely hidden from critical dispatch queue)
                if triage_tier == "VERIFIED_EMERGENCY" or v_score >= 80:
                    rep.status = "verified"
                    rep.relief_status = "verified"
                    rep.relief_eta_minutes = 20
                    rep.relief_team_name = "Rescue 1122 Rapid Unit"
                    rep.urgency_level = "critical"
                elif triage_tier == "FLAGGED_OR_PRANK" or v_score < 35 or v_level == "false_or_prank":
                    rep.status = "rejected"
                    rep.urgency_level = "low"
                else:  # SUSPECTED_UNCONFIRMED
                    rep.status = "pending_audit"
                    rep.relief_status = "pending"
                    rep.urgency_level = ReportService._map_vulnerability_to_urgency_static(v_level)
                    rep.callback_status = "pending"

                final_status = rep.status
                await session.commit()
                print(f"[ReportService] Report {report_id} 5-layer verified: score={v_score}, tier={triage_tier}, status={final_status}")

        # Broadcast update to connected clients via WebSocket
        try:
            from app.api.routes.websocket import broadcast_report_update
            await broadcast_report_update(
                report_id=str(report_id),
                event_type="report_verification_complete",
                data={
                    "report_id": str(report_id),
                    "status": final_status,
                    "parsed_text": verification_result.get("parsed_text"),
                    "voice_transcript": verification_result.get("voice_transcript"),
                    "acoustic_distress_level": verification_result.get("acoustic_distress_level"),
                    "verification_score": v_score,
                    "vulnerability_level": v_level,
                    "semantic_score": verification_result.get("semantic_score"),
                    "consistency_score": verification_result.get("consistency_score"),
                    "grounding_score": verification_result.get("grounding_score"),
                    "cluster_score": verification_result.get("cluster_score"),
                    "grounding_status": verification_result.get("grounding_status"),
                    "cluster_id": verification_result.get("cluster_id"),
                    "concise_report": verification_result.get("concise_report"),
                    "rubric_breakdown": verification_result.get("rubric_breakdown"),
                },
            )
        except Exception as ws_err:
            print(f"[ReportService] WebSocket broadcast warning: {ws_err}")

    except Exception as exc:
        print(f"[ReportService] Background verification exception ({exc}) — applying fail-open")
        try:
            async with async_session_maker() as session:
                res = await session.execute(select(Report).where(Report.id == report_id))
                rep = res.scalars().first()
                if rep:
                    rep.status = "pending_audit"
                    rep.vulnerability_level = "requires_human_triage"
                    rep.verification_score = 40
                    rep.urgency_level = "high"
                    await session.commit()
        except Exception as db_err:
            print(f"[ReportService] Fail-open DB commit error: {db_err}")


class ReportService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _map_vulnerability_to_urgency_static(v_level: str) -> str:
        if v_level in ["critical", "high", "medium", "low"]:
            return v_level
        return "high"

    def _map_vulnerability_to_urgency(self, v_level: str) -> str:
        return ReportService._map_vulnerability_to_urgency_static(v_level)

    async def create_report(
        self,
        report_data: ReportCreate,
        user_id: Optional[uuid.UUID] = None,
        audio_bytes: Optional[bytes] = None,
        audio_mime_type: str = "audio/webm",
        image_bytes: Optional[bytes] = None,
        video_bytes: Optional[bytes] = None,
        client_ip: Optional[str] = None,
    ) -> Report:
        """
        Fast-Path Dispatch (<300ms):
          1. Aggregates text notes and hazard tags.
          2. Resolves coordinates & location name.
          3. Persists report immediately with status='pending_audit'.
          4. Alerts coordinators via WebSocket.
          5. Launches background 5-layer verification task asynchronously and returns report immediately.
        """
        # 1. Text & hazard aggregation
        text_input = (report_data.text_note or report_data.text_input or "").strip()
        hazards = list(report_data.hazards or report_data.hazard_types or [])

        # If user did not provide text description, synthesize a clean sentence from selected hazards or location
        if not text_input:
            items_to_describe = []
            if hazards:
                items_to_describe.extend([h.replace('_', ' ').title() for h in hazards])
            if report_data.quick_buttons:
                items_to_describe.extend([b.replace('_', ' ').title() for b in report_data.quick_buttons])
            if items_to_describe:
                text_input = f"Reported emergency: {', '.join(items_to_describe)}"
            elif report_data.address_text:
                text_input = f"Emergency SOS signal broadcast from {report_data.address_text}"
            else:
                text_input = "Emergency SOS distress signal received."

        # 2. Location determination
        gps_tuple: Optional[Tuple[float, float]] = None
        if report_data.latitude is not None and report_data.longitude is not None:
            gps_tuple = (report_data.latitude, report_data.longitude)
        elif report_data.gps_location:
            gps_tuple = (report_data.gps_location.latitude, report_data.gps_location.longitude)

        loc_name = report_data.address_text
        if not loc_name and gps_tuple:
            loc_name = f"{gps_tuple[0]:.4f}° N, {gps_tuple[1]:.4f}° E"
        elif not loc_name:
            loc_name = "Reported Location"

        gps_wkt = None
        if gps_tuple:
            gps_wkt = f"SRID=4326;POINT({gps_tuple[1]} {gps_tuple[0]})"

        # 3. Fast-path initial emergency synthesis (<10ms)
        from app.ai.gemini_client import GeminiClient
        initial_synth = GeminiClient._heuristic_fallback_extraction(text_input, location_context=loc_name)
        primary_hazard = hazards[0] if hazards else (initial_synth.get("hazard_type") if initial_synth.get("hazard_type") != "unclear" else "general_emergency")
        initial_ext = {
            "hazard_type": primary_hazard,
            "detected_hazards": hazards or [primary_hazard],
            "parsed_text": initial_synth.get("parsed_text") or text_input or "Emergency distress signal received.",
            "situation_summary": initial_synth.get("situation_summary") or f"{primary_hazard.replace('_', ' ').title()} emergency at {loc_name}.",
            "english_translation": initial_synth.get("english_translation") or text_input or "Emergency relief assistance requested.",
            "urdu_translation": initial_synth.get("urdu_translation") or f"{loc_name} میں ایمرجنسی، فوری مدد درکار ہے۔",
            "caller_statement": initial_synth.get("parsed_text") or text_input or "Emergency distress signal received.",
            "headcount": initial_synth.get("headcount") or 1,
            "vulnerable_groups": initial_synth.get("vulnerable_groups") or [],
            "medical_risks": initial_synth.get("medical_risks") or [],
        }

        # 4. Fast-path DB persistence (<300ms)
        report = Report(
            user_id=user_id,
            raw_input=text_input,
            parsed_text=initial_ext["parsed_text"],
            input_type=report_data.input_type or ("voice" if audio_bytes else "text"),
            audio_url=report_data.audio_blob_url,
            confidence_score=0.5,
            urgency_level="critical",  # Humanitarian baseline: immediate critical urgency for citizen SOS
            verification_score=0,
            vulnerability_level="critical",
            triage_tier="suspected_unconfirmed",
            cluster_density_factor=0.0,
            device_integrity_score=100,
            media_forensics_score=100,
            semantic_consistency_score=100,
            tamper_penalty=0,
            callback_status="pending",
            semantic_score=0,
            consistency_score=0,
            grounding_score=10,
            cluster_score=5,
            grounding_status="unreported_localized_incident",
            grounding_label="unreported_localized_incident",
            ai_verification_report={
                "status": "pending_audit",
                "message": "AI 5-layer emergency verification executing in background",
            },
            ai_extraction=initial_ext,
            media_source=report_data.media_source or "voice_direct",
            capture_nonce=report_data.capture_nonce,
            capture_timestamp=report_data.capture_timestamp,
            gps_location=gps_wkt,
            extracted_location_name=loc_name,
            anomaly_flags=[],
            status="pending_audit",
            relief_status="pending",
            relief_eta_minutes=None,
            relief_team_name=None,
        )

        self.session.add(report)
        await self.session.commit()
        await self.session.refresh(report)

        # Pre-Gemini Token Saving Heuristic (<1.5s audio and <8 chars text)
        is_audio_present = audio_bytes is not None and len(audio_bytes) > 0
        audio_too_short = True
        if is_audio_present:
            audio_too_short = False
            # Check WAV duration
            if "wav" in audio_mime_type.lower() or (len(audio_bytes) >= 4 and audio_bytes[:4] == b"RIFF"):
                try:
                    import wave, io
                    with wave.open(io.BytesIO(audio_bytes), 'rb') as wf:
                        duration = wf.getnframes() / float(wf.getframerate())
                        if duration < 1.5:
                            audio_too_short = True
                except Exception:
                    if len(audio_bytes) < 4000:
                        audio_too_short = True
            elif len(audio_bytes) < 4000:
                audio_too_short = True

        raw_user_text = (report_data.text_note or report_data.text_input or "").strip()
        has_valid_audio = is_audio_present and not audio_too_short
        has_valid_text = len(raw_user_text) >= 8
        has_explicit_hazards = bool(hazards) or bool(report_data.quick_buttons)

        is_spam_or_empty = (not has_valid_audio) and (not has_valid_text) and (not has_explicit_hazards)

        if is_spam_or_empty:
            report.status = "rejected"
            report.vulnerability_level = "false_or_prank"
            report.triage_tier = "flagged_or_prank"
            report.urgency_level = "low"
            report.verification_score = 0
            report.ai_verification_report = {
                "status": "rejected",
                "triage_tier": "FLAGGED_OR_PRANK",
                "reason": "Pre-Gemini discard: audio duration <1.5s and text <8 characters (spam/empty signal)",
            }
            await self.session.commit()
            print(f"[ReportService] Report {report.id} discarded pre-Gemini: token spend eliminated.")
            return report

        # Spatial Clustering & Deduplication: Attach duplicate within 150m and 12h as child reference
        if gps_tuple:
            try:
                from app.services.clustering_service import ClusteringService
                clustering_svc = ClusteringService(self.session)
                parent_id = await clustering_svc.find_and_attach_nearby_parent(
                    report_id=report.id,
                    lat=gps_tuple[0],
                    lng=gps_tuple[1],
                    radius_meters=150.0,
                    time_window_hours=12,
                )
                if parent_id:
                    report.parent_report_id = parent_id
                    await self.session.commit()
                    print(f"[ReportService] Report {report.id} attached as duplicate child under parent {parent_id}.")
            except Exception as cluster_err:
                print(f"[ReportService] Deduplication attachment warning: {cluster_err}")

        # 4. Immediate Coordinator WebSocket alert
        try:
            from app.api.routes.websocket import broadcast_report_update
            asyncio.create_task(
                broadcast_report_update(
                    report_id=str(report.id),
                    event_type="new_emergency_report",
                    data={
                        "report_id": str(report.id),
                        "status": "pending_audit",
                        "triage_tier": report.triage_tier,
                        "location_name": loc_name,
                        "raw_input": text_input,
                        "audio_url": report.audio_url,
                        "hazard_types": hazards,
                    },
                )
            )
        except Exception as ws_err:
            print(f"[ReportService] Coordinator initial alert warning: {ws_err}")

        # 5. Launch Background 5-Layer Verification Task
        dev_dict = report_data.device_info.model_dump() if report_data.device_info else None
        asyncio.create_task(
            _run_verification_background(
                report_id=report.id,
                location_name=loc_name,
                gps_tuple=gps_tuple,
                text_input=text_input,
                audio_bytes=audio_bytes,
                audio_mime_type=audio_mime_type,
                quick_hazard_tags=hazards,
                device_info=dev_dict,
                client_ip=client_ip,
                image_bytes=image_bytes,
                video_bytes=video_bytes,
                capture_nonce=report_data.capture_nonce,
            )
        )

        # Return persisted report immediately
        return report

        # Return persisted report immediately
        return report

    async def get_report_by_id(self, report_id: uuid.UUID) -> Optional[Report]:
        result = await self.session.execute(select(Report).where(Report.id == report_id))
        return result.scalars().first()

    async def get_report_by_display_code(self, display_code: str) -> Optional[Report]:
        """Find a report by display code like RP-2847, UUID, or latest."""
        if not display_code:
            return None
        clean_code = display_code.upper().replace("RP-", "").strip()
        if not clean_code:
            return None

        # Check if full UUID was passed
        try:
            val_uuid = uuid.UUID(display_code)
            rep = await self.get_report_by_id(val_uuid)
            if rep:
                return rep
        except (ValueError, AttributeError):
            pass

        result = await self.session.execute(select(Report).order_by(Report.created_at.desc()))
        reports = result.scalars().all()
        if not reports:
            return None

        # If user requests latest or default queued code
        if display_code.upper() in ["LATEST", "RP-LATEST", "RP-QUEUED", "RP-NEW", "QUEUED", "NEW"]:
            return reports[0]

        for r in reports:
            r_id_str = str(r.id).upper()
            if r_id_str[:4] == clean_code or f"RP-{r_id_str[:4]}" == display_code.upper() or r_id_str == display_code.upper():
                return r
        return None

    async def advance_relief_status(
        self,
        report_id: uuid.UUID,
        new_status: str,
        team_name: Optional[str] = None,
        eta_minutes: Optional[int] = None,
    ) -> Optional[Report]:
        report = await self.get_report_by_id(report_id)
        if not report:
            return None
        report.relief_status = new_status
        if team_name:
            report.relief_team_name = team_name
        if eta_minutes is not None:
            report.relief_eta_minutes = eta_minutes
        await self.session.commit()
        await self.session.refresh(report)
        return report


from fastapi import Depends
from app.db.database import get_db

async def get_report_service(session: AsyncSession = Depends(get_db)) -> ReportService:
    return ReportService(session)
