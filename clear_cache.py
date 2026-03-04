import asyncio
import asyncpg
import sys
import os

# Add the current directory to sys.path so we can import 'app'
sys.path.append(os.getcwd())

from app.config import settings

async def clear_cache():
    try:
        print(f"Connecting to database...")
        conn = await asyncpg.connect(dsn=settings.asyncpg_dsn)
        print(f"Clearing ai_recommendation_cache table...")
        res = await conn.execute("DELETE FROM ai_recommendation_cache")
        print(f"Done: {res}")
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(clear_cache())
