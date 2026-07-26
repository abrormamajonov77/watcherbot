import asyncio
import logging
import ccxt.async_support as ccxt
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import TELEGRAM_BOT_TOKEN, WATCHER_TOKEN
from database import init_db, add_user, get_all_users
from services.sniper_engine import sniper_scanner_loop
from services.spot_engine import spot_scanner_loop
from services.watcher_engine import check_news_loop
from services.monitor_engine import background_checker, weekly_reporter, daily_reporter
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
        await message.answer_photo(photo=image_url, caption=warning_text)
    except Exception:
        await message.answer(warning_text)

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
