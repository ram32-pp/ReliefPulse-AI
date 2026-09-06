import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey, Float, Boolean, DateTime, Integer
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from geoalchemy2 import Geometry
from .base import BaseModel

class Report(BaseModel):
    __tablename__ = "reports"
    
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    raw_input: Mapped[Optional[str]] = mapped_column(String)
    parsed_text: Mapped[Optional[str]] = mapped_column(String) # Extracted/transcribed intelligible text from Gemini
    input_type: Mapped[str] = mapped_column(String, default="voice") # "voice | text | quick_button"
    audio_url: Mapped[Optional[str]] = mapped_column(String)
    voice_transcript: Mapped[Optional[str]] = mapped_column(String) # Verbatim transcription of voice note
    acoustic_distress_level: Mapped[Optional[str]] = mapped_column(String) # "critical | elevated | calm | inaudible"
    
    # Deprecated visual fields retained as nullable for backwards DB compatibility
    image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    ai_extraction: Mapped[Optional[dict]] = mapped_column(JSONB)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float)
    urgency_level: Mapped[Optional[str]] = mapped_column(String) # "critical | high | medium | low"
    
    # Deterministic Voice + Text + Location Verification Scores
    semantic_score: Mapped[int] = mapped_column(Integer, default=0) # 0 to 40 (Acoustic & Semantic Distress)
    consistency_score: Mapped[int] = mapped_column(Integer, default=0) # 0 to 20 (Cross-Modal Alignment)
    grounding_score: Mapped[int] = mapped_column(Integer, default=0) # 0 to 20 (Location Grounding)
    cluster_score: Mapped[int] = mapped_column(Integer, default=0) # 0 to 20 (Spatiotemporal Clustering)
    verification_score: Mapped[int] = mapped_column(Integer, default=0) # 0 to 100 deterministic
    vulnerability_level: Mapped[str] = mapped_column(String, default="requires_human_triage") # "critical | high | medium | low | requires_human_triage | false_or_prank"
    grounding_status: Mapped[str] = mapped_column(String, default="unreported_localized_incident") # "authoritative_match | unreported_localized_incident"
    cluster_id: Mapped[Optional[str]] = mapped_column(String)
    ai_verification_report: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Provenance and breakdown metadata
    media_source: Mapped[Optional[str]] = mapped_column(String, default="voice_direct")
    capture_nonce: Mapped[Optional[str]] = mapped_column(String)
    capture_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    grounding_label: Mapped[Optional[str]] = mapped_column(String) # Deprecated alias for grounding_status
    rubric_breakdown: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    flag_location_spoof: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    exif_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    gps_location: Mapped[Optional[str]] = mapped_column(Geometry('POINT', srid=4326))
    extracted_location_name: Mapped[Optional[str]] = mapped_column(String)
    gps_text_match_score: Mapped[Optional[float]] = mapped_column(Float)
    
    anomaly_flags: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String))
    status: Mapped[str] = mapped_column(String, default="pending_audit") # "pending_audit | pending | verified | clustered | dispatched | resolved | rejected"
    
    # End-to-end relief delivery progression
    relief_status: Mapped[str] = mapped_column(String, default="pending") # "pending | verified | dispatched | en_route | delivered | resolved"
    relief_eta_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    relief_team_name: Mapped[Optional[str]] = mapped_column(String)
    
    incident_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("incidents.id"))
    parent_report_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("reports.id", ondelete="SET NULL"), nullable=True, index=True)
    corroborated_count: Mapped[int] = mapped_column(Integer, default=1)
    
    is_offline_queued: Mapped[bool] = mapped_column(Boolean, default=False)
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

