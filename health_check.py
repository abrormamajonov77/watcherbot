import asyncio
import ccxt.async_support as ccxt
import feedparser
import motor.motor_asyncio
import certifi
from datetime import datetime

MONGO_URI = 'mongodb+srv://abrormamajonov77:40M979TA@cluster0.qh8kjbb.mongodb.net/?appName=Cluster0'

async def professional_health_check():
    print("=========================================")
    print("🚀 BOTS PROFESSIONAL HEALTH CHECK 🚀")
    print("=========================================\n")

    # 1. MongoDB M0 Cluster Test
    print("[1] Ma'lumotlar bazasini (MongoDB) tekshirish...")
    try:
        mongo_client = motor.motor_asyncio.AsyncIOMotorClient(
            MONGO_URI, 
            tlsCAFile=certifi.where(), 
            tlsAllowInvalidCertificates=True,
            serverSelectionTimeoutMS=5000
        )
        db = mongo_client['sniper_bot_db']
        users_count = await db['users'].count_documents({})
        signals_count = await db['signals'].count_documents({})
        memory_count = await db['memory'].count_documents({})
        print("✅ MongoDB: Ulanish mukammal!")
        print(f"   👥 Jami foydalanuvchilar (Obunachilar): {users_count} ta")
        print(f"   📈 Jami yuborilgan signallar: {signals_count} ta")
        print(f"   🧠 Xotiradagi ma'lumotlar: {memory_count} ta\n")
    except Exception as e:
        print(f"❌ MongoDB: XATOLIK! {str(e)}\n")

    # 2. MEXC Exchange Test (Snayper Bot)
    print("[2] Birja (MEXC API) ulanishini tekshirish...")
    try:
        exchange = ccxt.mexc()
        tickers = await exchange.fetch_tickers()
        print(f"✅ MEXC API: Ulanish a'lo darajada! {len(tickers)} ta tanga (kriptovalyuta) nazorat qilinmoqda.\n")
        await exchange.close()
    except Exception as e:
        print(f"❌ MEXC API: XATOLIK! {str(e)}\n")
        if 'exchange' in locals():
            await exchange.close()

    # 3. News RSS Test (Watcher Bot)
    print("[3] Yangiliklar markazini (RSS) tekshirish...")
    try:
        feed = feedparser.parse('https://cointelegraph.com/rss')
        if feed.entries:
            print(f"✅ Yangiliklar markazi: Ulanish joyida! {len(feed.entries)} ta so'nggi xalqaro xabarlar tayyor.\n")
        else:
            print("⚠️ Yangiliklar markazi: Ulandi, lekin ma'lumot topilmadi.\n")
    except Exception as e:
        print(f"❌ Yangiliklar markazi: XATOLIK! {str(e)}\n")

    print("=========================================")
    print("🏁 TEKSHIRUV YAKUNLANDI 🏁")
    print("=========================================")

if __name__ == "__main__":
    asyncio.run(professional_health_check())
