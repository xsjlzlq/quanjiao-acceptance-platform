import asyncio
from database import engine
from sqlalchemy import text

async def check_cbdkxx():
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT cbfbm, dkbm, length(dkbm::text) FROM cbdkxx LIMIT 10"))
        for r in res.fetchall():
            print(f"cbfbm: {r[0]} | dkbm: {r[1]} ({r[2]} chars)")

asyncio.run(check_cbdkxx())