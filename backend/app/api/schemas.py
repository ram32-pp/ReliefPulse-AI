from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
import uuid
from datetime import datetime

class GPSLocation(BaseModel):
    latitude: float
    longitude: float
    accuracy_meters: Optional[float] = None

class DeviceInfo(BaseModel):
    platform: Optional[str] = None
    connection_type: Optional[str] = None
    is_offline_sync: bool = False

class ReportCreate(BaseModel):
    input_type: str = Field(default="voice", description="'voice' | 'text' | 'quick_button'")
    text_input: Optional[str] = None
    text_note: Optional[str] = None  # Direct text field
    audio_blob_url: Optional[str] = None
    quick_buttons: Optional[List[str]] = []
    hazard_types: Optional[List[str]] = []
    hazards: Optional[List[str]] = []  # Direct hazard badge list
    address_text: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gps_location: Optional[GPSLocation] = None
    device_info: Optional[DeviceInfo] = None
    media_source: Optional[str] = "voice_direct"
    capture_nonce: Optional[str] = None
    capture_timestamp: Optional[Any] = None

class ReportResponse(BaseModel):
    report_id: str
    display_code: str
    status: str
    message_ur: str
    message_en: str
    estimated_review_seconds: int
    track_url: str
    parsed_text: Optional[str] = None
    raw_input: Optional[str] = None
    voice_transcript: Optional[str] = None
    acoustic_distress_level: Optional[str] = None
    ai_extraction: Optional[Dict[str, Any]] = None
    semantic_score: Optional[int] = None
    consistency_score: Optional[int] = None
    grounding_score: Optional[int] = None
    cluster_score: Optional[int] = None
    verification_score: Optional[int] = None
    vulnerability_level: Optional[str] = None
    grounding_status: Optional[str] = None
    cluster_id: Optional[str] = None
    concise_report: Optional[str] = None
    audio_url: Optional[str] = None
    grounding_label: Optional[str] = None
    rubric_breakdown: Optional[Dict[str, Any]] = None
    provenance_flags: Optional[List[str]] = None
    triage_tier: Optional[str] = "suspected_unconfirmed"
    cluster_density_factor: Optional[float] = 0.0
    device_integrity_score: Optional[int] = 100
    media_forensics_score: Optional[int] = 100
    semantic_consistency_score: Optional[int] = 100
    tamper_penalty: Optional[int] = 0
    callback_status: Optional[str] = None
    verification_breakdown_5layer: Optional[Dict[str, Any]] = None

class TimelineStep(BaseModel):
    step: str
    label_ur: str
    label_en: str
    completed: bool
    at: Optional[datetime] = None

class ReportStatus(BaseModel):
    report_id: str
    display_code: str
    status: str
    timeline: List[TimelineStep]
    incident_id: Optional[str] = None
    rescue_eta_minutes: Optional[int] = None
    helpline_number: str
    parsed_text: Optional[str] = None
    raw_input: Optional[str] = None
    voice_transcript: Optional[str] = None
    acoustic_distress_level: Optional[str] = None
    ai_extraction: Optional[Dict[str, Any]] = None
    semantic_score: Optional[int] = None
    consistency_score: Optional[int] = None
    grounding_score: Optional[int] = None
    cluster_score: Optional[int] = None
    verification_score: Optional[int] = None
    vulnerability_level: Optional[str] = None
    grounding_status: Optional[str] = None
    cluster_id: Optional[str] = None
    concise_report: Optional[str] = None
    ai_verification_report: Optional[Dict[str, Any]] = None
    relief_status: Optional[str] = "pending"
    relief_team_name: Optional[str] = None
    audio_url: Optional[str] = None
    location_name: Optional[str] = None
    gps_coords: Optional[Dict[str, float]] = None
    media_source: Optional[str] = None
    grounding_label: Optional[str] = None
    rubric_breakdown: Optional[Dict[str, Any]] = None
    provenance_flags: Optional[List[str]] = None
    triage_tier: Optional[str] = "suspected_unconfirmed"
    cluster_density_factor: Optional[float] = 0.0
    device_integrity_score: Optional[int] = 100
    media_forensics_score: Optional[int] = 100
    semantic_consistency_score: Optional[int] = 100
    tamper_penalty: Optional[int] = 0
    callback_status: Optional[str] = None
    verification_breakdown_5layer: Optional[Dict[str, Any]] = None

# Coordinator Schemas
class IncidentDetail(BaseModel):
    incident_id: str
    incident_code: str
    severity: str
    hazard_type: str
    location: Dict[str, Any]
    total_reports: int = 1
    total_individuals: int = 1
    medical_risks: List[Any] = Field(default_factory=list)
    cluster_confidence: float = 0.85
    ai_summary: Optional[str] = None
    ai_reasoning: List[str] = Field(default_factory=list)
    anomaly_flags: List[Any] = Field(default_factory=list)
    representative_audio_url: Optional[str] = None
    first_report_at: datetime
    last_report_at: datetime
    gps_text_match: Dict[str, Any] = Field(default_factory=dict)
    caller_transcript: Optional[str] = None
    caller_statement: Optional[str] = None
    english_translation: Optional[str] = None
    urdu_translation: Optional[str] = None
    relief_status: Optional[str] = "pending"
    relief_team_name: Optional[str] = None
    relief_eta_minutes: Optional[int] = None
    report_id: Optional[str] = None
    input_type: Optional[str] = "voice"
    phone_number: Optional[str] = None
    # 5-Layer Extensions
    triage_tier: Optional[str] = "suspected_unconfirmed"
    cluster_density_factor: Optional[float] = 0.0
    device_integrity_score: Optional[int] = 100
    verification_score: Optional[int] = 0
    tamper_penalty: Optional[int] = 0
    callback_status: Optional[str] = None
    verification_breakdown_5layer: Optional[Dict[str, Any]] = None

class CallbackRequest(BaseModel):
    report_id: Optional[str] = None
    incident_id: Optional[str] = None
    phone_number: Optional[str] = None
    custom_message: Optional[str] = None

class CallbackResponse(BaseModel):
    status: str
    report_id: str
    phone_number: Optional[str] = None
    callback_status: str
    message: str

class TriageQueueResponse(BaseModel):
    total: int
    page: int
    incidents: List[IncidentDetail]

class DispatchCreate(BaseModel):
    incident_id: Union[str, uuid.UUID]
    action: str = "dispatch"
    rescue_team_id: Optional[Union[str, uuid.UUID]] = None
    priority: str = "P0"
    coordinator_notes: Optional[str] = None
    special_equipment: Optional[List[str]] = None

class DispatchResponse(BaseModel):
    dispatch_id: str
    incident_code: str
    status: str
    rescue_team: str
    estimated_arrival_minutes: int
    notifications_sent: Dict[str, Any]

class RejectRequest(BaseModel):
    incident_id: Union[str, uuid.UUID]
    action: str = "reject"
    reason: str
    notes: Optional[str] = None

class AdvanceReliefRequest(BaseModel):
    report_id: Optional[str] = None
    incident_id: Optional[str] = None
    relief_status: str # "dispatched" | "en_route" | "delivered" | "resolved"
    relief_team_name: Optional[str] = "Rescue 1122 Rapid Unit"
    rescue_eta_minutes: Optional[int] = 15
    coordinator_notes: Optional[str] = None


class CaptureNonceResponse(BaseModel):
    nonce: str
    expires_at: str
    ttl_seconds: int
