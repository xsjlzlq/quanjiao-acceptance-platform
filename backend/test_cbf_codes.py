import asyncio
from database import engine
from sqlalchemy import text

async def check_cbf():
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT cbfbm, cbfmc, length(cbfbm::text) FROM cbf LIMIT 20"))
        for r in res.fetchall():
            print(f"cbfbm: {r[0]} ({r[2]} chars) | cbfmc: {r[1]}")

asyncio.run(check_cbf())