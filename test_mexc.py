import asyncio
import ccxt.async_support as ccxt
import pandas as pd
import pandas_ta as ta

async def test():
    mexc = ccxt.mexc()
    symbol = 'BTC/USDT'
    
    # Test 4H EMA50
    ohlcv_4h = await mexc.fetch_ohlcv(symbol, timeframe='4h', limit=100)
    df_4h = pd.DataFrame(ohlcv_4h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df_4h['ema50'] = ta.ema(df_4h['close'], length=50)
    print(f"4H EMA50 Test: Success. Last EMA50: {df_4h['ema50'].iloc[-1]}")
    
    # Test 15M ADX & ATR
    ohlcv = await mexc.fetch_ohlcv(symbol, timeframe='15m', limit=60)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    adx_data = ta.adx(df['high'], df['low'], df['close'], length=14)
    
    if adx_data is not None and 'ADX_14' in adx_data.columns:
        df['adx'] = adx_data['ADX_14']
    else:
        df['adx'] = 0
        
    print(f"15M ATR Test: Success. Last ATR: {df['atr'].iloc[-1]}")
    print(f"15M ADX Test: Success. Last ADX: {df['adx'].iloc[-1]}")
    
    await mexc.close()

if __name__ == '__main__':
    asyncio.run(test())
