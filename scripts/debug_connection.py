import asyncio
import asyncpg
import sys

async def test():
    url = "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius"
    print(f"Testing connection to: {url}")
    try:
        conn = await asyncpg.connect(url)
        print("SUCCESS: Connected!")
        await conn.close()
    except Exception as e:
        print(f"FAILURE: {e}")
        with open("db_error.txt", "w") as f:
            f.write(str(e))

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test())
