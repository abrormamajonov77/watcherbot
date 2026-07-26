import asyncio
import ccxt.async_support as ccxt
import pandas as pd
import pandas_ta as ta

async def debug_symbol(symbol, mexc):
    try:
        ohlcv_15m = await mexc.fetch_ohlcv(symbol, timeframe='15m', limit=100)
        if len(ohlcv_15m) < 25: return "Not enough 15m candles"

        df = pd.DataFrame(ohlcv_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['ema20'] = ta.ema(df['close'], length=20)
        df['ema50'] = ta.ema(df['close'], length=50)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)

        closed_candle = df.iloc[-2]
        prev_candles  = df.iloc[-20:-2]

        current_close  = closed_candle['close']
        current_volume = closed_candle['volume']
        current_rsi    = closed_candle['rsi']
        ema20_val      = closed_candle['ema20']
        ema50_val      = closed_candle['ema50']
        current_atr    = closed_candle['atr']
        
        if pd.isna(current_atr) or current_atr == 0: return "ATR is NaN/0"

        avg_volume     = prev_candles['volume'].mean()
        resistance_high = prev_candles['high'].max()
        support_low    = prev_candles['low'].min()
        candle_size = abs(closed_candle['close'] - closed_candle['open'])

        if current_volume < (avg_volume * 1.5): return f"Volume too low ({current_volume:.2f} < {avg_volume*1.5:.2f})"
        if candle_size < (current_atr * 0.8): return f"Candle body too small ({candle_size:.5f} < {current_atr*0.8:.5f})"

        is_long_breakout = current_close > resistance_high and current_rsi > 55 and ema20_val > ema50_val
        is_short_breakdown = current_close < support_low and current_rsi < 45 and ema20_val < ema50_val
        
        ema_diff_percent = abs(ema20_val - ema50_val) / ema50_val
        if ema_diff_percent < 0.001: return "Chop Zone (EMAs too close)"

        if not (is_long_breakout or is_short_breakdown):
            if current_close > resistance_high:
                if current_rsi <= 55: return f"Breakout but RSI too low ({current_rsi:.2f})"
                if ema20_val <= ema50_val: return "Breakout but EMA20 <= EMA50 (Lagging)"
            return "No Breakout/Breakdown"
            
        return "PASSED 15M!"

    except Exception as e:
        return f"Error: {str(e)}"

async def main():
    print("Connecting to MEXC...")
    mexc = ccxt.mexc({'enableRateLimit': True, 'options': {'defaultType': 'spot'}})
    try:
        tickers = await mexc.fetch_tickers()
        valid = [s for s, t in tickers.items() if s.endswith('/USDT') and t.get('quoteVolume', 0) > 1000000]
        valid = valid[:100] # test top 100
        
        reasons = {}
        print(f"Testing {len(valid)} symbols...")
        for sym in valid:
            res = await debug_symbol(sym, mexc)
            reasons[res] = reasons.get(res, 0) + 1
            if res.startswith("PASSED") or "Breakout but" in res:
                print(f"{sym}: {res}")
                
        print("\n--- SUMMARY OF REJECTIONS ---")
        for reason, count in sorted(reasons.items(), key=lambda x: x[1], reverse=True):
            print(f"{count} coins: {reason}")
            
    finally:
        await mexc.close()

asyncio.run(main())
