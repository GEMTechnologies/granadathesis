import asyncio
import os
import asyncpg
import redis.asyncio as redis
from datetime import datetime

async def check_postgres():
    print(f"[{datetime.now()}] 🐘 Checking PostgreSQL...")
    dsn = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/thesis")
    print(f"   URL: {dsn}")
    try:
        conn = await asyncpg.connect(dsn, timeout=5)
        version = await conn.fetchval("SELECT version()")
        print(f"   ✅ Connected! Version: {version}")
        await conn.close()
        return True
    except Exception as e:
        print(f"   ❌ PostgreSQL Failed: {e}")
        return False

async def check_redis():
    print(f"[{datetime.now()}] 🔴 Checking Redis...")
    url = os.getenv("REDIS_URL", "redis://localhost:6379")
    print(f"   URL: {url}")
    try:
        r = redis.from_url(url, socket_connect_timeout=3)
        await r.ping()
        print(f"   ✅ Connected to Redis!")
        await r.close()
        return True
    except Exception as e:
        print(f"   ❌ Redis Failed: {e}")
        return False

async def main():
    print("=== CONNECTION DIAGNOSTICS ===")
    pg = await check_postgres()
    rd = await check_redis()
    
    if pg and rd:
        print("\n🎉 ALL SYSTEMS GO!")
    else:
        print("\n⚠️ SYSTEM ISSUES DETECTED")

if __name__ == "__main__":
    asyncio.run(main())
