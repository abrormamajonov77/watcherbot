import asyncio
import motor.motor_asyncio
import certifi

async def test():
    client = motor.motor_asyncio.AsyncIOMotorClient('mongodb+srv://abrormamajonov77:40M979TA@cluster0.qh8kjbb.mongodb.net/?appName=Cluster0', tlsCAFile=certifi.where())
    try:
        info = await client.server_info()
        print("Muvaffaqiyatli ulandi!", info)
    except Exception as e:
        print("XATOLIK:", e)

asyncio.run(test())
