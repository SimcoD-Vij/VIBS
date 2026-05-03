import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import os

DATABASE_URL = "postgresql+asyncpg://debate_user:debate_pass@localhost:5432/debate_analyzer"

async def check_session(session_id):
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        result = await session.execute(text(f"SELECT status, progress_percent FROM sessions WHERE id = '{session_id}'"))
        row = result.fetchone()
        if row:
            print(f"Session {session_id}: Status={row[0]}, Progress={row[1]}%")
        else:
            print(f"Session {session_id} not found.")
    
    await engine.dispose()

if __name__ == "__main__":
    session_id = "1122c12a-14a9-44f9-91b6-b085d831a0ec"
    asyncio.run(check_session(session_id))
