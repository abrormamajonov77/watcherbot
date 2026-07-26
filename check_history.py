import asyncio
import ccxt.async_support as ccxt
import pandas as pd
import pandas_ta as ta

async def check(symbol):
    print(f"\n--- Checking {symbol} ---")
    try:
        b = ccxt.binance()
        ohlcv = await b.fetch_ohlcv(symbol, timeframe='15m', limit=100)
        await b.close()
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['ema20'] = ta.ema(df['close'], length=20)
        df['ema50'] = ta.ema(df['close'], length=50)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        # Look at candles around 10:00 AM (UTC+5 -> 05:00 UTC)
        # We will just print the last 5 candles to see what was happening recently
        target = df.tail(10)
        for _, row in target.iterrows():
            print(f"Time: {row['datetime']} | Close: {row['close']} | Vol: {row['volume']} | RSI: {row['rsi']:.2f} | EMA20: {row['ema20']:.5f} | EMA50: {row['ema50']:.5f} | ATR: {row['atr']:.5f}")
            
    except Exception as e:
        print(f"Error checking {symbol}: {e}")

async def main():
    await check('SHIB/USDT')
    await check('EUL/USDT')

asyncio.run(main())
