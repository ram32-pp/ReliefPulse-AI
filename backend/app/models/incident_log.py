import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from .base import BaseModel

class IncidentLog(BaseModel):
    """
    Immutable audit log for full legal and operational traceability of incident status transitions.
    """
    __tablename__ = "incident_logs"

    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), index=True)
    previous_status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    new_status: Mapped[str] = mapped_column(String, index=True)
    changed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    metadata_snapshot: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
