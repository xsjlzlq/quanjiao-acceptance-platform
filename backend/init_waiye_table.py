import asyncio
from database import engine
from sqlalchemy import text

async def init_waiye_table():
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS waiye_samples (
                id SERIAL PRIMARY KEY,
                township_name VARCHAR(100),
                village_name VARCHAR(100),
                group_name VARCHAR(100),
                group_code VARCHAR(50),
                cbfmc VARCHAR(100),
                cbfbm VARCHAR(50),
                cbfbm_short VARCHAR(20),
                lxdh VARCHAR(50),
                dkmc VARCHAR(100),
                dkbm VARCHAR(50),
                dkbm_short VARCHAR(20),
                scmj NUMERIC,
                area_acknowledged VARCHAR(10) DEFAULT '',
                rights_correct VARCHAR(10) DEFAULT '',
                bound_correct VARCHAR(10) DEFAULT '',
                member_qualified VARCHAR(10) DEFAULT '',
                self_verified VARCHAR(10) DEFAULT '',
                self_signed VARCHAR(10) DEFAULT '',
                satisfaction VARCHAR(10) DEFAULT '满意',
                survey_method VARCHAR(20) DEFAULT '现场',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_waiye_group_code ON waiye_samples (group_code)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_waiye_township ON waiye_samples (township_name)"))
        print("waiye_samples table created successfully.")

asyncio.run(init_waiye_table())