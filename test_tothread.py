import asyncio
from google import genai
import sys
from functools import partial

API_KEY = "AIzaSyDb0_Xh-PlHDANyS02xqw5DLbukWEsbbFA"
client = genai.Client(api_key=API_KEY)

async def test_model():
    print(f"Testing sync client via asyncio.to_thread...")
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model='gemini-2.5-flash',
            contents="Say hi"
        )
        print(f"SUCCESS: -> {response.text}")
    except Exception as e:
        print(f"FAILED: -> {type(e).__name__}: {e}")

asyncio.run(test_model())
