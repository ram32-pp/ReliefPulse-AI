from fastapi import APIRouter, Form
from app.services.sms_service import sms_service
from app.services.report_service import get_report_service, ReportService
from app.db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from app.api.schemas import ReportCreate
import uuid

router = APIRouter(prefix="/sms", tags=["SMS"])

@router.post("/incoming")
async def incoming_sms(
    From: str = Form(...),
    Body: str = Form(...),
    session: AsyncSession = Depends(get_db)
):
    # Parse incoming SMS through AI
    report_service = ReportService(session)
    report_data = ReportCreate(
        input_type="text",
        text_input=Body
    )
    
    # Process the report
    report = await report_service.create_report(report_data)
    
    # Send status update SMS
    await sms_service.send_sms(From, f"ReliefPulse: Aapki report (ID: {str(report.id)[:8]}) mil gayi hai. Hum check kar rahe hain.")
    
    return {"status": "ok"}
