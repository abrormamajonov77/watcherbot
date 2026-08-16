import asyncio
from google import genai
import sys

API_KEY = "AIzaSyDb0_Xh-PlHDANyS02xqw5DLbukWEsbbFA"
client = genai.Client(api_key=API_KEY)

async def test_model(model_name):
    print(f"Testing {model_name}...")
    try:
        response = await client.aio.models.generate_content(
            model=model_name,
            contents="Say hi"
        )
        print(f"SUCCESS: {model_name} -> {response.text}")
    except Exception as e:
        print(f"FAILED: {model_name} -> {type(e).__name__}: {e}")

async def main():
    await test_model('gemini-1.5-flash')
    await test_model('gemini-2.0-flash')
    await test_model('gemini-2.5-flash')

asyncio.run(main())
