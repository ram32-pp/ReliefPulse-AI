from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.incident import Incident, IncidentStatus
from app.models.incident_log import IncidentLog
from app.models.report import Report
import uuid
import random
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

# Strict deterministic transition graph
VALID_STATE_TRANSITIONS: Dict[IncidentStatus, List[IncidentStatus]] = {
    IncidentStatus.PENDING: [IncidentStatus.VERIFIED, IncidentStatus.REJECTED],
    IncidentStatus.VERIFIED: [IncidentStatus.ASSIGNED, IncidentStatus.REJECTED],
    IncidentStatus.ASSIGNED: [IncidentStatus.EN_ROUTE, IncidentStatus.REJECTED],
    IncidentStatus.EN_ROUTE: [IncidentStatus.REACHED, IncidentStatus.REJECTED],
    IncidentStatus.REACHED: [IncidentStatus.RESOLVED],
    IncidentStatus.RESOLVED: [],
    IncidentStatus.REJECTED: [],
}

class IncidentService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _generate_incident_code(self) -> str:
        return f"RP-{random.randint(1000, 9999)}"

    def _calculate_severity(self, total_individuals: int, medical_risks: List[Dict[str, Any]], reports_count: int) -> str:
        has_vulnerable = any(r.get("type") in ["infant", "elderly", "pregnant"] for risk_list in medical_risks if risk_list for r in risk_list)
        if total_individuals >= 20 or has_vulnerable or reports_count >= 10:
            return "critical"
        if total_individuals >= 5 or medical_risks:
            return "high"
        return "medium"

    async def transition_status(
        self,
        incident_id: uuid.UUID,
        new_status: Union[IncidentStatus, str],
        changed_by_user_id: Optional[uuid.UUID] = None,
        assigned_team_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
        metadata_snapshot: Optional[dict] = None,
    ) -> Incident:
        """
        Enforce strict deterministic state transitions:
        Pending -> Verified -> Assigned -> En Route -> Reached -> Resolved (or Rejected).
        Enforces database constraint: cannot set 'assigned' without valid assigned_team_id.
        Creates immutable audit record in incident_logs.
        """
        target_status = IncidentStatus(new_status) if isinstance(new_status, str) else new_status

        incident = await self.session.get(Incident, incident_id)
        if not incident:
            raise ValueError(f"Incident {incident_id} not found")

        current_status_str = incident.status or IncidentStatus.PENDING.value
        try:
            current_status = IncidentStatus(current_status_str)
        except ValueError:
            # Normalize legacy statuses like 'open' -> PENDING
            current_status = IncidentStatus.PENDING

        allowed_targets = VALID_STATE_TRANSITIONS.get(current_status, [])
        if target_status not in allowed_targets:
            raise ValueError(
                f"Invalid incident state transition from '{current_status.value}' to '{target_status.value}'. "
                f"Allowed transitions: {[s.value for s in allowed_targets]}"
            )

        # Enforce assignment team constraint
        effective_team_id = assigned_team_id or incident.assigned_team_id
        if target_status == IncidentStatus.ASSIGNED and not effective_team_id:
            raise ValueError("Database constraint violation: cannot set status to 'assigned' without a valid assigned_team_id")

        if assigned_team_id:
            incident.assigned_team_id = assigned_team_id

        previous_status_val = incident.status
        incident.status = target_status.value

        if target_status == IncidentStatus.RESOLVED:
            incident.resolved_at = datetime.utcnow()

        # Immutable audit log
        log_entry = IncidentLog(
            incident_id=incident.id,
            previous_status=previous_status_val,
            new_status=target_status.value,
            changed_by_user_id=changed_by_user_id,
            timestamp=datetime.utcnow(),
            notes=notes,
            metadata_snapshot=metadata_snapshot or {
                "assigned_team_id": str(effective_team_id) if effective_team_id else None,
                "total_reports": incident.total_reports,
            },
        )
        self.session.add(log_entry)

        await self.session.commit()
        return incident

    async def merge_reports_into_incident(self, report_ids: List[uuid.UUID], cluster_data: Dict[str, Any]) -> Incident:
        # Check if any report already belongs to an incident
        stmt = select(Incident).join(Report).where(Report.id.in_(report_ids))
        result = await self.session.execute(stmt)
        existing_incident = result.scalars().first()

        severity = self._calculate_severity(
            cluster_data["total_individuals"], 
            cluster_data["medical_risks"] or [],
            cluster_data["total_reports"]
        )

        if existing_incident:
            # Update existing
            existing_incident.total_reports = cluster_data["total_reports"]
            existing_incident.total_individuals = cluster_data["total_individuals"]
            existing_incident.severity = severity
            existing_incident.cluster_confidence = cluster_data["avg_confidence"]
            incident = existing_incident
        else:
            # Create new with PENDING status
            incident = Incident(
                incident_code=self._generate_incident_code(),
                hazard_type=cluster_data["hazard_types"][0] if cluster_data["hazard_types"] else "other",
                severity=severity,
                centroid=f"SRID=4326;{cluster_data['centroid']}",
                total_reports=cluster_data["total_reports"],
                total_individuals=cluster_data["total_individuals"],
                medical_risks=cluster_data["medical_risks"],
                cluster_confidence=cluster_data["avg_confidence"],
                status=IncidentStatus.PENDING.value,
            )
            self.session.add(incident)
            await self.session.flush()

            # Record initial log
            self.session.add(IncidentLog(
                incident_id=incident.id,
                previous_status=None,
                new_status=IncidentStatus.PENDING.value,
                notes=f"Created via spatiotemporal clustering of {cluster_data['total_reports']} reports",
            ))

        # Update reports to point to this incident
        await self.session.execute(
            update(Report)
            .where(Report.id.in_(report_ids))
            .values(incident_id=incident.id, status="clustered")
        )
        
        await self.session.commit()
        return incident

from fastapi import Depends
from app.db.database import get_db

async def get_incident_service(session: AsyncSession = Depends(get_db)) -> IncidentService:
    return IncidentService(session)
