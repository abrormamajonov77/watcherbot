import asyncio
import ccxt.async_support as ccxt

async def test():
    try:
        print("Ulanish...")
        m = ccxt.mexc({'options': {'defaultType': 'spot'}})
        tickers = await m.fetch_tickers()
        print(f"Topildi {len(tickers)} ta ticker.")
    except Exception as e:
        print(f"Xato: {e}")
    finally:
        await m.close()

asyncio.run(test())
