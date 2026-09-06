from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    fastapi_env: str = "development"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/reliefpulse"
    redis_url: str = "redis://localhost:6379/0"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    gemini_model_pro: str = "gemini-3.8-flash"
    gemini_max_output_tokens: int = 4096
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    firebase_credentials_json: str = ""
    
    # Alibaba Cloud OSS Storage
    alibaba_oss_access_key_id: str = ""
    alibaba_oss_access_key_secret: str = ""
    alibaba_oss_endpoint: str = ""
    alibaba_oss_bucket_name: str = ""
    alibaba_oss_region: str = ""
    
    # Media upload fallback (local filesystem)
    media_upload_dir: str = "uploads/media"
    
    clustering_radius_meters: float = 150.0
    clustering_time_window_hours: int = 12
    clustering_min_size: int = 2
    
    # Anti-spoofing & Provenance
    capture_nonce_secret: str = "reliefpulse-nonce-secret-change-me"
    
    # Asymmetric Grounding Engine
    openweathermap_api_key: str = ""
    
    # Verification Pipeline
    verification_timeout_seconds: int = 30
    phash_hamming_threshold: int = 5
    
    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgresql://"):
                v = "postgresql+asyncpg://" + v[len("postgresql://"):]
            elif v.startswith("postgres://"):
                v = "postgresql+asyncpg://" + v[len("postgres://"):]
        return v
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

