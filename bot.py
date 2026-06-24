import asyncio
import json
import os
import time
from datetime import datetime, timedelta
import pandas as pd
import pandas_ta as ta
import ccxt.async_support as ccxt
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    print("TELEGRAM_BOT_TOKEN topilmadi. Iltimos .env faylini tekshiring.")
    exit(1)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()

USERS_FILE = 'users.json'
SIGNALS_FILE = 'signals.json'

def load_json(filename, default):
    if not os.path.exists(filename):
        return default
    with open(filename, 'r') as f:
        try:
            return json.load(f)
        except:
            return default

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

users = load_json(USERS_FILE, [])
signals_db = load_json(SIGNALS_FILE, [])

mexc = ccxt.mexc({'enableRateLimit': True})

# === ASOSIY SOZLAMALAR ===
MIN_24H_VOLUME = 1_000_000
TIMEFRAME = '15m'
MACRO_TIMEFRAME = '4h'
VOLUME_SPIKE_X = 2.5
PAST_CANDLES = 16
CONCURRENT_REQUESTS = 5

sem = asyncio.Semaphore(CONCURRENT_REQUESTS)
seen_signals = {} 

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users:
        users.append(user_id)
        save_json(USERS_FILE, users)
    
    warning_text = (
        "⚠️ <b>DIQQAT - MOLIYAVIY MASLAHAT EMAS!</b> ⚠️\n\n"
        "Ushbu bot faqatgina bozor holatini tahlil qilib, <b>yordamchi signallar</b> beradi. "
        "Bot yuborgan signallar 100% to'g'ri chiqishiga kafolat yo'q. "
        "Iltimos, har bir signalni o'zingiz qayta tahlil qiling va faqat o'z xavf-xataringiz ostida savdoga kiring!\n\n"
        "<i>Bot sizga avtomatik signallarni shu yerga yuborishni boshlaydi. Kutib turing... 🚀</i>"
    )
    image_url = "https://images.unsplash.com/photo-1621416894569-0f39ed31d247?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80"
    try:
        await message.answer_photo(photo=image_url, caption=warning_text)
    except Exception:
        await message.answer(warning_text)

async def send_to_all(text, symbol=None):
    tv_url = f"https://www.tradingview.com/chart/?symbol=MEXC:{symbol.replace('/', '')}" if symbol else None
    reply_markup = None
    if tv_url:
        kb = [[InlineKeyboardButton(text="📈 TradingView'da ko'rish", url=tv_url)]]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=kb)
        
    for u in users:
        try:
            await bot.send_message(chat_id=u, text=text, reply_markup=reply_markup, link_preview_options=types.LinkPreviewOptions(is_disabled=True))
        except Exception as e:
            print(f"[{symbol}] Telegram yuborishda xatolik user {u} uchun: {e}")

async def analyze_symbol(symbol):
    async with sem:
        try:
            # 1. 4H Macro trendni tekshiramiz
            ohlcv_4h = await mexc.fetch_ohlcv(symbol, timeframe=MACRO_TIMEFRAME, limit=10)
            if len(ohlcv_4h) < 10: return
            
            df_4h = pd.DataFrame(ohlcv_4h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df_4h['ema9'] = ta.ema(df_4h['close'], length=9)
            
            if pd.isna(df_4h['ema9'].iloc[-2]): return
            macro_trend_up = df_4h['close'].iloc[-2] > df_4h['ema9'].iloc[-2]
            
            # 2. 15M tahlil
            ohlcv = await mexc.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=30)
            if len(ohlcv) < (PAST_CANDLES + 2): return
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['rsi'] = ta.rsi(df['close'], length=14)
            
            # Faqat TO'LIQ YOPILGAN oxirgi shamchani (iloc[-2]) tekshiramiz
            closed_candle = df.iloc[-2]
            prev_candles = df.iloc[-(PAST_CANDLES+2):-2]
            
            current_close = closed_candle['close']
            current_volume = closed_candle['volume']
            current_rsi = closed_candle['rsi']
            timestamp = closed_candle['timestamp']
            
            avg_volume = prev_candles['volume'].mean()
            resistance_high = prev_candles['high'].max()
            support_low = prev_candles['low'].min()
            
            if current_volume < (avg_volume * VOLUME_SPIKE_X):
                return
                
            volume_spike = current_volume / avg_volume
            
            signal_key = f"{symbol}_{timestamp}"
            if signal_key in seen_signals:
                return
            
            # 🟢 O'SISH (LONG)
            if current_close > resistance_high and macro_trend_up and current_rsi < 75:
                entry = current_close
                sl = closed_candle['low'] * 0.995 
                if sl >= entry: sl = entry * 0.99 
                risk = entry - sl
                tp = entry + (risk * 2) # 1:2 Risk-Reward
                
                msg = (
                    f"🚀 <b>{symbol}</b> | 15M Breakout (LONG)\n\n"
                    f"💵 <b>Kirish narxi:</b> ${entry:.4f}\n"
                    f"🎯 <b>Take-Profit:</b> ${tp:.4f}\n"
                    f"🛑 <b>Stop-Loss:</b> ${sl:.4f}\n\n"
                    f"📈 <b>RSI kuchi:</b> {current_rsi:.1f}\n"
                    f"📊 <b>Kirgan hajm:</b> {volume_spike:.1f}x o'sish\n\n"
                    f"⚡️ <i>4H Trend o'sishda tasdiqlangan!</i>"
                )
                seen_signals[signal_key] = True
                signals_db.append({
                    "symbol": symbol, "type": "LONG", "entry": entry,
                    "tp": tp, "sl": sl, "status": "PENDING",
                    "timestamp": datetime.now().isoformat()
                })
                save_json(SIGNALS_FILE, signals_db)
                await send_to_all(msg, symbol)
                print(f"✅ LONG signal: {symbol}")
                
            # 🔴 QULASH (SHORT)
            elif current_close < support_low and not macro_trend_up and current_rsi > 25:
                entry = current_close
                sl = closed_candle['high'] * 1.005
                if sl <= entry: sl = entry * 1.01
                risk = sl - entry
                tp = entry - (risk * 2)
                
                msg = (
                    f"🩸 <b>{symbol}</b> | 15M Breakdown (SHORT)\n\n"
                    f"💵 <b>Kirish narxi:</b> ${entry:.4f}\n"
                    f"🎯 <b>Take-Profit:</b> ${tp:.4f}\n"
                    f"🛑 <b>Stop-Loss:</b> ${sl:.4f}\n\n"
                    f"📉 <b>RSI kuchi:</b> {current_rsi:.1f}\n"
                    f"📊 <b>Chiqib ketgan hajm:</b> {volume_spike:.1f}x o'sish\n\n"
                    f"⚡️ <i>4H Trend qulashda tasdiqlangan!</i>"
                )
                seen_signals[signal_key] = True
                signals_db.append({
                    "symbol": symbol, "type": "SHORT", "entry": entry,
                    "tp": tp, "sl": sl, "status": "PENDING",
                    "timestamp": datetime.now().isoformat()
                })
                save_json(SIGNALS_FILE, signals_db)
                await send_to_all(msg, symbol)
                print(f"🚨 SHORT signal: {symbol}")
                
        except Exception as e:
            pass

async def scanner_loop():
    while True:
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] MEXC bozorini Skanerlash boshlandi...")
            tickers = await mexc.fetch_tickers()
            markets = await mexc.load_markets()
            
            valid_symbols = [s for s, t in tickers.items() if s.endswith('/USDT') and markets.get(s, {}).get('spot') and t.get('quoteVolume', 0) >= MIN_24H_VOLUME]
            print(f"Jami tekshiriladigan tangalar: {len(valid_symbols)} ta")
            
            tasks = [analyze_symbol(sym) for sym in valid_symbols]
            await asyncio.gather(*tasks)
            
            print("Skanerlash yakunlandi. Keyingi siklgacha 1 daqiqa kutilmoqda...\n")
            await asyncio.sleep(60)
        except Exception as e:
            print(f"Skaner kritik xatoligi: {e}")
            await asyncio.sleep(60)

async def background_checker():
    while True:
        try:
            changed = False
            for sig in signals_db:
                if sig['status'] == 'PENDING':
                    try:
                        ticker = await mexc.fetch_ticker(sig['symbol'])
                        current_price = ticker['last']
                        
                        if sig['type'] == 'LONG':
                            if current_price >= sig['tp']:
                                sig['status'] = 'WIN'
                                changed = True
                            elif current_price <= sig['sl']:
                                sig['status'] = 'LOSS'
                                changed = True
                        elif sig['type'] == 'SHORT':
                            if current_price <= sig['tp']:
                                sig['status'] = 'WIN'
                                changed = True
                            elif current_price >= sig['sl']:
                                sig['status'] = 'LOSS'
                                changed = True
                    except:
                        pass
            
            if changed:
                save_json(SIGNALS_FILE, signals_db)
                
        except Exception as e:
            print(f"Checker xatosi: {e}")
            
        await asyncio.sleep(300)

async def weekly_reporter():
    while True:
        now = datetime.now()
        if now.weekday() == 6 and now.hour == 23 and 50 <= now.minute <= 59:
            last_week = now - timedelta(days=7)
            total, wins, losses = 0, 0, 0
            
            for sig in signals_db:
                try:
                    sig_date = datetime.fromisoformat(sig['timestamp'])
                    if sig_date > last_week and sig['status'] in ['WIN', 'LOSS']:
                        total += 1
                        if sig['status'] == 'WIN': wins += 1
                        if sig['status'] == 'LOSS': losses += 1
                except: pass
            
            if total > 0:
                win_rate = (wins / total) * 100
                report_msg = (
                    "📊 <b>HAFTALIK HISOBOT</b> 📊\n\n"
                    f"Yakunlangan haftada jami <b>{total} ta</b> signal yopildi.\n"
                    f"✅ To'g'ri chiqqan: <b>{wins} ta</b>\n"
                    f"❌ Xato chiqqan: <b>{losses} ta</b>\n\n"
                    f"🏆 <b>Haftalik Aniqlik (WinRate): {win_rate:.1f}%</b>"
                )
                await send_to_all(report_msg)
                print("Haftalik hisobot yuborildi.")
            
            await asyncio.sleep(3600)
        else:
            await asyncio.sleep(60)

async def main():
    print("Bot ishga tushmoqda...")
    asyncio.create_task(scanner_loop())
    asyncio.create_task(background_checker())
    asyncio.create_task(weekly_reporter())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
