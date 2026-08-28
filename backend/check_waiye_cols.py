import asyncio
from database import engine
from sqlalchemy import text

async def check_cols():
    async with engine.begin() as conn:
        res = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'waiye_samples'
            ORDER BY ordinal_position
        """))
        for r in res.fetchall():
            print(f"{r[0]}: {r[1]}")

asyncio.run(check_cols())