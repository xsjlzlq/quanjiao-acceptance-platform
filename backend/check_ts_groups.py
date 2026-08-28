import asyncio
from database import engine
from sqlalchemy import text

async def check_groups():
    async with engine.begin() as conn:
        res = await conn.execute(text("""
            SELECT substring(qsdwdm::text, 1, 9) as ts, count(*) 
            FROM qsdwdmb 
            WHERE qsdwdm::text NOT LIKE '%00' 
            GROUP BY substring(qsdwdm::text, 1, 9)
            ORDER BY ts
        """))
        for r in res.fetchall():
            print(f"Township code {r[0]}: {r[1]} groups")

asyncio.run(check_groups())