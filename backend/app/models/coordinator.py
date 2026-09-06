from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from .base import BaseModel

class Coordinator(BaseModel):
    __tablename__ = "coordinators"
    
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    role: Mapped[str] = mapped_column(String, default="coordinator") # "coordinator | admin | super_admin"
    organization: Mapped[str] = mapped_column(String)
