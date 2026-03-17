import asyncio
import aiohttp
import json

async def explore_markets():
    async with aiohttp.ClientSession() as session:
        keywords = ["weather", "rain", "temperature", "hurricane", "snow", "flood"]
        for kw in keywords:
            url = f"https://gamma-api.polymarket.com/markets?active=true&closed=false&q={kw}&limit=20"
            async with session.get(url) as resp:
                data = await resp.json()
                print(f"--- Results for '{kw}' ---")
                for m in data:
                    print(f"Q: {m.get('question')}")
                    print(f"Desc: {m.get('description')[:100]}...")
                    print(f"Category: {m.get('category')}")
                    print(f"Tags: {m.get('tags')}")
                    print("-" * 20)

if __name__ == "__main__":
    asyncio.run(explore_markets())
