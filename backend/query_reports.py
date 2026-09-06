import asyncio
from sqlalchemy import text
from app.db.database import engine

async def check():
    async with engine.connect() as conn:
        res = await conn.execute(text("""
            SELECT id, raw_input, parsed_text, voice_transcript, input_type,
                   extracted_location_name, urgency_level, relief_status, 
                   relief_team_name, relief_eta_minutes, created_at,
                   ST_AsText(gps_location) as coords,
                   ai_extraction
            FROM reports
            ORDER BY created_at DESC
            LIMIT 15;
        """))
        rows = res.fetchall()
        print(f"Latest {len(rows)} reports in database:")
        for r in rows:
            code = f"RP-{str(r[0])[:4].upper()}"
            print("--------------------------------------------------")
            print(f"Code: {code} | ID: {r[0]}")
            print(f"Raw Input: {r[1]}")
            print(f"Parsed Text: {r[2]}")
            print(f"Voice Transcript: {r[3]}")
            print(f"Extracted Location: {r[5]}")
            print(f"Coords: {r[11]}")
            print(f"Urgency: {r[6]} | Relief Status: {r[7]} | Created: {r[10]}")
            ai_ext = r[12] or {}
            print(f"AI Hazard: {ai_ext.get('hazard_type')} | Headcount: {ai_ext.get('people', {}).get('headcount')} | Summary: {ai_ext.get('situation_summary')}")

if __name__ == "__main__":
    asyncio.run(check())
