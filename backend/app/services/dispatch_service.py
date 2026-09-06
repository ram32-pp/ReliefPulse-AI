from sqlalchemy.ext.asyncio import AsyncSession
from app.models.dispatch import Dispatch
from app.models.incident import Incident
from app.api.schemas import DispatchCreate
import uuid

class DispatchService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_dispatch(self, dispatch_data: DispatchCreate, coordinator_id: uuid.UUID) -> Dispatch:
        dispatch = Dispatch(
            incident_id=dispatch_data.incident_id,
            coordinator_id=coordinator_id,
            rescue_team_id=dispatch_data.rescue_team_id,
            priority=dispatch_data.priority,
            coordinator_notes=dispatch_data.coordinator_notes,
            status="dispatched"
        )
        self.session.add(dispatch)
        
        # Update incident status
        incident = await self.session.get(Incident, dispatch_data.incident_id)
        if incident:
            incident.status = "dispatched"
            
        await self.session.commit()
        await self.session.refresh(dispatch)
        return dispatch

from fastapi import Depends
from app.db.database import get_db

async def get_dispatch_service(session: AsyncSession = Depends(get_db)) -> DispatchService:
    return DispatchService(session)

