from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-initialize database tables if not already present
    try:
        from app.db.database import engine
        from app.models import Base
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            new_columns = [
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS audio_url VARCHAR",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS voice_transcript VARCHAR",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS acoustic_distress_level VARCHAR",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS semantic_score INTEGER DEFAULT 0",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS consistency_score INTEGER DEFAULT 0",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS grounding_score INTEGER DEFAULT 0",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS cluster_score INTEGER DEFAULT 0",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS verification_score INTEGER DEFAULT 0",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS vulnerability_level VARCHAR DEFAULT 'requires_human_triage'",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS grounding_status VARCHAR DEFAULT 'unreported_localized_incident'",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS cluster_id VARCHAR",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS ai_verification_report JSONB",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS relief_status VARCHAR DEFAULT 'pending'",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS relief_eta_minutes INTEGER",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS relief_team_name VARCHAR",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS media_source VARCHAR DEFAULT 'voice_direct'",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS capture_nonce VARCHAR",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS capture_timestamp TIMESTAMPTZ",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS phash VARCHAR",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS flag_location_spoof BOOLEAN DEFAULT FALSE",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS exif_metadata JSONB",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS grounding_label VARCHAR",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS rubric_breakdown JSONB",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS parsed_text VARCHAR",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS image_url VARCHAR",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS video_url VARCHAR",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS parent_report_id UUID REFERENCES reports(id) ON DELETE SET NULL",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS corroborated_count INTEGER DEFAULT 1",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS triage_tier VARCHAR DEFAULT 'suspected_unconfirmed'",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS cluster_density_factor FLOAT DEFAULT 0.0",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS device_integrity_score INTEGER DEFAULT 100",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS media_forensics_score INTEGER DEFAULT 100",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS semantic_consistency_score INTEGER DEFAULT 100",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS tamper_penalty INTEGER DEFAULT 0",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS callback_status VARCHAR",
                "ALTER TABLE reports ADD COLUMN IF NOT EXISTS verification_breakdown_5layer JSONB",
                "ALTER TABLE incidents ADD COLUMN IF NOT EXISTS assigned_team_id UUID",
                "ALTER TABLE incidents DROP CONSTRAINT IF EXISTS chk_incident_assigned_team",
                "ALTER TABLE incidents ADD CONSTRAINT chk_incident_assigned_team CHECK (status != 'assigned' OR assigned_team_id IS NOT NULL)",
            ]
            for col_stmt in new_columns:
                try:
                    await conn.execute(text(col_stmt))
                except Exception as col_err:
                    pass
        print("[ReliefPulse API] Database tables verified/initialized with updated columns.")
    except Exception as e:
        print(f"[ReliefPulse API] Note: Could not auto-initialize DB tables on startup ({e}).")
    yield

def create_app() -> FastAPI:
    app = FastAPI(
        title="ReliefPulse AI",
        description="A voice-first, AI-powered disaster management platform",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from pathlib import Path
    from fastapi.staticfiles import StaticFiles

    upload_dir = Path(settings.media_upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

    from app.api.routes import api_router, api_legacy_router
    from app.api.routes.websocket import socket_app

    app.include_router(api_router)
    app.include_router(api_legacy_router)
    app.mount("/ws", socket_app)

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return app

app = create_app()

