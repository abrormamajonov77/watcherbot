import asyncio
import logging
import pandas as pd
import pandas_ta as ta
from datetime import datetime
from config import MIN_24H_VOLUME, VOLUME_SPIKE_X, CONCURRENT_REQUESTS
from database import add_signal
from utils.indicators import calculate_dynamic_tp_sl, is_stablecoin

seen_signals = {}
logger = logging.getLogger(__name__)

async def analyze_symbol(symbol, mexc, tickers):
    """
    Koinni 15M (kirish), 1H (oraliq trend) va 4H (makro trend) bo'yicha analiz qilish.
    Uchta taymfreym ham bir tomonga qarab tursa signal beriladi.
    """
    try:
        # ── 4H (MAKRO TREND) ────────────────────────────────────────────
        ohlcv_4h = await mexc.fetch_ohlcv(symbol, timeframe='4h', limit=50)
        if len(ohlcv_4h) < 20: return

        df_4h = pd.DataFrame(ohlcv_4h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_4h['ema20'] = ta.ema(df_4h['close'], length=20)
        if pd.isna(df_4h['ema20'].iloc[-2]): return

        # 4H da narx EMA20 dan yuqori/pastda bo'lishi — asosiy yo'nalish
        trend_4h_up = df_4h['close'].iloc[-2] > df_4h['ema20'].iloc[-2]

        # ── 1H (ORALIQ TREND) ───────────────────────────────────────────
        ohlcv_1h = await mexc.fetch_ohlcv(symbol, timeframe='1h', limit=50)
        if len(ohlcv_1h) < 25: return

        df_1h = pd.DataFrame(ohlcv_1h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_1h['ema50'] = ta.ema(df_1h['close'], length=50)
        if pd.isna(df_1h['ema50'].iloc[-2]): return

        trend_1h_up = df_1h['close'].iloc[-2] > df_1h['ema50'].iloc[-2]

        # ── 15M (KIRISH NUQTASI) ────────────────────────────────────────
        ohlcv_15m = await mexc.fetch_ohlcv(symbol, timeframe='15m', limit=100)
        if len(ohlcv_15m) < 25: return

        df = pd.DataFrame(ohlcv_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['ema20'] = ta.ema(df['close'], length=20)
        df['ema50'] = ta.ema(df['close'], length=50)

        closed_candle = df.iloc[-2]
        prev_candles  = df.iloc[-20:-2]  # Oxirgi 18 ta sham tarixi

        current_close  = closed_candle['close']
        current_volume = closed_candle['volume']
        current_rsi    = closed_candle['rsi']
        ema20_val      = closed_candle['ema20']
        ema50_val      = closed_candle['ema50']
        timestamp      = closed_candle['timestamp']

        avg_volume     = prev_candles['volume'].mean()
        resistance_high = prev_candles['high'].max()
        support_low    = prev_candles['low'].min()

        # ── HAJM FILTRI (Eng kami 1.5x, 5 yulduz uchun 2.0x) ────────────
        if current_volume < (avg_volume * 1.5): return
        volume_spike = current_volume / avg_volume

        signal_key = f"{symbol}_{timestamp}"
        if signal_key in seen_signals: return

        signal_type = None
        stars = 3
        tp, sl, atr  = 0, 0, 0

        # Mantiqiy o'zgaruvchilar (breakout/breakdown)
        is_long_breakout = current_close > resistance_high and current_rsi < 75 and ema20_val > ema50_val
        is_short_breakdown = current_close < support_low and current_rsi > 25 and ema20_val < ema50_val

        # ── LONG SHARTLARI ──────────────────────────
        if is_long_breakout and trend_1h_up:
            signal_type = "LONG"
            if trend_4h_up and volume_spike >= 2.0:
                stars = 5
            tp, sl, atr = calculate_dynamic_tp_sl(df, current_close, is_long=True)

        # ── SHORT SHARTLARI ─────────────────────────
        elif is_short_breakdown and not trend_1h_up:
            signal_type = "SHORT"
            if not trend_4h_up and volume_spike >= 2.0:
                stars = 5
            tp, sl, atr = calculate_dynamic_tp_sl(df, current_close, is_long=False)

        if signal_type:
            seen_signals[signal_key] = True

            trend_icon = "📈" if signal_type == "LONG" else "📉"
            entry_emoji = "🚀" if signal_type == "LONG" else "🩸"
            star_emoji = "⭐⭐⭐⭐⭐" if stars == 5 else "⭐⭐⭐"
            star_label = "O'ta ishonchli" if stars == 5 else "O'rta daraja (Risky)"

            msg = (
                f"{entry_emoji} <b>{symbol}</b> | 15M Breakout ({signal_type})\n"
                f"Ishonchlilik: {star_emoji} <i>({star_label})</i>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💵 <b>Kirish narxi:</b> ${current_close:.5f}\n"
                f"🎯 <b>Take-Profit:</b> ${tp:.5f}\n"
                f"🛑 <b>Stop-Loss:</b> ${sl:.5f}\n\n"
                f"📊 <b>Hajm o'sishi:</b> {volume_spike:.1f}x\n"
                f"📉 <b>RSI:</b> {current_rsi:.1f}\n"
                f"📏 <b>ATR (Volatillik):</b> ${atr:.5f}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"{trend_icon} <i>4H {'↑' if trend_4h_up else '↓'} | 1H {'↑' if trend_1h_up else '↓'} | 15M tasdiqlangan</i>"
            )

            logger.info(f"Yangi Snayper Signali: {symbol} - {signal_type} ({stars} yulduz)")
            return {
                "symbol": symbol,
                "type":   signal_type,
                "entry":  current_close,
                "tp":     tp,
                "sl":     sl,
                "message": msg,
                "stars": stars
            }

    except Exception as e:
        pass

    return None


async def sniper_scanner_loop(mexc, telegram_notifier_func):
    """
    MEXC birjasidagi tangalarni skanerlash va signal topsa Telegramga yuborish.
    """
    logger.info("🚀 SnayperBot (15M/1H/4H) ishga tushdi! MEXC skanerlanmoqda...")
    markets_cache = None
    iteration     = 0

    sem = asyncio.Semaphore(CONCURRENT_REQUESTS)

    while True:
        try:
            tickers = await mexc.fetch_tickers()
            if markets_cache is None or iteration % 60 == 0:
                markets_cache = await mexc.load_markets()
            iteration += 1

            valid_symbols = []
            for s, t in tickers.items():
                if not s.endswith('/USDT'):                          continue
                if is_stablecoin(s, tickers):                        continue
                if not markets_cache.get(s, {}).get('spot'):         continue
                if t.get('quoteVolume', 0) < MIN_24H_VOLUME:        continue
                valid_symbols.append(s)

            async def sem_task(sym):
                async with sem:
                    return await analyze_symbol(sym, mexc, tickers)

            results = await asyncio.gather(*[sem_task(sym) for sym in valid_symbols])

            for res in results:
                if res:
                    sent_messages = await telegram_notifier_func(res['message'], res['symbol'])
                    await add_signal(
                        res['symbol'], res['type'], res['entry'], res['tp'], res['sl'],
                        "PENDING", datetime.now().isoformat(), sent_messages, res['stars']
                    )

            await asyncio.sleep(60)  # 1 minutda bir aylanadi

        except Exception as e:
            logger.error(f"Snayper kritik xatoligi: {e}")
            await asyncio.sleep(60)
