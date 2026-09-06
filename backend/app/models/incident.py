import uuid
import enum
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry
from .base import BaseModel


class IncidentStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    ASSIGNED = "assigned"
    EN_ROUTE = "en_route"
    REACHED = "reached"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class Incident(BaseModel):
    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint(
            "status != 'assigned' OR assigned_team_id IS NOT NULL",
            name="chk_incident_assigned_team",
        ),
    )

    incident_code: Mapped[str] = mapped_column(String, unique=True, index=True)  # "RP-XXXX"
    hazard_type: Mapped[str] = mapped_column(String)  # "flood | earthquake | fire | medical | structural | other"
    severity: Mapped[str] = mapped_column(String)  # "critical | high | medium | low"

    centroid: Mapped[Optional[str]] = mapped_column(Geometry('POINT', srid=4326))
    cluster_polygon: Mapped[Optional[str]] = mapped_column(Geometry('POLYGON', srid=4326))

    total_reports: Mapped[int] = mapped_column(Integer, default=0)
    total_individuals: Mapped[int] = mapped_column(Integer, default=0)

    medical_risks: Mapped[Optional[dict]] = mapped_column(JSONB)
    ai_summary: Mapped[Optional[dict]] = mapped_column(JSONB)
    cluster_confidence: Mapped[Optional[float]] = mapped_column(Float)

    status: Mapped[str] = mapped_column(
        String, default=IncidentStatus.PENDING.value, index=True
    )  # "pending | verified | assigned | en_route | reached | resolved | rejected"

    assigned_team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("rescue_teams.id", ondelete="SET NULL"), nullable=True, index=True
    )

    first_report_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_report_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
