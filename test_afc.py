import asyncio
from google import genai
from google.genai import types
import sys

API_KEY = "AIzaSyDb0_Xh-PlHDANyS02xqw5DLbukWEsbbFA"
client = genai.Client(api_key=API_KEY)

async def test_model():
    print(f"Testing async gemini-2.5-flash with AFC disabled...")
    try:
        config = types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
        )
        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents="Say hi",
            config=config
        )
        print(f"SUCCESS: -> {response.text}")
    except Exception as e:
        print(f"FAILED: -> {type(e).__name__}: {e}")

asyncio.run(test_model())
