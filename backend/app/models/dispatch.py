import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey, DateTime
from .base import BaseModel

class Dispatch(BaseModel):
    __tablename__ = "dispatches"
    
    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incidents.id"))
    coordinator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("coordinators.id"))
    rescue_team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rescue_teams.id"))
    
    priority: Mapped[str] = mapped_column(String) # "P0 | P1 | P2 | P3"
    coordinator_notes: Mapped[Optional[str]] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="dispatched") # "dispatched | en_route | on_site | completed | cancelled"
    
    dispatched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    eta: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
