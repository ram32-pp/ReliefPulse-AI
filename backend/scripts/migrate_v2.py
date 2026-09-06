import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
from sqlalchemy import text
from app.db.database import engine

async def main():
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS parent_report_id UUID REFERENCES reports(id) ON DELETE SET NULL;"))
        await conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS corroborated_count INTEGER DEFAULT 1;"))
        print("DB MIGRATION SUCCESS: parent_report_id and corroborated_count added to reports table.")

if __name__ == "__main__":
    asyncio.run(main())
