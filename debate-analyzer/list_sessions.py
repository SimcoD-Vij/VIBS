import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://debate_user:debate_pass@localhost:5432/debate_analyzer"

async def check():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession)
    async with async_session() as s:
        res = await s.execute(text('SELECT id, status, progress_percent FROM sessions ORDER BY created_at DESC LIMIT 5'))
        for row in res.fetchall():
            print(row)
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
