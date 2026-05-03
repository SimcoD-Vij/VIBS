import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://debate_user:debate_pass@localhost:5432/debate_analyzer"

async def check(session_id):
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession)
    async with async_session() as s:
        res = await s.execute(text(f"SELECT count(*) FROM segments WHERE session_id = '{session_id}'"))
        print(f"Segments: {res.scalar()}")
        
        res = await s.execute(text(f"SELECT count(*) FROM speakers WHERE session_id = '{session_id}'"))
        print(f"Speakers: {res.scalar()}")

        res = await s.execute(text(f"SELECT id, explanation, conclusion FROM graph_data WHERE session_id = '{session_id}'"))
        row = res.fetchone()
        if row:
            print(f"Graph Data found!")
            print(f"Explanation length: {len(row[1]) if row[1] else 0}")
            print(f"Conclusion length: {len(row[2]) if row[2] else 0}")
        else:
            print("Graph Data NOT found.")
    await engine.dispose()

if __name__ == "__main__":
    session_id = "1122c12a-14a9-44f9-91b6-b085d831a0ec"
    asyncio.run(check(session_id))
