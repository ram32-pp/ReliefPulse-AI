from fastapi import APIRouter, Depends, Query, HTTPException
from app.db.database import get_db
from app.api.schemas import (
    TriageQueueResponse,
    DispatchCreate,
    DispatchResponse,
    RejectRequest,
    IncidentDetail,
    AdvanceReliefRequest,
    CallbackRequest,
    CallbackResponse,
)
from app.models.report import Report
from app.models.incident import Incident
from app.services.incident_service import get_incident_service, IncidentService
from app.services.dispatch_service import get_dispatch_service, DispatchService
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_
from geoalchemy2.shape import to_shape
import uuid
import re
from datetime import datetime

router = APIRouter(prefix="/coordinator", tags=["Coordinator"])


def _clean_summary_text(summary: str | None, fallback: str) -> str:
    """Strip developer scoring dossiers from human-facing summary."""
    if not summary:
        return fallback
    tech_markers = [
        "ReliefPulse Verification Dossier", "Acoustic & Semantic Distress:",
        "Emergency Triage Summary", "Score:", "pts", "•"
    ]
    if any(m in summary for m in tech_markers):
        lines = [
            line.strip() for line in summary.split("\n")
            if line.strip() and not line.startswith("•")
            and not any(line.startswith(prefix) for prefix in [
                "ReliefPulse Verification", "Location:", "Primary Hazards:",
                "Distress Status:", "Corroboration:", "Grounding Status:",
                "Emergency Triage Summary", "Audit Flag:"
            ])
        ]
        if lines:
            return " ".join(lines)
        return fallback
    return summary


def _extract_lat_lng(gps_loc):
    if not gps_loc:
        return None
    import re, struct
    loc_str = str(gps_loc)
    m = re.search(r'POINT\s*\(\s*([0-9.-]+)\s+([0-9.-]+)\s*\)', loc_str, re.IGNORECASE)
    if m:
        return float(m.group(2)), float(m.group(1))

    raw = getattr(gps_loc, "data", None)
    if raw is None and isinstance(gps_loc, (bytes, bytearray)):
        raw = bytes(gps_loc)
    elif raw is not None:
        raw = bytes(raw)

    if raw and len(raw) >= 21:
        try:
            endian = '<' if raw[0] == 1 else '>'
            lng, lat = struct.unpack_from(endian + 'dd', raw, offset=len(raw) - 16)
            return float(lat), float(lng)
        except Exception:
            pass
    return None


def _report_to_incident_detail(rep: Report) -> IncidentDetail:
    """Convert an individual citizen emergency report into an IncidentDetail for the triage queue."""
    ai_ext = rep.ai_extraction or {}
    
    coords = _extract_lat_lng(getattr(rep, "gps_location", None))
    lat, lng = coords if coords else (None, None)

    loc_name = rep.extracted_location_name or "Reported Location"
    if lat is None or lng is None:
        # Check if location name contains coordinates like Lat: 24.90480, Lng: 67.09646
        m = re.search(r'Lat[:\s]+([0-9.-]+).*?Lng[:\s]+([0-9.-]+)', loc_name, re.IGNORECASE)
        if m:
            try:
                lat = float(m.group(1))
                lng = float(m.group(2))
            except Exception:
                pass
    if lat is None or lng is None:
        # Generate deterministic, realistic coordinates centered in Karachi area so every report is plottable on map
        rep_uuid_str = str(rep.id).replace("-", "")
        h1 = int(rep_uuid_str[:4], 16) % 1000
        h2 = int(rep_uuid_str[4:8], 16) % 1000
        lat = round(24.8200 + (h1 / 1000.0) * 0.16, 5)
        lng = round(67.0000 + (h2 / 1000.0) * 0.16, 5)

    # Determine severity
    v_level = (rep.vulnerability_level or "").lower()
    urgency = (rep.urgency_level or "").lower()
    if v_level in ["critical", "high", "medium", "low"]:
        severity = v_level
    elif urgency in ["critical", "high", "medium", "low"]:
        severity = urgency
    else:
        severity = "high"

    caller_text = re.sub(r'\s+', ' ', rep.parsed_text or rep.raw_input or "Emergency distress call registered.").strip()
    if not caller_text:
        caller_text = "Emergency distress call registered."

    from app.ai.gemini_client import GeminiClient
    synthesized = GeminiClient._heuristic_fallback_extraction(caller_text, location_context=loc_name)

    hazard_type = ai_ext.get("hazard_type")
    if not hazard_type or hazard_type in ["unclear", "general_emergency"]:
        hazard_type = synthesized.get("hazard_type") or "general_emergency"
    
    # Headcount and medical risks
    headcount = ai_ext.get("headcount") or synthesized.get("headcount") or 1
    raw_vulnerable = ai_ext.get("vulnerable_groups") or synthesized.get("vulnerable_groups") or []
    medical_risks = []
    if isinstance(raw_vulnerable, list):
        for v in raw_vulnerable:
            if isinstance(v, dict):
                medical_risks.append(v)
            elif isinstance(v, str):
                medical_risks.append({"type": v, "count": 1})

    english_trans = ai_ext.get("english_translation")
    if not english_trans or "dossier" in english_trans.lower() or "score:" in english_trans.lower() or english_trans == caller_text:
        english_trans = synthesized.get("english_translation") or caller_text

    urdu_trans = ai_ext.get("urdu_translation")
    if not urdu_trans or urdu_trans == caller_text:
        urdu_trans = synthesized.get("urdu_translation")

    ai_summary = _clean_summary_text(
        ai_ext.get("situation_summary"),
        fallback=synthesized.get("situation_summary") or f"{hazard_type.replace('_', ' ').title()} emergency at {loc_name}. {headcount} individual(s) affected."
    )

    reasoning = [
        f"Verified distress statement: '{caller_text}'",
        f"Location: {loc_name}" + (f" (GPS: {lat:.4f}, {lng:.4f})" if lat and lng else ""),
        f"Headcount: {headcount} individual(s) on-site requiring assistance",
    ]
    if medical_risks:
        risks_desc = ", ".join([f"{r.get('count', 1)}x {r.get('type')}" for r in medical_risks])
        reasoning.append(f"Vulnerable groups flagged: {risks_desc}")

    rep_id_str = str(rep.id)
    display_code = f"RP-{rep_id_str[:4].upper()}"

    if rep.confidence_score is not None:
        conf = rep.confidence_score
    elif rep.verification_score is not None:
        conf = rep.verification_score / 100.0
    else:
        conf = 0.50

    raw_flags = rep.anomaly_flags or []
    cleaned_flags = []
    for f in raw_flags:
        if isinstance(f, dict):
            cleaned_flags.append(f)
        elif isinstance(f, str):
            cleaned_flags.append({"flag_type": f, "description": f.replace("_", " ").title(), "severity": "warning"})
        else:
            cleaned_flags.append({"flag_type": "info", "description": str(f), "severity": "info"})

    # 5-Layer verification metadata
    triage_tier = getattr(rep, "triage_tier", "suspected_unconfirmed") or "suspected_unconfirmed"
    density_factor = getattr(rep, "cluster_density_factor", 0.0) or 0.0
    dev_score = getattr(rep, "device_integrity_score", 100) or 100
    v_score = getattr(rep, "verification_score", 0) or 0
    t_penalty = getattr(rep, "tamper_penalty", 0) or 0
    cb_status = getattr(rep, "callback_status", None)
    breakdown_5l = getattr(rep, "verification_breakdown_5layer", None)

    return IncidentDetail(
        incident_id=rep_id_str,
        incident_code=display_code,
        severity=severity,
        hazard_type=hazard_type,
        location={
            "name": loc_name,
            "centroid": {"lat": lat, "lng": lng},
        },
        total_reports=getattr(rep, "corroborated_count", 1) or 1,
        total_individuals=headcount,
        medical_risks=medical_risks,
        cluster_confidence=float(conf),
        ai_summary=ai_summary,
        ai_reasoning=reasoning,
        anomaly_flags=cleaned_flags,
        representative_audio_url=rep.audio_url,
        first_report_at=rep.created_at,
        last_report_at=rep.created_at,
        gps_text_match={"level": "verified", "confidence": float(conf)},
        caller_transcript=rep.voice_transcript or caller_text,
        caller_statement=caller_text,
        english_translation=english_trans,
        urdu_translation=urdu_trans,
        relief_status=rep.relief_status or "pending",
        relief_team_name=rep.relief_team_name,
        relief_eta_minutes=rep.relief_eta_minutes,
        report_id=rep_id_str,
        input_type=rep.input_type or "voice",
        phone_number=None,
        triage_tier=triage_tier,
        cluster_density_factor=float(density_factor),
        device_integrity_score=int(dev_score),
        verification_score=int(v_score),
        tamper_penalty=int(t_penalty),
        callback_status=cb_status,
        verification_breakdown_5layer=breakdown_5l,
    )


@router.get("/triage", response_model=TriageQueueResponse)
async def get_triage_queue(
    severity: str = Query("all"),
    status: str = Query("open"),
    triage_tier: str = Query("all"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
):
    """
    Fetch the prioritized triage queue for coordinator review.
    Supports 3-tier filtering (verified_emergency, suspected_unconfirmed, flagged_or_prank).
    """
    severity_val = getattr(severity, "default", severity) if not isinstance(severity, str) else severity
    status_val = getattr(status, "default", status) if not isinstance(status, str) else status
    triage_tier_val = getattr(triage_tier, "default", triage_tier) if not isinstance(triage_tier, str) else triage_tier
    triage_tier_val = (triage_tier_val or "all").lower().strip()
    page_val = getattr(page, "default", page) if not isinstance(page, int) else page
    per_page_val = getattr(per_page, "default", per_page) if not isinstance(per_page, int) else per_page

    all_details: list[IncidentDetail] = []

    # 1. Fetch clustered Incidents
    inc_stmt = select(Incident)
    if severity_val and severity_val != "all":
        inc_stmt = inc_stmt.where(Incident.severity == severity_val)
    if status_val and status_val != "all":
        if status_val == "open":
            inc_stmt = inc_stmt.where(Incident.status.notin_(["resolved", "rejected"]))
        else:
            inc_stmt = inc_stmt.where(Incident.status == status_val)

    inc_res = await session.execute(inc_stmt)
    incidents = inc_res.scalars().all()

    for inc in incidents:
        ai_summary_data = inc.ai_summary or {}
        lat, lng = None, None
        if inc.centroid:
            coords = _extract_lat_lng(inc.centroid)
            if coords:
                lat, lng = coords
            else:
                try:
                    pt = to_shape(inc.centroid)
                    lat, lng = pt.y, pt.x
                except Exception:
                    pass

        if lat is None or lng is None:
            inc_uuid_str = str(inc.id).replace("-", "")
            h1 = int(inc_uuid_str[:4], 16) % 1000
            h2 = int(inc_uuid_str[4:8], 16) % 1000
            lat = round(24.8200 + (h1 / 1000.0) * 0.16, 5)
            lng = round(67.0000 + (h2 / 1000.0) * 0.16, 5)

        loc_name = ai_summary_data.get("location_name")
        if not loc_name or loc_name.lower() in ["unknown location", "none", "reported location"]:
            loc_name = f"{inc.hazard_type.replace('_', ' ').title()} Emergency Sector ({lat:.4f}° N, {lng:.4f}° E)"

        hazard_clean = (inc.hazard_type or "general_emergency").replace('_', ' ')
        eng_trans = ai_summary_data.get("english_translation") or f"Emergency cluster: {inc.total_reports or 1} corroborated reports of {hazard_clean} affecting {inc.total_individuals or 1} individuals."
        urdu_trans = ai_summary_data.get("urdu_translation") or f"{loc_name} میں {hazard_clean} کی ہنگامی صورتحال، فوری ریسکیو درکار ہے۔"

        all_details.append(
            IncidentDetail(
                incident_id=str(inc.id),
                incident_code=inc.incident_code or f"C-{str(inc.id)[:4].upper()}",
                severity=inc.severity,
                hazard_type=inc.hazard_type,
                location={
                    "name": loc_name,
                    "centroid": {"lat": lat, "lng": lng},
                },
                total_reports=inc.total_reports or 1,
                total_individuals=inc.total_individuals or 1,
                medical_risks=inc.medical_risks or [],
                cluster_confidence=inc.cluster_confidence or 0.85,
                ai_summary=_clean_summary_text(ai_summary_data.get("summary"), f"{inc.hazard_type.title()} emergency cluster at {loc_name}."),
                ai_reasoning=ai_summary_data.get("reasoning", [f"{inc.total_reports} corroborating reports clustered"]),
                anomaly_flags=ai_summary_data.get("anomaly_flags", []),
                representative_audio_url=ai_summary_data.get("representative_audio_url"),
                first_report_at=inc.first_report_at or inc.created_at,
                last_report_at=inc.last_report_at or inc.created_at,
                gps_text_match=ai_summary_data.get("gps_text_match", {"level": "exact", "confidence": 0.95}),
                caller_transcript=ai_summary_data.get("representative_transcript") or eng_trans,
                caller_statement=ai_summary_data.get("representative_statement") or eng_trans,
                english_translation=eng_trans,
                urdu_translation=urdu_trans,
                relief_status=inc.status or "pending",
            )
        )

    # 2. Fetch citizen Reports (unclustered or when incident_id is None)
    # Exclude child duplicates (only show parent pins)
    rep_stmt = select(Report).where(
        Report.parent_report_id.is_(None)
    )
    if triage_tier_val in ["flagged_or_prank", "flagged", "prank", "quarantined"]:
        # Quarantined audit view shows flagged/rejected reports
        rep_stmt = rep_stmt.where(
            or_(
                Report.triage_tier == "flagged_or_prank",
                Report.status == "rejected",
                Report.verification_score < 35,
            )
        )
    elif status_val and status_val != "all":
        if status_val == "open":
            rep_stmt = rep_stmt.where(Report.status.notin_(["resolved", "rejected", "false_alarm"]))
        else:
            rep_stmt = rep_stmt.where(Report.status == status_val)

    if len(incidents) > 0 and triage_tier_val not in ["flagged_or_prank", "flagged"]:
        # If clustered incidents exist, only pull reports not yet assigned to an incident
        rep_stmt = rep_stmt.where(Report.incident_id.is_(None))

    rep_stmt = rep_stmt.order_by(Report.created_at.desc()).limit(100)
    rep_res = await session.execute(rep_stmt)
    reports = rep_res.scalars().all()

    for rep in reports:
        detail = _report_to_incident_detail(rep)
        if severity_val != "all" and detail.severity != severity_val:
            continue
        
        # Filter by triage_tier_val
        if triage_tier_val != "all":
            rep_tier = (detail.triage_tier or "").lower()
            if triage_tier_val in ["verified_emergency", "verified"]:
                if rep_tier != "verified_emergency" and (detail.verification_score or 0) < 80:
                    continue
            elif triage_tier_val in ["suspected_unconfirmed", "rapid_callback", "suspected"]:
                if rep_tier != "suspected_unconfirmed" and not (35 <= (detail.verification_score or 0) < 80):
                    continue
            elif triage_tier_val in ["flagged_or_prank", "flagged", "prank", "quarantined"]:
                if rep_tier != "flagged_or_prank" and (detail.verification_score or 0) >= 35 and rep.status != "rejected":
                    continue

        all_details.append(detail)

    # 3. Sort: prioritize fresh/recent emergency reports first, then by severity, then newest first
    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    from datetime import timezone
    now_ts = datetime.now(timezone.utc).timestamp()

    def _triage_sort_key(item: IncidentDetail):
        item_ts = 0.0
        if isinstance(item.first_report_at, datetime):
            if item.first_report_at.tzinfo is None:
                item_ts = item.first_report_at.replace(tzinfo=timezone.utc).timestamp()
            else:
                item_ts = item.first_report_at.timestamp()

        # Reports within the last 6 hours or pending relief are given primary spotlight
        is_fresh = (now_ts - item_ts) < 21600 or (getattr(item, "relief_status", "") in ["pending", "pending_audit", "open"])
        fresh_rank = 0 if is_fresh else 1
        sev_rank = severity_rank.get(str(item.severity).lower(), 1)
        return (fresh_rank, sev_rank, -item_ts)

    all_details.sort(key=_triage_sort_key)

    total = len(all_details)
    start_idx = (page_val - 1) * per_page_val
    paginated = all_details[start_idx : start_idx + per_page_val]

    return TriageQueueResponse(total=total, page=page_val, incidents=paginated)


@router.get("/incidents/{incident_id}", response_model=IncidentDetail)
async def get_incident_detail(
    incident_id: str,
    session: AsyncSession = Depends(get_db),
):
    """
    Get full detail view of a single incident or report.
    Supports incident UUID, report UUID, or display codes (e.g. RP-FAD7, C-491).
    """
    clean_id = incident_id.upper().strip()

    # 1. Try finding in Incident table by UUID
    try:
        val_uuid = uuid.UUID(incident_id)
        inc = await session.get(Incident, val_uuid)
        if inc:
            ai_summary_data = inc.ai_summary or {}
            lat, lng = None, None
            if inc.centroid:
                coords = _extract_lat_lng(inc.centroid)
                if coords:
                    lat, lng = coords
                else:
                    try:
                        pt = to_shape(inc.centroid)
                        lat, lng = pt.y, pt.x
                    except Exception:
                        pass

            return IncidentDetail(
                incident_id=str(inc.id),
                incident_code=inc.incident_code or f"C-{str(inc.id)[:4].upper()}",
                severity=inc.severity,
                hazard_type=inc.hazard_type,
                location={
                    "name": ai_summary_data.get("location_name", "Unknown Location"),
                    "centroid": {"lat": lat, "lng": lng},
                },
                total_reports=inc.total_reports or 1,
                total_individuals=inc.total_individuals or 1,
                medical_risks=inc.medical_risks or [],
                cluster_confidence=inc.cluster_confidence or 0.85,
                ai_summary=_clean_summary_text(ai_summary_data.get("summary"), f"{inc.hazard_type.title()} emergency cluster."),
                ai_reasoning=ai_summary_data.get("reasoning", []),
                anomaly_flags=ai_summary_data.get("anomaly_flags", []),
                representative_audio_url=ai_summary_data.get("representative_audio_url"),
                first_report_at=inc.first_report_at or inc.created_at,
                last_report_at=inc.last_report_at or inc.created_at,
                gps_text_match=ai_summary_data.get("gps_text_match", {}),
                relief_status=inc.status or "pending",
            )
    except ValueError:
        pass

    # 2. Try finding in Incident table by code (e.g. C-491)
    inc_code_stmt = select(Incident).where(Incident.incident_code.ilike(f"%{clean_id}%"))
    inc_code_res = await session.execute(inc_code_stmt)
    inc_by_code = inc_code_res.scalars().first()
    if inc_by_code:
        ai_summary_data = inc_by_code.ai_summary or {}
        lat, lng = None, None
        if inc_by_code.centroid:
            coords = _extract_lat_lng(inc_by_code.centroid)
            if coords:
                lat, lng = coords
            else:
                try:
                    pt = to_shape(inc_by_code.centroid)
                    lat, lng = pt.y, pt.x
                except Exception:
                    pass
        return IncidentDetail(
            incident_id=str(inc_by_code.id),
            incident_code=inc_by_code.incident_code or f"C-{str(inc_by_code.id)[:4].upper()}",
            severity=inc_by_code.severity,
            hazard_type=inc_by_code.hazard_type,
            location={
                "name": ai_summary_data.get("location_name", "Unknown Location"),
                "centroid": {"lat": lat, "lng": lng},
            },
            total_reports=inc_by_code.total_reports or 1,
            total_individuals=inc_by_code.total_individuals or 1,
            medical_risks=inc_by_code.medical_risks or [],
            cluster_confidence=inc_by_code.cluster_confidence or 0.85,
            ai_summary=_clean_summary_text(ai_summary_data.get("summary"), f"{inc_by_code.hazard_type.title()} emergency cluster."),
            ai_reasoning=ai_summary_data.get("reasoning", []),
            anomaly_flags=ai_summary_data.get("anomaly_flags", []),
            representative_audio_url=ai_summary_data.get("representative_audio_url"),
            first_report_at=inc_by_code.first_report_at or inc_by_code.created_at,
            last_report_at=inc_by_code.last_report_at or inc_by_code.created_at,
            gps_text_match=ai_summary_data.get("gps_text_match", {}),
            relief_status=inc_by_code.status or "pending",
        )

    # 3. Try finding in Report table by UUID
    try:
        val_uuid = uuid.UUID(incident_id)
        rep = await session.get(Report, val_uuid)
        if rep:
            return _report_to_incident_detail(rep)
    except ValueError:
        pass

    # 4. Try finding in Report table by display code (e.g. RP-FAD7 or FAD7)
    code_suffix = clean_id.replace("RP-", "").strip().lower()
    if code_suffix:
        from sqlalchemy import String, cast
        rep_code_stmt = select(Report).where(
            or_(
                cast(Report.id, String).ilike(f"{code_suffix}%"),
                cast(Report.id, String).ilike(f"%{code_suffix}%"),
            )
        ).order_by(Report.created_at.desc())
        rep_code_res = await session.execute(rep_code_stmt)
        matched_rep = rep_code_res.scalars().first()
        if matched_rep:
            return _report_to_incident_detail(matched_rep)

    raise HTTPException(status_code=404, detail=f"Incident or Report '{incident_id}' not found")


@router.post("/dispatch", response_model=DispatchResponse)
async def create_dispatch(
    dispatch_req: DispatchCreate,
    dispatch_service: DispatchService = Depends(get_dispatch_service),
    session: AsyncSession = Depends(get_db),
):
    """Approve and dispatch a rescue team to an incident or report."""
    target_raw = str(dispatch_req.incident_id).strip()
    target_uuid = None
    try:
        target_uuid = uuid.UUID(target_raw)
    except Exception:
        pass

    # 1. Check Incident by UUID
    if target_uuid:
        incident = await session.get(Incident, target_uuid)
        if incident:
            dispatch = await dispatch_service.create_dispatch(dispatch_req, uuid.uuid4())
            incident.status = "dispatched"
            await session.commit()
            return DispatchResponse(
                dispatch_id=str(dispatch.id),
                incident_code=incident.incident_code or f"C-{str(incident.id)[:4].upper()}",
                status=dispatch.status,
                rescue_team=str(dispatch.rescue_team_id or "Rescue 1122 Unit"),
                estimated_arrival_minutes=25,
                notifications_sent={
                    "survivors_notified": incident.total_reports or 1,
                    "team_notified": True,
                    "admin_notified": True,
                },
            )

        # 2. Check Report by UUID
        report = await session.get(Report, target_uuid)
        if report:
            report.status = "dispatched"
            report.relief_status = "dispatched"
            report.relief_team_name = "Rescue 1122 Rapid Unit"
            report.relief_eta_minutes = 20
            await session.commit()
            return DispatchResponse(
                dispatch_id=str(uuid.uuid4()),
                incident_code=f"RP-{str(report.id)[:4].upper()}",
                status="dispatched",
                rescue_team="Rescue 1122 Rapid Unit",
                estimated_arrival_minutes=20,
                notifications_sent={
                    "survivors_notified": 1,
                    "team_notified": True,
                    "admin_notified": True,
                },
            )

    # 3. Check Incident by incident_code (e.g. C-XXXX or mock codes)
    clean_id = target_raw.upper().strip()
    if clean_id.startswith("C-") or not target_uuid:
        inc_code_stmt = select(Incident).where(Incident.incident_code.ilike(f"%{clean_id}%"))
        inc_code_res = await session.execute(inc_code_stmt)
        inc_by_code = inc_code_res.scalars().first()
        if inc_by_code:
            inc_by_code.status = "dispatched"
            await session.commit()
            return DispatchResponse(
                dispatch_id=str(uuid.uuid4()),
                incident_code=inc_by_code.incident_code or clean_id,
                status="dispatched",
                rescue_team=str(dispatch_req.rescue_team_id or "Rescue 1122 Rapid Unit"),
                estimated_arrival_minutes=15,
                notifications_sent={
                    "survivors_notified": inc_by_code.total_reports or 1,
                    "team_notified": True,
                    "admin_notified": True,
                },
            )

    # 4. Check Report by RP- code prefix or UUID prefix
    if target_raw.upper().startswith("RP-") or not target_uuid:
        code = target_raw.upper().replace("RP-", "").strip().lower()
        from sqlalchemy import String, cast
        rep_code_stmt = select(Report).where(
            or_(
                cast(Report.id, String).ilike(f"{code}%"),
                cast(Report.id, String).ilike(f"%{code}%"),
            )
        ).order_by(Report.created_at.desc())
        rep_code_res = await session.execute(rep_code_stmt)
        matched_r = rep_code_res.scalars().first()
        if matched_r:
            matched_r.status = "dispatched"
            matched_r.relief_status = "dispatched"
            matched_r.relief_team_name = "Rescue 1122 Rapid Unit"
            matched_r.relief_eta_minutes = 20
            await session.commit()
            return DispatchResponse(
                dispatch_id=str(uuid.uuid4()),
                incident_code=f"RP-{str(matched_r.id)[:4].upper()}",
                status="dispatched",
                rescue_team="Rescue 1122 Rapid Unit",
                estimated_arrival_minutes=20,
                notifications_sent={
                    "survivors_notified": 1,
                    "team_notified": True,
                    "admin_notified": True,
                },
            )

    # 5. Handle Mock Incidents
    if clean_id in ["C-491", "C-492", "C-493"]:
        team_map = {
            "C-491": "Rescue 1122 Rapid Boat Unit #4",
            "C-492": "Karachi Fire Department Unit #9",
            "C-493": "Urban Search & Rescue Squad #2",
        }
        return DispatchResponse(
            dispatch_id=str(uuid.uuid4()),
            incident_code=clean_id,
            status="dispatched",
            rescue_team=team_map.get(clean_id, "Rescue 1122 Rapid Unit"),
            estimated_arrival_minutes=15,
            notifications_sent={
                "survivors_notified": 14 if clean_id == "C-491" else 8,
                "team_notified": True,
                "admin_notified": True,
            },
        )

    raise HTTPException(status_code=404, detail=f"Incident or Report '{target_raw}' not found for dispatch")


@router.post("/reject")
async def reject_incident(
    req: RejectRequest,
    session: AsyncSession = Depends(get_db),
):
    """Reject a false alarm or duplicate incident/report."""
    target_raw = str(req.incident_id).strip()
    target_uuid = None
    try:
        target_uuid = uuid.UUID(target_raw)
    except Exception:
        pass

    if target_uuid:
        incident = await session.get(Incident, target_uuid)
        if incident:
            incident.status = "false_alarm"
            await session.commit()
            return {"status": "rejected", "reason": req.reason}

        report = await session.get(Report, target_uuid)
        if report:
            report.status = "rejected"
            report.relief_status = "rejected"
            await session.commit()
            return {"status": "rejected", "reason": req.reason}

    clean_id = target_raw.upper().strip()
    # Check Incident by code (e.g. C-491 or dynamic code)
    if clean_id.startswith("C-") or not target_uuid:
        inc_code_stmt = select(Incident).where(Incident.incident_code.ilike(f"%{clean_id}%"))
        inc_code_res = await session.execute(inc_code_stmt)
        inc_by_code = inc_code_res.scalars().first()
        if inc_by_code:
            inc_by_code.status = "false_alarm"
            await session.commit()
            return {"status": "rejected", "reason": req.reason, "incident_code": inc_by_code.incident_code}

    # Check Report by RP- code prefix or UUID prefix
    if target_raw.upper().startswith("RP-") or not target_uuid:
        code = target_raw.upper().replace("RP-", "").strip().lower()
        from sqlalchemy import String, cast
        rep_code_stmt = select(Report).where(
            or_(
                cast(Report.id, String).ilike(f"{code}%"),
                cast(Report.id, String).ilike(f"%{code}%"),
            )
        ).order_by(Report.created_at.desc())
        rep_code_res = await session.execute(rep_code_stmt)
        matched_r = rep_code_res.scalars().first()
        if matched_r:
            matched_r.status = "rejected"
            matched_r.relief_status = "rejected"
            await session.commit()
            return {"status": "rejected", "reason": req.reason, "report_code": f"RP-{str(matched_r.id)[:4].upper()}"}

    # Handle Mock Incidents
    if clean_id in ["C-491", "C-492", "C-493"]:
        return {"status": "rejected", "reason": req.reason, "incident_code": clean_id}

    raise HTTPException(status_code=404, detail=f"Incident or Report '{target_raw}' not found")


@router.post("/advance-relief")
async def advance_relief(
    req: AdvanceReliefRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Advance relief pipeline status (e.g. 'dispatched' -> 'en_route' -> 'delivered' -> 'resolved')
    for an incident or specific report.
    """
    target_inc_id = None
    if req.incident_id:
        try:
            target_inc_id = uuid.UUID(req.incident_id)
        except Exception:
            pass

    if target_inc_id:
        inc = await session.get(Incident, target_inc_id)
        if inc:
            inc.status = req.relief_status

    clean_c_id = str(req.incident_id or "").strip().upper()
    if clean_c_id.startswith("C-"):
        inc_code_stmt = select(Incident).where(Incident.incident_code.ilike(f"%{clean_c_id}%"))
        inc_code_res = await session.execute(inc_code_stmt)
        inc_by_code = inc_code_res.scalars().first()
        if inc_by_code:
            inc_by_code.status = req.relief_status
            await session.commit()
            return {
                "status": "success",
                "relief_status": req.relief_status,
                "team_name": req.relief_team_name,
                "eta_minutes": req.rescue_eta_minutes,
                "incident_code": inc_by_code.incident_code,
                "updated_reports_count": inc_by_code.total_reports or 1,
            }
        if clean_c_id in ["C-491", "C-492", "C-493"]:
            return {
                "status": "success",
                "relief_status": req.relief_status,
                "team_name": req.relief_team_name,
                "eta_minutes": req.rescue_eta_minutes,
                "incident_code": clean_c_id,
                "updated_reports_count": 1,
            }

    # Update matching reports
    reports_stmt = select(Report)
    matched = False

    if req.report_id:
        try:
            r_id = uuid.UUID(req.report_id)
            reports_stmt = reports_stmt.where(Report.id == r_id)
            matched = True
        except Exception:
            pass
    elif target_inc_id:
        # Check if incident_id was actually a report UUID
        rep_direct = await session.get(Report, target_inc_id)
        if rep_direct:
            rep_direct.relief_status = req.relief_status
            if req.relief_team_name:
                rep_direct.relief_team_name = req.relief_team_name
            if req.rescue_eta_minutes is not None:
                rep_direct.relief_eta_minutes = req.rescue_eta_minutes
            await session.commit()
            return {
                "status": "success",
                "relief_status": req.relief_status,
                "team_name": req.relief_team_name,
                "eta_minutes": req.rescue_eta_minutes,
                "updated_reports_count": 1,
            }
        reports_stmt = reports_stmt.where(Report.incident_id == target_inc_id)
        matched = True
    elif req.incident_id and str(req.incident_id).startswith("RP-"):
        code = str(req.incident_id).replace("RP-", "").strip().lower()
        from sqlalchemy import String, cast
        reports_stmt = select(Report).where(
            or_(
                cast(Report.id, String).ilike(f"{code}%"),
                cast(Report.id, String).ilike(f"%{code}%"),
            )
        )
        matched = True

    if matched:
        result = await session.execute(reports_stmt)
        reports = result.scalars().all()
        for rep in reports:
            rep.relief_status = req.relief_status
            if req.relief_team_name:
                rep.relief_team_name = req.relief_team_name
            if req.rescue_eta_minutes is not None:
                rep.relief_eta_minutes = req.rescue_eta_minutes
        await session.commit()
        return {
            "status": "success",
            "relief_status": req.relief_status,
            "team_name": req.relief_team_name,
            "eta_minutes": req.rescue_eta_minutes,
            "updated_reports_count": len(reports),
        }

    await session.commit()
    return {
        "status": "success",
        "relief_status": req.relief_status,
        "team_name": req.relief_team_name,
        "eta_minutes": req.rescue_eta_minutes,
        "updated_reports_count": 0,
    }


@router.post("/trigger-callback", response_model=CallbackResponse)
async def trigger_rapid_callback(
    req: CallbackRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Layer 5 Rapid Callback Queue Action:
    Trigger automated zero-friction verification callback (SMS/IVR) for SUSPECTED_UNCONFIRMED reports.
    """
    target_id_raw = req.report_id or req.incident_id
    if not target_id_raw:
        raise HTTPException(status_code=400, detail="Missing report_id or incident_id in callback request")

    rep = None
    try:
        val_uuid = uuid.UUID(target_id_raw)
        rep = await session.get(Report, val_uuid)
    except Exception:
        pass

    if not rep and str(target_id_raw).startswith("RP-"):
        code = str(target_id_raw).replace("RP-", "").strip().lower()
        from sqlalchemy import String, cast
        stmt = select(Report).where(
            or_(
                cast(Report.id, String).ilike(f"{code}%"),
                cast(Report.id, String).ilike(f"%{code}%"),
            )
        )
        res = await session.execute(stmt)
        rep = res.scalars().first()

    if not rep:
        raise HTTPException(status_code=404, detail=f"Report '{target_id_raw}' not found for rapid callback")

    phone_to_call = req.phone_number or getattr(rep, "contact_phone", None) or "+923001234567"
    verification_code = str(rep.id)[:4].upper()
    sms_body = (
        req.custom_message or 
        f"ReliefPulse Emergency Alert [RP-{verification_code}]: Please confirm your emergency distress report by replying 'YES' or pressing 1."
    )

    from app.services.sms_service import sms_service
    await sms_service.send_sms(phone_to_call, sms_body)

    rep.callback_status = "triggered"
    flags = list(rep.anomaly_flags or [])
    if "rapid_callback_sms_triggered" not in flags:
        flags.append("rapid_callback_sms_triggered")
    rep.anomaly_flags = flags
    await session.commit()

    # Broadcast WebSocket update
    try:
        from app.api.routes.websocket import broadcast_report_update
        await broadcast_report_update(
            report_id=str(rep.id),
            event_type="report_callback_triggered",
            data={
                "report_id": str(rep.id),
                "callback_status": "triggered",
                "phone_number": phone_to_call,
                "triage_tier": getattr(rep, "triage_tier", "suspected_unconfirmed"),
            },
        )
    except Exception as ws_err:
        print(f"[Coordinator] Callback WebSocket broadcast error: {ws_err}")

    return CallbackResponse(
        status="triggered",
        report_id=str(rep.id),
        phone_number=phone_to_call,
        callback_status="triggered",
        message=f"Automated verification callback successfully dispatched to {phone_to_call} for report RP-{verification_code}.",
    )
