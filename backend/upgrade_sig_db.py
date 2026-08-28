import asyncio
from database import engine
from sqlalchemy import text

async def upgrade_db():
    async with engine.begin() as conn:
        await conn.execute(text("""
            DO $$ 
            BEGIN 
                BEGIN 
                    ALTER TABLE waiye_samples ADD COLUMN signature_url VARCHAR(255) DEFAULT ''; 
                EXCEPTION 
                    WHEN duplicate_column THEN NULL; 
                END; 
            END $$;
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS contractor_signatures (
                cbfbm VARCHAR(50) PRIMARY KEY,
                cbfmc VARCHAR(100),
                signature_path VARCHAR(255),
                signature_data TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        print("Database schema upgraded with signature columns successfully.")

asyncio.run(upgrade_db())