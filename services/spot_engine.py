import asyncio
import logging
import pandas as pd
import pandas_ta as ta
from datetime import datetime
from config import MIN_24H_VOLUME, CONCURRENT_REQUESTS
from database import add_signal
from utils.indicators import calculate_dynamic_tp_sl, is_stablecoin

seen_signals = {}
logger = logging.getLogger(__name__)

async def analyze_spot_symbol(symbol, mexc, tickers):
    """
    Spot uchun uzoq muddatli 1D (Kunlik) tahlil.
    """
    try:
        ohlcv_1d = await mexc.fetch_ohlcv(symbol, timeframe='1d', limit=250)
        if len(ohlcv_1d) < 200: return # 200 kunlik tarix bo'lmasa rad etish
        
        df = pd.DataFrame(ohlcv_1d, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Oltin Kesisishma (Golden Cross) yoki uzoq muddatli trend uchun EMA lar
        df['ema50'] = ta.ema(df['close'], length=50)
        df['ema200'] = ta.ema(df['close'], length=200)
        df['rsi'] = ta.rsi(df['close'], length=14)
        
        if pd.isna(df['ema200'].iloc[-2]): return
        
        closed_candle = df.iloc[-2]
        current_close = closed_candle['close']
        current_rsi = closed_candle['rsi']
        ema50 = closed_candle['ema50']
        ema200 = closed_candle['ema200']
        timestamp = closed_candle['timestamp']
        
        signal_key = f"SPOT_{symbol}_{timestamp}"
        if signal_key in seen_signals: return
        
        # Spot LONG shartlari: Narx 200 Kunlik MA dan balandda (Yoki yaqinda kesib o'tgan), RSI normal
        # EMA50 > EMA200 (Golden Cross tasdig'i)
        if current_close > ema200 and ema50 > ema200 and 40 < current_rsi < 65:
            # Qo'shimcha hajm (volume) tekshiruvi: oxirgi kun hajmi o'rtachadan baland bo'lsa
            avg_vol = df['volume'].tail(15).mean()
            if closed_candle['volume'] > (avg_vol * 1.5):
                
                tp, sl, atr = calculate_dynamic_tp_sl(df, current_close, is_long=True)
                # Spot uchun ATR ni 2 marta kattalashtiramiz, chunki tebranish kattaroq
                sl = current_close - (atr * 2)
                tp = current_close + (atr * 4) # Risk 1:2
                
                seen_signals[signal_key] = True
                
                msg = (
                    f"💎 <b>{symbol}</b> | SPOT Signali (1D Chart)\n"
                    f"Ishonchlilik: ⭐⭐⭐⭐⭐ <i>(Uzoq muddatli)</i>\n\n"
                    f"💵 <b>Kirish narxi:</b> ${current_close:.5f}\n"
                    f"🎯 <b>Uzoq muddatli TP:</b> ${tp:.5f}\n"
                    f"🛑 <b>Stop-Loss:</b> ${sl:.5f}\n\n"
                    f"📈 <b>Sabab:</b> Narx 200 kunlik EMA dan yuqorida, hajm o'sishi kuzatildi.\n"
                    f"⚠️ <i>Spot signallar oylab kutilishi mumkin!</i>"
                )
                
                logger.info(f"Yangi Spot Signali: {symbol}")
                return {
                    "symbol": symbol,
                    "type": "LONG", # Spot faqat long bo'ladi
                    "entry": current_close,
                    "tp": tp,
                    "sl": sl,
                    "message": msg,
                    "stars": 5
                }
                
    except Exception as e:
        pass
        
    return None

async def spot_scanner_loop(mexc, telegram_notifier_func):
    logger.info("🔭 SpotBot (1D) ishga tushdi! Uzoq muddatli signallar qidirilmoqda...")
    markets_cache = None
    iteration = 0
    
    sem = asyncio.Semaphore(CONCURRENT_REQUESTS)
    
    while True:
        try:
            tickers = await mexc.fetch_tickers()
            if markets_cache is None or iteration % 12 == 0:
                markets_cache = await mexc.load_markets()
            iteration += 1
            
            valid_symbols = []
            for s, t in tickers.items():
                if not s.endswith('/USDT'): continue
                if is_stablecoin(s, tickers): continue
                if not markets_cache.get(s, {}).get('spot'): continue
                # Spot uchun 24h hajm kamida 5 million bo'lishi yaxshi (ishonchli loyihalar)
                if t.get('quoteVolume', 0) < (MIN_24H_VOLUME * 5): continue
                
                valid_symbols.append(s)

            async def sem_task(sym):
                async with sem:
                    return await analyze_spot_symbol(sym, mexc, tickers)

            tasks = [sem_task(sym) for sym in valid_symbols]
            results = await asyncio.gather(*tasks)
            
            for res in results:
                if res:
                    sent_messages = await telegram_notifier_func(res['message'], res['symbol'])
                    await add_signal(
                        res['symbol'], res['type'], res['entry'], res['tp'], res['sl'], 
                        "PENDING", datetime.now().isoformat(), sent_messages, res['stars']
                    )

            await asyncio.sleep(3600) # Spot bot har 1 soatda 1 marta tekshiradi
            
        except Exception as e:
            logger.error(f"Spot kritik xatoligi: {e}")
            await asyncio.sleep(3600)
