import asyncio
import logging
import pandas as pd
import pandas_ta as ta
from datetime import datetime
from config import MIN_24H_VOLUME, VOLUME_SPIKE_X
from database import add_signal
from utils.indicators import calculate_dynamic_tp_sl, is_stablecoin

seen_signals = {}
logger = logging.getLogger(__name__)

async def analyze_symbol(symbol, mexc, tickers):
    """
    Koinni 15M (kirish) va 1H (trend tasdig'i) bo'yicha analiz qilish.
    """
    try:
        # 1H (Macro trend) analiz
        ohlcv_1h = await mexc.fetch_ohlcv(symbol, timeframe='1h', limit=50)
        if len(ohlcv_1h) < 25: return
        
        df_1h = pd.DataFrame(ohlcv_1h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_1h['ema50'] = ta.ema(df_1h['close'], length=50)
        
        if pd.isna(df_1h['ema50'].iloc[-2]): return
        macro_trend_up = df_1h['close'].iloc[-2] > df_1h['ema50'].iloc[-2]

        # 15M (Kirish) analiz
        ohlcv_15m = await mexc.fetch_ohlcv(symbol, timeframe='15m', limit=100)
        if len(ohlcv_15m) < 25: return
        
        df = pd.DataFrame(ohlcv_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['ema20'] = ta.ema(df['close'], length=20)
        df['ema50'] = ta.ema(df['close'], length=50)
        
        closed_candle = df.iloc[-2]
        prev_candles = df.iloc[-20:-2] # Oxirgi 18 ta sham tarixi
        
        current_close = closed_candle['close']
        current_volume = closed_candle['volume']
        current_rsi = closed_candle['rsi']
        ema20_val = closed_candle['ema20']
        ema50_val = closed_candle['ema50']
        timestamp = closed_candle['timestamp']
        
        # O'rtacha hajm va qarshiliklar
        avg_volume = prev_candles['volume'].mean()
        resistance_high = prev_candles['high'].max()
        support_low = prev_candles['low'].min()
        
        # 1. Hajm filtri (Kamida 2.5 marta o'sgan bo'lishi kerak)
        if current_volume < (avg_volume * VOLUME_SPIKE_X): return
        volume_spike = current_volume / avg_volume
        
        signal_key = f"{symbol}_{timestamp}"
        if signal_key in seen_signals: return
        
        signal_type = None
        tp, sl, atr = 0, 0, 0
        
        # LONG SHARTLARI
        if current_close > resistance_high and macro_trend_up and current_rsi < 75 and ema20_val > ema50_val:
            signal_type = "LONG"
            tp, sl, atr = calculate_dynamic_tp_sl(df, current_close, is_long=True)
            
        # SHORT SHARTLARI
        elif current_close < support_low and not macro_trend_up and current_rsi > 25 and ema20_val < ema50_val:
            signal_type = "SHORT"
            tp, sl, atr = calculate_dynamic_tp_sl(df, current_close, is_long=False)

        if signal_type:
            seen_signals[signal_key] = True
            
            # Formatted xabar
            msg = (
                f"{'🚀' if signal_type == 'LONG' else '🩸'} <b>{symbol}</b> | 15M Breakout ({signal_type})\n\n"
                f"💵 <b>Kirish narxi:</b> ${current_close:.5f}\n"
                f"🎯 <b>Take-Profit:</b> ${tp:.5f}\n"
                f"🛑 <b>Stop-Loss:</b> ${sl:.5f}\n\n"
                f"📉 <b>RSI kuchi:</b> {current_rsi:.1f}\n"
                f"📊 <b>Kirgan hajm:</b> {volume_spike:.1f}x o'sish\n"
                f"📏 <b>Bozor volatilligi (ATR):</b> ${atr:.5f}\n\n"
                f"⚡️ <i>Trend: 1H va 15M tasdiqlangan (Smart TP/SL)</i>"
            )
            
            logger.info(f"Yangi Snayper Signali: {symbol} - {signal_type}")
            return {
                "symbol": symbol,
                "type": signal_type,
                "entry": current_close,
                "tp": tp,
                "sl": sl,
                "message": msg
            }
            
    except Exception as e:
        # logger.error(f"Error in {symbol} sniper analysis: {e}")
        pass
    
    return None

async def sniper_scanner_loop(mexc, telegram_notifier_func):
    """
    MEXC birjasidagi tangalarni skanerlash va signal topsa Telegramga yuborish.
    """
    logger.info("🚀 SnayperBot (15M/1H) ishga tushdi! MEXC skanerlanmoqda...")
    markets_cache = None
    iteration = 0
    
    sem = asyncio.Semaphore(CONCURRENT_REQUESTS)
    
    while True:
        try:
            tickers = await mexc.fetch_tickers()
            if markets_cache is None or iteration % 60 == 0:
                markets_cache = await mexc.load_markets()
            iteration += 1
            
            valid_symbols = []
            for s, t in tickers.items():
                if not s.endswith('/USDT'): continue
                
                # Dinamik stablecoin filtr
                if is_stablecoin(s, tickers): continue
                
                if not markets_cache.get(s, {}).get('spot'): continue
                if t.get('quoteVolume', 0) < MIN_24H_VOLUME: continue
                
                valid_symbols.append(s)

            async def sem_task(sym):
                async with sem:
                    return await analyze_symbol(sym, mexc, tickers)

            tasks = [sem_task(sym) for sym in valid_symbols]
            results = await asyncio.gather(*tasks)
            
            for res in results:
                if res:
                    # Telegramga xabar yuborish
                    sent_messages = await telegram_notifier_func(res['message'], res['symbol'])
                    
                    # Ma'lumotlar bazasiga saqlash
                    await add_signal(
                        res['symbol'], res['type'], res['entry'], res['tp'], res['sl'], 
                        "PENDING", datetime.now().isoformat(), sent_messages
                    )

            await asyncio.sleep(60) # 1 minutda bir aylanadi
            
        except Exception as e:
            logger.error(f"Snayper kritik xatoligi: {e}")
            await asyncio.sleep(60)
