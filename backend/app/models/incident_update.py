import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from .base import BaseModel

class IncidentUpdate(BaseModel):
    __tablename__ = "incident_updates"
    
    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incidents.id"))
    update_type: Mapped[str] = mapped_column(String) # "report_added | status_change | team_update | escalation"
    payload: Mapped[dict] = mapped_column(JSONB)
