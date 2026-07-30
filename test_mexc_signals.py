import asyncio
import ccxt.async_support as ccxt
import pandas as pd
import pandas_ta as ta

async def test_mexc():
    mexc = ccxt.mexc({'enableRateLimit': True, 'options': {'defaultType': 'spot'}})
    async def mock_fetch_swap_markets(*args, **kwargs): return []
    mexc.fetch_swap_markets = mock_fetch_swap_markets
    
    try:
        markets = await mexc.load_markets()
        tickers = await mexc.fetch_tickers()
        print(f"Loaded {len(markets)} markets, {len(tickers)} tickers")
        
        valid = []
        for s, t in tickers.items():
            if not s.endswith('/USDT'): continue
            if 'USDC' in s or 'TUSD' in s or 'FDUSD' in s: continue
            if not markets.get(s, {}).get('spot'): continue
            if t.get('quoteVolume', 0) < 300000: continue
            valid.append(s)
            
        print(f"Found {len(valid)} valid coins")
        
        reasons = {}
        for sym in valid[:50]:
            try:
                ohlcv = await mexc.fetch_ohlcv(sym, timeframe='15m', limit=100)
                if len(ohlcv) < 25: 
                    reasons['not_enough_data'] = reasons.get('not_enough_data', 0) + 1
                    continue
                
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['rsi'] = ta.rsi(df['close'], length=14)
                df['ema20'] = ta.ema(df['close'], length=20)
                df['ema50'] = ta.ema(df['close'], length=50)
                df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
                
                closed = df.iloc[-2]
                prev = df.iloc[-20:-2]
                
                if pd.isna(closed['atr']) or closed['atr'] == 0:
                    reasons['bad_atr'] = reasons.get('bad_atr', 0) + 1
                    continue
                    
                avg_vol = prev['volume'].mean()
                if closed['volume'] < (avg_vol * 1.5):
                    reasons['volume_too_low'] = reasons.get('volume_too_low', 0) + 1
                    continue
                    
                candle_size = abs(closed['close'] - closed['open'])
                if candle_size < (closed['atr'] * 0.8):
                    reasons['candle_too_small'] = reasons.get('candle_too_small', 0) + 1
                    continue
                    
                res_high = prev['high'].max()
                sup_low = prev['low'].min()
                
                is_long = closed['close'] > res_high and closed['rsi'] > 55 and closed['ema20'] > closed['ema50']
                is_short = closed['close'] < sup_low and closed['rsi'] < 45 and closed['ema20'] < closed['ema50']
                
                if not (is_long or is_short):
                    reasons['no_breakout'] = reasons.get('no_breakout', 0) + 1
                    continue
                    
                print(f"SIGNAL FOUND ON {sym}!")
                
            except Exception as e:
                print(f"Error on {sym}: {e}")
                
        print("Rejection reasons:", reasons)
        
    finally:
        await mexc.close()

if __name__ == "__main__":
    asyncio.run(test_mexc())
