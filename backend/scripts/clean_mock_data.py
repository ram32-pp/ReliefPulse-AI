import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.database import async_session_maker
from sqlalchemy import text

async def clean_database():
    async with async_session_maker() as session:
        print("Cleaning mock and test reports/incidents...")
        # Break foreign key references first
        await session.execute(text("UPDATE reports SET parent_report_id = NULL, incident_id = NULL;"))
        await session.execute(text("DELETE FROM dispatches;"))
        res_rep = await session.execute(text("DELETE FROM reports;"))
        res_inc = await session.execute(text("DELETE FROM incidents;"))
        await session.commit()
        print(f"Cleaned database successfully! Reports deleted: {res_rep.rowcount}, Incidents deleted: {res_inc.rowcount}")

if __name__ == "__main__":
    asyncio.run(clean_database())
