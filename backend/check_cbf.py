import asyncio
from database import engine
from sqlalchemy import text

async def check_cbf():
    async with engine.begin() as conn:
        res = await conn.execute(text("""
            SELECT substring(cbfbm::text, 1, 9) as ts, count(*) 
            FROM cbf
            GROUP BY substring(cbfbm::text, 1, 9)
            ORDER BY ts
        """))
        for r in res.fetchall():
            print(f"Township code in CBF {r[0]}: {r[1]} contractors")

asyncio.run(check_cbf())