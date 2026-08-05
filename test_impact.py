import asyncio
import ccxt.async_support as ccxt
import pandas as pd
import pandas_ta as ta

def calc_old_logic(df, i):
    # Old logic requires analyzing candle at index `i` based on history up to `i`
    # df has 1000 rows. We need at least 50 history.
    if i < 50: return None
    
    current = df.iloc[i]
    prev_candles = df.iloc[i-20:i-1] # previous 18 candles
    avg_volume = prev_candles['volume'].mean()
    
    resistance_high = prev_candles['close'].max()
    support_low = prev_candles['close'].min()
    
    current_volume = current['volume']
    candle_size = abs(current['close'] - current['open'])
    current_atr = current['atr']
    
    if current_volume < (avg_volume * 1.5): return None
    if candle_size < (current_atr * 0.6): return None
    
    is_long = (current['close'] > resistance_high) and (current['rsi'] > 55) and (current['ema20'] > current['ema50'])
    is_short = (current['close'] < support_low) and (current['rsi'] < 45) and (current['ema20'] < current['ema50'])
    
    ema_diff = abs(current['ema20'] - current['ema50']) / current['ema50']
    if ema_diff < 0.001: return None
    
    if is_long: return 'LONG'
    if is_short: return 'SHORT'
    return None

def calc_new_logic(df, i):
    if i < 50: return None
    
    current = df.iloc[i]
    prev_candles = df.iloc[i-20:i-1] # previous 18 candles
    avg_volume = prev_candles['volume'].mean()
    
    # NEW LOGIC: Use high/low instead of close for breakouts
    resistance_high = prev_candles['high'].max()
    support_low = prev_candles['low'].min()
    
    current_volume = current['volume']
    candle_size = abs(current['close'] - current['open'])
    current_atr = current['atr']
    
    # NEW LOGIC: stricter volume and candle size
    if current_volume < (avg_volume * 2.0): return None
    if candle_size < (current_atr * 1.0): return None
    
    is_long = (current['close'] > resistance_high) and (current['rsi'] > 55) and (current['ema20'] > current['ema50'])
    is_short = (current['close'] < support_low) and (current['rsi'] < 45) and (current['ema20'] < current['ema50'])
    
    ema_diff = abs(current['ema20'] - current['ema50']) / current['ema50']
    if ema_diff < 0.001: return None
    
    if is_long: return 'LONG'
    if is_short: return 'SHORT'
    return None

async def run_test():
    mexc = ccxt.mexc({'options': {'defaultType': 'spot'}})
    symbol = 'WIF/USDT'
    
    print(f"Fetching data for {symbol}...")
    # Fetch 1000 candles (15m)
    ohlcv = await mexc.fetch_ohlcv(symbol, timeframe='15m', limit=1000)
    await mexc.close()
    
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['ema20'] = ta.ema(df['close'], length=20)
    df['ema50'] = ta.ema(df['close'], length=50)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    old_signals = 0
    new_signals = 0
    
    for i in range(50, len(df)):
        if calc_old_logic(df, i): old_signals += 1
        if calc_new_logic(df, i): new_signals += 1
        
    print(f"--- NATIJALAR (Oxirgi 10 kunlik 15M shamlarida) ---")
    print(f"Koin: {symbol}")
    print(f"Eski Mantiq bo'yicha Signallar soni (shovqin): {old_signals}")
    print(f"Yangi Mantiq bo'yicha Signallar soni (tozalanngan): {new_signals}")

if __name__ == "__main__":
    asyncio.run(run_test())
