from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer
from sqlalchemy.dialects.postgresql import ARRAY
from geoalchemy2 import Geometry
from .base import BaseModel

class RescueTeam(BaseModel):
    __tablename__ = "rescue_teams"
    
    team_name: Mapped[str] = mapped_column(String)
    team_type: Mapped[str] = mapped_column(String) # "medical | rescue | supply | mixed"
    current_location: Mapped[Optional[str]] = mapped_column(Geometry('POINT', srid=4326))
    status: Mapped[str] = mapped_column(String, default="available") # "available | en_route | on_site | off_duty"
    capacity: Mapped[int] = mapped_column(Integer, default=0)
    capabilities: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String))
