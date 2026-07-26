import asyncio
import ccxt.async_support as ccxt
import logging
from services.sniper_engine import analyze_symbol
from database import init_db

logging.basicConfig(level=logging.INFO)

async def test_bot():
    print("--- 1. Baza inisializatsiya qilinmoqda ---")
    await init_db()
    
    print("--- 2. MEXC ga ulanish ---")
    mexc = ccxt.mexc({
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })
    
    try:
        print("--- 3. Tickers olinmoqda ---")
        tickers = await mexc.fetch_tickers()
        
        test_coins = ['BTC/USDT', 'SOL/USDT', 'ETH/USDT', 'DOGE/USDT', 'XRP/USDT']
        
        print("--- 4. Skanerlash boshlandi ---")
        for coin in test_coins:
            print(f"Tekshirilmoqda: {coin}")
            result = await analyze_symbol(coin, mexc, tickers)
            if result:
                print(f"!!! SIGNAL TOPILDI: {result['symbol']} - {result['type']} !!!")
                print(result['message'])
            else:
                print(f"{coin} uchun shartlar bajarilmadi (Signal yo'q).")
                
    except Exception as e:
        print(f"Kritik Xato: {e}")
    finally:
        await mexc.close()

if __name__ == "__main__":
    asyncio.run(test_bot())
