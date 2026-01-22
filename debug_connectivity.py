import httpx
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

async def check():
    url = f"https://api.telegram.org/bot{TOKEN}/getMe"
    print(f"Checking URL: {url.replace(TOKEN, 'HIDDEN_TOKEN')}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check())
