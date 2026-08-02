import asyncio
import logging
import ccxt.async_support as ccxt
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram import F

from config import TELEGRAM_BOT_TOKEN, WATCHER_TOKEN
from database import init_db, add_user, get_all_users, get_pending_signals, get_weekly_signals_stats, get_daily_coin_stats
from services.sniper_engine import sniper_scanner_loop
from services.spot_engine import spot_scanner_loop
from services.watcher_engine import check_news_loop
from services.monitor_engine import background_checker, weekly_reporter, daily_reporter, generate_ai_summary
from keep_alive import keep_alive
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta
from keep_alive import keep_alive

# Logging sozlari
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ikkita alohida bot
bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
watcher_bot = Bot(token=WATCHER_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()

# CCXT MEXC Instance
mexc = ccxt.mexc({
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'}
})

# Katta muammo yechimi: CCXT kutubxonasi 'spot' deb ko'rsatilsa ham orqa fonda 'fetch_swap_markets' orqali 
# fyuchears marketlarni qidiradi va MEXC dagi blokirovka/yangilanish tufayli Crash bo'ladi (bot jim bo'lib qoladi).
# Buni chetlab o'tish uchun shu funksiyani bo'sh (empty) qilib qo'yamiz.
async def mock_fetch_swap_markets(*args, **kwargs):
    return []
mexc.fetch_swap_markets = mock_fetch_swap_markets

def get_main_menu():
    kb = [
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="🟢 Faol Signallar")],
        [KeyboardButton(text="🔍 Tangani tekshirish"), KeyboardButton(text="⚙️ Sozlamalar")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    await add_user(user_id)
    
    warning_text = (
        "⚠️ <b>DIQQAT - MOLIYAVIY MASLAHAT EMAS!</b> ⚠️\n\n"
        "Ushbu bot faqatgina bozor holatini tahlil qilib, <b>yordamchi signallar</b> beradi. "
        "Bot yuborgan signallar 100% to'g'ri chiqishiga kafolat yo'q. "
        "Iltimos, har bir signalni o'zingiz qayta tahlil qiling va faqat o'z xavf-xataringiz ostida savdoga kiring!\n\n"
        "<i>Bot sizga avtomatik signallarni shu yerga yuborishni boshlaydi (Snayper va Spot). Kutib turing... 🚀</i>"
    )
    image_url = "https://images.unsplash.com/photo-1621416894569-0f39ed31d247?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80"
    try:
        await message.answer_photo(photo=image_url, caption=warning_text, reply_markup=get_main_menu())
    except Exception:
        await message.answer(warning_text, reply_markup=get_main_menu())

@dp.message(F.text == "📊 Statistika")
async def handle_stats_btn(message: types.Message):
    await message.answer("Sizning bugungi statistikangiz hisoblanmoqda... ⏳")
    now = datetime.now()
    yesterday_iso = (now - timedelta(days=1)).isoformat()
    
    stats = await get_weekly_signals_stats(yesterday_iso)
    total = 0
    wins, losses, bes = 0, 0, 0
    for row in stats:
        stars, status, count = row[0], row[1], row[2]
        total += count
        if status == 'WIN': wins += count
        elif status == 'LOSS': losses += count
        elif status == 'BREAK_EVEN': bes += count
        
    if total == 0:
        await message.answer("Oxirgi 24 soat ichida yakunlangan signallar yo'q.")
        return
        
    win_rate = (wins / total) * 100
    res = f"📊 <b>OXIRGI 24 SOATLIK STATISTIKA</b> 📊\n\n"
    res += f"Jami yopilgan: {total} ta\n"
    res += f"🎯 TP: {wins} | 🛑 SL: {losses} | 🛡 BE: {bes}\n"
    res += f"🏆 Umumiy Aniqlik: <b>{win_rate:.1f}%</b>"
    await message.answer(res)

@dp.message(F.text == "🟢 Faol Signallar")
async def handle_active_signals(message: types.Message):
    signals = await get_pending_signals()
    if not signals:
        await message.answer("Hozirda ochiq (faol) signallar yo'q.")
        return
    
    res = "🟢 <b>FAOL SIGNALLAR RO'YXATI:</b>\n\n"
    for s in signals:
        res += f"🔸 <b>{s['symbol']}</b> ({s['type']}) | Kirish: ${s['entry']:.4f} | TP1: ${s['tp']:.4f} | SL: ${s['sl']:.4f}\n"
        
    await message.answer(res)

@dp.message(F.text == "🔍 Tangani tekshirish")
async def handle_check_btn(message: types.Message):
    await message.answer("Tangani tahlil qilish uchun quyidagicha yozing:\n\n<code>/check BTC</code>\n(yoki istalgan tanga nomi)")

@dp.message(F.text == "⚙️ Sozlamalar")
async def handle_settings_btn(message: types.Message):
    await message.answer("Tez kunda... Bu yerda siz xabarlarni o'chirib yoqishingiz mumkin bo'ladi.")

@dp.message(Command("check"))
async def cmd_check_coin(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Iltimos koin nomini yozing. Masalan: /check TON")
        return
    
    symbol = args[1].upper()
    if not symbol.endswith("USDT"):
        symbol += "/USDT"
        
    msg = await message.answer(f"🔍 <b>{symbol}</b> tahlil qilinmoqda... ⏳")
    try:
        ohlcv = await mexc.fetch_ohlcv(symbol, timeframe='15m', limit=50)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['ema50'] = ta.ema(df['close'], length=50)
        
        current_close = df['close'].iloc[-1]
        rsi = df['rsi'].iloc[-1]
        ema50 = df['ema50'].iloc[-1]
        
        trend = "O'suvchi (UP)" if current_close > ema50 else "Tushuvchi (DOWN)"
        
        res = f"📊 <b>{symbol} (15M Chart)</b>:\n"
        res += f"💵 Joriy narx: ${current_close:.5f}\n"
        res += f"📉 Trend (EMA50): {trend}\n"
        res += f"⚡ RSI: {rsi:.1f}\n\n"
        
        if current_close > ema50 and rsi > 55:
            res += "Maslahat: O'sish kuchli (LONG ehtimoli bor) 🚀"
        elif current_close < ema50 and rsi < 45:
            res += "Maslahat: Tushish kuchli (SHORT ehtimoli bor) 🩸"
        else:
            res += "Maslahat: Bozor yonlama (Chop zone) - kutib turing 🛡"
            
        await msg.edit_text(res)
    except Exception as e:
        await msg.edit_text(f"Xatolik: Bunday koin topilmadi yoki birjada yo'q ({symbol}).")

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    """Foydalanuvchi bot ishlayotganini tekshirishi uchun ping komandasi."""
    status_msg = (
        "✅ <b>Bot faol holatda ishlayapti!</b>\n\n"
        "Barcha tizimlar joyida:\n"
        "🚀 Snayper skaneri (15M/1H/4H)\n"
        "🔭 Spot skaneri (1D)\n"
        "📰 Yangiliklar (Watcher)\n"
        "🛡 Monitor (TP/SL kuzatish)\n\n"
        "<i>Bozorda qulay imkoniyat paydo bo'lishi bilan signal yuboriladi...</i>"
    )
    await message.answer(status_msg)

async def send_to_all_users(text, symbol=None, reply_to_message_ids=None):
    """Barcha foydalanuvchilarga xabar yuborish (Snayper/Spot uchun)."""
    tv_url = f"https://www.tradingview.com/chart/?symbol=MEXC:{symbol.replace('/', '')}" if symbol else None
    reply_markup = None
    if tv_url:
        kb = [[InlineKeyboardButton(text="📈 TradingView'da ko'rish", url=tv_url)]]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=kb)
        
    users = await get_all_users()
    sent_messages = {}
    
    for u in users:
        try:
            reply_to = reply_to_message_ids.get(str(u)) if reply_to_message_ids else None
            sent_msg = await bot.send_message(
                chat_id=u, 
                text=text, 
                reply_markup=reply_markup, 
                reply_to_message_id=reply_to,
                link_preview_options=types.LinkPreviewOptions(is_disabled=True)
            )
            sent_messages[str(u)] = sent_msg.message_id
        except Exception as e:
            logger.error(f"[{symbol}] Telegram yuborishda xatolik user {u} uchun: {e}")
            
    return sent_messages

async def main():
    logger.info("Bot tizimlari ishga tushirilmoqda...")
    
    # 1. Web server (Render/Heroku uchun)
    keep_alive()
    
    # 2. Database inisializatsiyasi
    await init_db()

    # 3. Webhookni o'chirish (polling bilan conflict bo'lmasin)
    await bot.delete_webhook(drop_pending_updates=True)
    await watcher_bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Webhooklar o'chirildi, polling rejimiga o'tildi.")

    # 4. Asinxron tasklarni (dvigatellarni) yaratish
    asyncio.create_task(sniper_scanner_loop(mexc, send_to_all_users))
    asyncio.create_task(spot_scanner_loop(mexc, send_to_all_users))
    asyncio.create_task(background_checker(mexc, send_to_all_users))
    asyncio.create_task(weekly_reporter(send_to_all_users))
    asyncio.create_task(daily_reporter(send_to_all_users))
    asyncio.create_task(check_news_loop(watcher_bot))
    
    # 4. Telegram Bot polling
    try:
        await dp.start_polling(bot)
    finally:
        await mexc.close()
        await bot.session.close()
        await watcher_bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot to'xtatildi (KeyboardInterrupt).")
