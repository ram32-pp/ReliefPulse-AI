from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from geoalchemy2 import Geometry
from .base import BaseModel

class User(BaseModel):
    __tablename__ = "users"
    
    phone_number: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)
    firebase_uid: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)
    last_known_location: Mapped[Optional[str]] = mapped_column(Geometry('POINT', srid=4326))
