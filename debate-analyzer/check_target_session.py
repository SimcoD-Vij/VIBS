import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://debate_user:debate_pass@localhost:5432/debate_analyzer"

async def check_session(session_id):
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession)
    async with async_session() as session:
        result = await session.execute(text(f"SELECT status, progress_percent, wav_path FROM sessions WHERE id = '{session_id}'"))
        row = result.fetchone()
        if row:
            print(f"Session {session_id}: Status={row[0]}, Progress={row[1]}%, Path={row[2]}")
        else:
            print(f"Session {session_id} not found.")
    await engine.dispose()

if __name__ == "__main__":
    session_id = "27a663b8-9a44-44ab-8f5c-2ed405da3f27"
    asyncio.run(check_session(session_id))
