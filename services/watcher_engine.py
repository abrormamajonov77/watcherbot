import asyncio
import logging
import aiohttp
import feedparser
from google import genai
from config import GEMINI_KEY, RSS_URL, TARGET_CHANNEL
from database import get_last_news_link, save_last_news_link

logger = logging.getLogger(__name__)

# Yangi google-genai Client (Explicit Header yordamida AQ. kalitlarni majburlash)
client = genai.Client(
    api_key=GEMINI_KEY,
    http_options={'headers': {'x-goog-api-key': GEMINI_KEY}}
)

async def fetch_rss(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

async def check_news_loop(telegram_bot):
    logger.info("📰 WatcherBot (Yangiliklar) ishga tushdi! RSS kuzatilmoqda...")
    
    while True:
        try:
            xml_data = await fetch_rss(RSS_URL)
            feed = feedparser.parse(xml_data)
            
            if feed.entries:
                latest_news = feed.entries[0]
                news_link = latest_news.link
                oxirgi_link = await get_last_news_link()

                if news_link != oxirgi_link:
                    if oxirgi_link == "":
                        logger.info("Watcher: Birinchi marta ishga tushdi, xotira bo'sh. Faqat saqlaymiz.")
                        await save_last_news_link(news_link)
                    else:
                        logger.info("🔔 Watcher: Yangi post topildi! Tarjima qilinmoqda...")
                        title = latest_news.title
                        
                        prompt = (
                            f"Ushbu inglizcha moliyaviy yangilik sarlavhasini o'zbek tiliga professional, "
                            f"moliya jurnalistlari tilida tarjima qil. Ortiqcha gap qo'shma, faqat tarjimani ber.\n"
                            f"Sarlavha: {title}"
                        )
                        
                        # Gemini tarjimasi
                        try:
                            response = await client.aio.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=prompt
                            )
                            tarjima = response.text.strip()
                        except Exception as gem_e:
                            logger.error(f"Gemini API xatosi: {gem_e}")
                            tarjima = title # fallback original
                        
                        xabar = f"📰 <b>{tarjima}</b>\n\n👉 <a href='{news_link}'>Batafsil o'qish</a>\n\n🇺🇿 {TARGET_CHANNEL}"

                        image_url = None
                        if hasattr(latest_news, 'media_content') and len(latest_news.media_content) > 0:
                            image_url = latest_news.media_content[0].get('url')
                        elif hasattr(latest_news, 'enclosures') and len(latest_news.enclosures) > 0:
                            image_url = latest_news.enclosures[0].get('href')

                        try:
                            if image_url:
                                await telegram_bot.send_photo(chat_id=TARGET_CHANNEL, photo=image_url, caption=xabar, parse_mode="HTML")
                            else:
                                await telegram_bot.send_message(chat_id=TARGET_CHANNEL, text=xabar, parse_mode="HTML")
                            
                            await save_last_news_link(news_link)
                            logger.info("✅ Watcher: Kanalga muvaffaqiyatli yuborildi!")
                        except Exception as tg_e:
                            logger.error(f"Watcher Telegram yuborish xatosi: {tg_e}")
                            
        except Exception as e:
            logger.error(f"❌ Watcher asosiy xatosi: {e}")
        
        await asyncio.sleep(180) # 3 minutda bir tekshiradi
