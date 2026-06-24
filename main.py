from keep_alive import keep_alive
keep_alive()

import asyncio
import feedparser
import google.generativeai as genai
from aiogram import Bot
import os

# === SOZLAMALAR ===
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")
TARGET_CHANNEL = os.getenv("TARGET_CHANNEL", "@watcherguruuz")
RSS_URL = os.getenv("RSS_URL", "https://watcher.guru/news/feed")

# Sinalgan va barqaror tarjimon (gemini-1.5-flash) ga o'tdik!
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
bot = Bot(token=BOT_TOKEN)

def xotirani_oqish():
    if os.path.exists("oxirgi_yangilik.txt"):
        try:
            with open("oxirgi_yangilik.txt", "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return ""

def xotiraga_yozish(link):
    try:
        with open("oxirgi_yangilik.txt", "w", encoding="utf-8") as f:
            f.write(link)
    except Exception as e:
        print(f"Xotiraga yozishda xatolik: {e}")

async def check_news():
    print("🌐 Watcher Guru sayti tekshirilmoqda...", flush=True)
    feed = feedparser.parse(RSS_URL)

    if not feed.entries:
        return

    latest_news = feed.entries[0]
    news_link = latest_news.link
    oxirgi_link = xotirani_oqish()

    if news_link != oxirgi_link:
        if oxirgi_link == "":
            print("🚀 Birinchi marta ishga tushdi, xotira bo'sh. Eski yangiliklarni yubormaymiz, faqat saqlaymiz.", flush=True)
            xotiraga_yozish(news_link)
            return

        print("🔔 Yangi post topildi! Tarjima qilinmoqda...", flush=True)
        title = latest_news.title

        prompt = f"Ushbu inglizcha moliyaviy yangilik sarlavhasini o'zbek tiliga professional, moliya jurnalistlari tilida tarjima qil. Ortiqcha gap qo'shma, faqat tarjimani ber.\nSarlavha: {title}"

        try:
            response = model.generate_content(prompt)
            tarjima = response.text.strip()
            
            xabar = f"📰 {tarjima}\n\n👉 [Batafsil o'qish]({news_link})\n\n🇺🇿 {TARGET_CHANNEL}"

            # Rasm bor-yo'qligini tekshirish
            image_url = None
            if hasattr(latest_news, 'media_content') and len(latest_news.media_content) > 0:
                image_url = latest_news.media_content[0].get('url')
            elif hasattr(latest_news, 'enclosures') and len(latest_news.enclosures) > 0:
                image_url = latest_news.enclosures[0].get('href')

            if image_url:
                await bot.send_photo(chat_id=TARGET_CHANNEL, photo=image_url, caption=xabar, parse_mode="Markdown")
            else:
                await bot.send_message(chat_id=TARGET_CHANNEL, text=xabar, parse_mode="Markdown")
            
            xotiraga_yozish(news_link)
            print("✅ Kanalga muvaffaqiyatli yuborildi!", flush=True)
        except Exception as e:
            print(f"❌ Xatolik yuz berdi: {e}", flush=True)
    else:
        print("Hozircha yangi post yo'q. Kutmoqdamiz...", flush=True)

async def main():
    print("🚀 'TANK' bot ishga tushdi! Sayt kuzatilmoqda...", flush=True)
    while True:
        try:
            await check_news()
        except Exception as e:
            print(f"Asosiy xatolik: {e}", flush=True)
        
        await asyncio.sleep(180) 

if __name__ == "__main__":
    asyncio.run(main())
