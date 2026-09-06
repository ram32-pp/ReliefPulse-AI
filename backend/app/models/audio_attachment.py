import uuid
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, ForeignKey
from .base import BaseModel

class AudioAttachment(BaseModel):
    __tablename__ = "audio_attachments"
    
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reports.id"))
    storage_url: Mapped[str] = mapped_column(String)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    mime_type: Mapped[Optional[str]] = mapped_column(String)
    transcription: Mapped[Optional[str]] = mapped_column(String)
