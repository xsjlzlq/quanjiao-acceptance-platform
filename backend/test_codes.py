import asyncio
from database import engine
from sqlalchemy import text

async def check_codes():
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT qsdwdm, qsdwmc, length(qsdwdm::text) FROM qsdwdmb LIMIT 25"))
        for r in res.fetchall():
            print(f"qsdwdm: {r[0]} ({r[2]} chars) | {r[1]}")

asyncio.run(check_codes())