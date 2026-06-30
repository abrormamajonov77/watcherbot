import asyncio
import os
from datetime import datetime, timedelta
import pandas as pd
import pandas_ta as ta
import ccxt.async_support as ccxt
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

import feedparser
import google.generativeai as genai
from keep_alive import keep_alive
import motor.motor_asyncio
import certifi
import logging

logging.basicConfig(level=logging.INFO)

# 1. Barcha web-server va asinxron orqa fon jarayonlarini yoqish (Render uchun)
keep_alive()

load_dotenv()

# --- SOZLAMALAR ---
# 1-Bot (Snayper)
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# 2-Bot (Watcher)
WATCHER_TOKEN = os.getenv('BOT_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_KEY')
TARGET_CHANNEL = os.getenv('TARGET_CHANNEL', '@watcherguruuz')
RSS_URL = os.getenv('RSS_URL', 'https://watcher.guru/news/feed')

# 3-MongoDB (Ma'lumotlar bazasi)
MONGO_URI = os.getenv('MONGO_URI')

if not TOKEN or not WATCHER_TOKEN or not GEMINI_KEY:
    print("XATOLIK: .env yoki Variables faylida tokenlar to'liq emas!")
    print("Iltimos, TELEGRAM_BOT_TOKEN, BOT_TOKEN va GEMINI_KEY ni kiriting.")
    exit(1)

if not MONGO_URI:
    print("XATOLIK: MONGO_URI kiritilmagan! MongoDB ga ulanib bo'lmaydi. Dastur to'xtatildi.")
    exit(1)

# MongoDB ulanishi
mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where(), tlsAllowInvalidCertificates=True)
db = mongo_client['sniper_bot_db']
users_collection = db['users']
signals_collection = db['signals']
memory_collection = db['memory']

# Ikkita alohida bot yasaladi
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
watcher_bot = Bot(token=WATCHER_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()

# --- WATCHER GURU BOT QISMI (YANGILIKLAR) ---
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

async def get_ai_technical_analysis(symbol, signal_type, rsi, volume_spike, trend, market_state, is_pump=False):
    pump_text = "DIQQAT! KATTA HAJM VA PUMP!" if is_pump else "O'rtacha"
    prompt = (
        f"Siz professional kripto tahlilchi va Wall Street treyderisiz.\n"
        f"Vazifangiz: Berilgan raqamlar asosida ijodiy, takrorlanmas, o'zbek tilida professional texnik xulosa yozish. Qolipga tushib qolmang.\n\n"
        f"Tanga: {symbol}\n"
        f"Signal: {signal_type}\n"
        f"RSI: {rsi:.1f}\n"
        f"Hajm o'sishi: {volume_spike:.1f} barobar ({pump_text})\n"
        f"Trend (4H): {'O\'sish (Bullish)' if trend else 'Qulash (Bearish)'}\n"
        f"Volatillik: {market_state}\n\n"
        f"Xulosani albatta quyidagi 3 ta qismga bo'lib yozing (Har safar turlicha so'zlar ishlating):\n"
        f"📉 Bozor Konyukturasi: (Nega signal olingani haqida professional fikr)\n"
        f"⚠️ Risk Menejmenti: (Volatillikka qarab xavf holati qanday)\n"
        f"🎯 Kutilayotgan Harakat: (Narxning maqsadi)\n"
    )
    try:
        response = await model.generate_content_async(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"AI Xatolik: {e}")
        return "Bozor holatini qat'iy risk-menejment bilan kuzatish tavsiya etiladi."

async def xotirani_oqish():
    doc = await memory_collection.find_one({"_id": "watcher_memory"})
    if doc:
        return doc.get("oxirgi_link", "")
    return ""

async def xotiraga_yozish(link):
    await memory_collection.update_one(
        {"_id": "watcher_memory"},
        {"$set": {"oxirgi_link": link}},
        upsert=True
    )

async def check_news_loop():
    print("🚀 WatcherBot (2-motor) ishga tushdi! Sayt kuzatilmoqda...", flush=True)
    while True:
        try:
            feed = feedparser.parse(RSS_URL)
            if feed.entries:
                latest_news = feed.entries[0]
                news_link = latest_news.link
                oxirgi_link = await xotirani_oqish()

                if news_link != oxirgi_link:
                    if oxirgi_link == "":
                        print("🚀 Watcher: Baza bo'sh, faqat yangilikni saqlaymiz.", flush=True)
                        await xotiraga_yozish(news_link)
                    else:
                        print("🔔 Watcher: Yangi post topildi! Tarjima qilinmoqda...", flush=True)
                        title = latest_news.title
                        prompt = f"Ushbu inglizcha moliyaviy yangilik sarlavhasini o'zbek tiliga professional, moliya jurnalistlari tilida tarjima qil. Ortiqcha gap qo'shma, faqat tarjimani ber.\nSarlavha: {title}"
                        
                        try:
                            response = await model.generate_content_async(prompt)
                            tarjima = response.text.strip()
                        except Exception:
                            tarjima = title
                        
                        xabar = f"📰 <b>{tarjima}</b>\n\n👉 <a href='{news_link}'>Batafsil o'qish</a>\n\n🇺🇿 {TARGET_CHANNEL}"

                        image_url = None
                        if hasattr(latest_news, 'media_content') and len(latest_news.media_content) > 0:
                            image_url = latest_news.media_content[0].get('url')
                        elif hasattr(latest_news, 'enclosures') and len(latest_news.enclosures) > 0:
                            image_url = latest_news.enclosures[0].get('href')

                        if image_url:
                            await watcher_bot.send_photo(chat_id=TARGET_CHANNEL, photo=image_url, caption=xabar, parse_mode="HTML")
                        else:
                            await watcher_bot.send_message(chat_id=TARGET_CHANNEL, text=xabar, parse_mode="HTML")
                        
                        await xotiraga_yozish(news_link)
                        print("✅ Watcher: Kanalga muvaffaqiyatli yuborildi!", flush=True)
        except Exception as e:
            print(f"❌ Watcher xatosi: {e}", flush=True)
        
        await asyncio.sleep(180)


# --- SNAYPER BOT QISMI (MEXC SCANNER) ---
mexc = ccxt.mexc({'enableRateLimit': True})

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
    
    # Foydalanuvchini bazaga qo'shish
    user_exists = await users_collection.find_one({"user_id": user_id})
    if not user_exists:
        await users_collection.insert_one({
            "user_id": user_id,
            "joined_at": datetime.now().isoformat()
        })
    
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

# AQLLI TARQATUVCHI (BROADCASTER)
async def send_to_all(text, symbol=None):
    tv_url = f"https://www.tradingview.com/chart/?symbol=MEXC:{symbol.replace('/', '')}" if symbol else None
    reply_markup = None
    if tv_url:
        kb = [[InlineKeyboardButton(text="📈 TradingView'da ko'rish", url=tv_url)]]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=kb)
        
    cursor = users_collection.find({})
    async for u_doc in cursor:
        user_id = u_doc['user_id']
        try:
            await bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup, link_preview_options=types.LinkPreviewOptions(is_disabled=True))
        except Exception as e:
            print(f"[{symbol}] Telegram yuborishda xatolik user {user_id} uchun: {e}")
            # Agar botni bloklagan bo'lsa o'chirib tashlash mumkin
            if "bot was blocked by the user" in str(e):
                await users_collection.delete_one({"user_id": user_id})
                
        # Telegram blokirovkasidan (Spam limit) himoya! 
        # 1 soniyada maksimum 30 taga ruxsat beradi. Biz 20 taga moslaymiz (0.05 * 20 = 1 sekund)
        await asyncio.sleep(0.05) 

async def analyze_symbol(symbol):
    async with sem:
        try:
            ohlcv_4h = await mexc.fetch_ohlcv(symbol, timeframe=MACRO_TIMEFRAME, limit=100)
            if len(ohlcv_4h) < 60: return
            
            df_4h = pd.DataFrame(ohlcv_4h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df_4h['ema50'] = ta.ema(df_4h['close'], length=50)
            if pd.isna(df_4h['ema50'].iloc[-2]): return
            macro_trend_up = df_4h['close'].iloc[-2] > df_4h['ema50'].iloc[-2]
            
            ohlcv = await mexc.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=60)
            if len(ohlcv) < (PAST_CANDLES + 20): return
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            adx_data = ta.adx(df['high'], df['low'], df['close'], length=14)
            if adx_data is not None and 'ADX_14' in adx_data.columns:
                df['adx'] = adx_data['ADX_14']
            else:
                df['adx'] = 0
            
            closed_candle = df.iloc[-2]
            prev_candles = df.iloc[-(PAST_CANDLES+2):-2]
            
            current_close = closed_candle['close']
            current_volume = closed_candle['volume']
            current_rsi = closed_candle['rsi']
            current_atr = closed_candle['atr']
            current_adx = closed_candle['adx']
            timestamp = closed_candle['timestamp']
            
            avg_volume = prev_candles['volume'].mean()
            resistance_high = prev_candles['high'].max()
            support_low = prev_candles['low'].min()
            
            if pd.isna(current_atr) or pd.isna(current_adx): return
            
            usdt_volume = current_volume * current_close
            if current_volume < (avg_volume * VOLUME_SPIKE_X): return
            volume_spike = current_volume / avg_volume
            
            is_pump = (volume_spike >= 5.0) and (usdt_volume >= 100000)
            
            if not is_pump and current_adx < 25: return
            
            atr_percent = (current_atr / current_close) * 100
            market_state = "VOLATILE" if atr_percent > 0.5 else "NORMAL"
            
            signal_key = f"{symbol}_{timestamp}"
            if signal_key in seen_signals: return
            
            if current_close > resistance_high and (macro_trend_up or is_pump) and (current_rsi < 85 if is_pump else current_rsi < 75):
                entry = current_close
                sl = entry - (current_atr * 1.5)
                risk = entry - sl
                tp = entry + (current_atr * 3.0)
                
                ai_text = await get_ai_technical_analysis(symbol, "LONG", current_rsi, volume_spike, macro_trend_up, market_state, is_pump)
                
                msg = (
                    f"🚀 <b>{symbol}</b> | 15M Breakout (LONG)\n\n"
                    f"💵 <b>Kirish narxi:</b> ${entry:.4f}\n"
                    f"🎯 <b>Take-Profit:</b> ${tp:.4f}\n"
                    f"🛑 <b>Stop-Loss:</b> ${sl:.4f}\n\n"
                    f"📈 <b>RSI kuchi:</b> {current_rsi:.1f}\n"
                    f"📊 <b>Kirgan hajm:</b> {volume_spike:.1f}x o'sish\n"
                    f"⚡️ <i>4H Trend o'sishda tasdiqlangan!</i>\n\n"
                    f"🤖 <b>AI Xulosasi:</b> <i>{ai_text}</i>"
                )
                seen_signals[signal_key] = True
                
                # Bazaga yozish
                await signals_collection.insert_one({
                    "symbol": symbol, "type": "LONG", "entry": entry,
                    "tp": tp, "sl": sl, "status": "PENDING",
                    "timestamp": datetime.now().isoformat()
                })
                
                await send_to_all(msg, symbol)
                print(f"✅ Snayper LONG: {symbol}")
                
            elif current_close < support_low and (not macro_trend_up or is_pump) and (current_rsi > 15 if is_pump else current_rsi > 25):
                entry = current_close
                sl = entry + (current_atr * 1.5)
                risk = sl - entry
                tp = entry - (current_atr * 3.0)
                
                ai_text = await get_ai_technical_analysis(symbol, "SHORT", current_rsi, volume_spike, macro_trend_up, market_state, is_pump)
                
                msg = (
                    f"🩸 <b>{symbol}</b> | 15M Breakdown (SHORT)\n\n"
                    f"💵 <b>Kirish narxi:</b> ${entry:.4f}\n"
                    f"🎯 <b>Take-Profit:</b> ${tp:.4f}\n"
                    f"🛑 <b>Stop-Loss:</b> ${sl:.4f}\n\n"
                    f"📉 <b>RSI kuchi:</b> {current_rsi:.1f}\n"
                    f"📊 <b>Chiqib ketgan hajm:</b> {volume_spike:.1f}x o'sish\n"
                    f"⚡️ <i>4H Trend qulashda tasdiqlangan!</i>\n\n"
                    f"🤖 <b>AI Xulosasi:</b> <i>{ai_text}</i>"
                )
                seen_signals[signal_key] = True
                
                # Bazaga yozish
                await signals_collection.insert_one({
                    "symbol": symbol, "type": "SHORT", "entry": entry,
                    "tp": tp, "sl": sl, "status": "PENDING",
                    "timestamp": datetime.now().isoformat()
                })
                
                await send_to_all(msg, symbol)
                print(f"🚨 Snayper SHORT: {symbol}")
                
        except Exception as e:
            pass

async def scanner_loop():
    print("🚀 SnayperBot (1-motor) ishga tushdi! MEXC skanerlanmoqda...", flush=True)
    while True:
        try:
            tickers = await mexc.fetch_tickers()
            markets = await mexc.load_markets()
            
            valid_symbols = [s for s, t in tickers.items() if s.endswith('/USDT') and markets.get(s, {}).get('spot') and t.get('quoteVolume', 0) >= MIN_24H_VOLUME]
            
            tasks = [analyze_symbol(sym) for sym in valid_symbols]
            await asyncio.gather(*tasks)
            await asyncio.sleep(60)
        except Exception as e:
            print(f"Snayper kritik xatoligi: {e}")
            await asyncio.sleep(60)

async def background_checker():
    while True:
        try:
            cursor = signals_collection.find({"status": "PENDING"})
            async for sig in cursor:
                try:
                    ticker = await mexc.fetch_ticker(sig['symbol'])
                    current_price = ticker['last']
                    
                    new_status = None
                    if sig['type'] == 'LONG':
                        if current_price >= sig['tp']: new_status = 'WIN'
                        elif current_price <= sig['sl']: new_status = 'LOSS'
                    elif sig['type'] == 'SHORT':
                        if current_price <= sig['tp']: new_status = 'WIN'
                        elif current_price >= sig['sl']: new_status = 'LOSS'
                        
                    if new_status:
                        await signals_collection.update_one(
                            {"_id": sig["_id"]},
                            {"$set": {"status": new_status}}
                        )
                        print(f"📌 Signal yopildi: {sig['symbol']} -> {new_status}")
                except Exception:
                    pass
        except Exception:
            pass
            
        await asyncio.sleep(300)

async def weekly_reporter():
    while True:
        now = datetime.now()
        # Dushanba kuni soat 07:00 da yuboriladi
        if now.weekday() == 0 and now.hour == 7 and 0 <= now.minute <= 9:
            last_week = now - timedelta(days=7)
            total, wins, losses = 0, 0, 0
            
            cursor = signals_collection.find({"status": {"$in": ["WIN", "LOSS"]}})
            async for sig in cursor:
                try:
                    sig_date = datetime.fromisoformat(sig['timestamp'])
                    if sig_date > last_week:
                        total += 1
                        if sig['status'] == 'WIN': wins += 1
                        if sig['status'] == 'LOSS': losses += 1
                except: pass
            
            if total > 0:
                win_rate = (wins / total) * 100
                prompt = (
                    f"Siz kriptotreyder botining professional tahlilchisisiz. Haftalik hisobot:\n"
                    f"Jami signallar: {total} ta\n"
                    f"Foyda (Take-Profit): {wins} ta\n"
                    f"Zarar (Stop-Loss): {losses} ta\n"
                    f"Aniqlik (WinRate): {win_rate:.1f}%\n"
                    f"Vazifa: Ushbu natijaga qarab obunachilarga 1-2 gaplik xolis xulosa va kelasi haftaga ehtiyotkorlik maslahatini yozing. Faqat o'zbek tilida."
                )
                try:
                    response = await model.generate_content_async(prompt)
                    ai_report = response.text.strip()
                except:
                    ai_report = "Tavakkalchilikni me'yorda ushlagan holda, intizom bilan davom etish tavsiya qilinadi."
                
                report_msg = (
                    "📊 <b>O'TGAN HAFTALIK SAVDO HISOBOTI</b> 📊\n\n"
                    f"Yakunlangan haftada Snayper botimiz jami <b>{total} ta</b> signal yopdi.\n\n"
                    f"🎯 <b>Take-Profit (Foyda) olinganlar:</b> {wins} ta\n"
                    f"🛑 <b>Stop-Loss (Zarar) olinganlar:</b> {losses} ta\n"
                    f"🏆 <b>Haftalik Aniqlik (WinRate): {win_rate:.1f}%</b>\n\n"
                    f"🤖 <b>AI Xulosasi:</b> <i>{ai_report}</i>"
                )
                await send_to_all(report_msg)
            
            await asyncio.sleep(3600)
        else:
            await asyncio.sleep(60)

async def main():
    print("Matorlar o't oldirilmoqda...", flush=True)
    asyncio.create_task(scanner_loop())
    asyncio.create_task(background_checker())
    asyncio.create_task(weekly_reporter())
    asyncio.create_task(check_news_loop())
    
    # Aiogram dp faqat SnayperBot (start komandasi) uchun ishlaydi
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
