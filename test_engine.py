import asyncio
import os
from datetime import datetime
from database import init_db, add_signal, update_signal_status, get_weekly_signals_stats, get_daily_coin_stats

async def test_db():
    print("--- 1. Baza inisializatsiya qilinmoqda ---")
    await init_db()
    
    print("--- 2. Mock signallar qo'shilmoqda ---")
    now_iso = datetime.now().isoformat()
    # 5-star signals
    await add_signal("BTC/USDT", "LONG", 60000, 62000, 59000, "WIN", now_iso, "{}", stars=5)
    await add_signal("BTC/USDT", "LONG", 61000, 63000, 60000, "WIN", now_iso, "{}", stars=5)
    await add_signal("ETH/USDT", "SHORT", 3000, 2800, 3100, "LOSS", now_iso, "{}", stars=5)
    
    # 3-star signals
    await add_signal("SOL/USDT", "LONG", 150, 160, 140, "WIN", now_iso, "{}", stars=3)
    await add_signal("SOL/USDT", "LONG", 155, 165, 145, "LOSS", now_iso, "{}", stars=3)
    await add_signal("ADA/USDT", "SHORT", 0.5, 0.45, 0.55, "BREAK_EVEN", now_iso, "{}", stars=3)
    
    print("--- 3. Baza o'qilmoqda ---")
    old_iso = "2020-01-01T00:00:00"
    
    print("Weekly Stats:")
    weekly = await get_weekly_signals_stats(old_iso)
    for row in weekly:
        print(row)
        
    print("\nDaily Coin Stats:")
    daily = await get_daily_coin_stats(old_iso)
    for row in daily:
        print(row)

if __name__ == "__main__":
    asyncio.run(test_db())
