import asyncio
import logging
import yfinance as yf
from datetime import datetime, timedelta
import google.generativeai as genai
from config import GEMINI_KEY
from database import get_users_for_macro

logger = logging.getLogger(__name__)

# Gemini sozlamalari
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def get_macro_data():
    try:
        # yfinance orqali oxirgi yopilish yoki joriy narxni olish
        # Dam olish kunlarida (Shanba/Yakshanba) 1d bo'sh kelishi mumkin, shuning uchun 5d beramiz va oxirgisini olamiz
        spx = yf.Ticker("^GSPC").history(period="5d")['Close'].iloc[-1]
        dxy = yf.Ticker("DX-Y.NYB").history(period="5d")['Close'].iloc[-1]
        us10y = yf.Ticker("^TNX").history(period="5d")['Close'].iloc[-1]
        return spx, dxy, us10y
    except Exception as e:
        logger.error(f"yfinance xatosi: {e}")
        return None, None, None

async def generate_macro_analysis(spx, dxy, us10y):
    prompt = f"""
Sen — professional institutsional makroiqtisodchi, texnik tahlilchi va kripto ekspertisan.

VAZIFANG:
Senga joriy bozor ma'lumotlarini taqdim etaman. Sen quyidagi asosiy indikatorlar asosida bozor holatini tahlil qilasan:
1. US10Y (AQSh 10 yillik obligatsiyalar rentabelligi)
2. DXY (Dollar indeksi)
3. SPX (S&P 500 indeksi)
4. Kripto ichki holati: BTC.D (Bitcoin Dominance) va bozor yangiliklari.

Joriy narxlar:
- S&P 500 (SPX): {spx:.2f}
- Dollar indeksi (DXY): {dxy:.2f}
- US 10-Yillik (US10Y): {us10y:.3f}%

TAHLIL TALABLARI:
1. Makro oqim: DXY va US10Y dinamikasiga qarab kapital qayerga oqmoqda? (Risk-On yoki Risk-Off?)
2. Kripto Korrelyatsiya: Makro holat kriptoga qanday ta'sir qilyapti? SPX bilan sinxronlik bormi yoki uzilish (decoupling)?
3. Likvidlik va Og'ish: Katta hajmdagi manipulatsiyalar, fundamental voqealar fonidagi kutilmalar.

HISOBOT FORMATI:
📊 Makro holat: [US10Y, DXY, SPX o'zaro bog'liqligi va xulosasi]
🌊 Kapital oqimi: [Risk-On / Risk-Off / Aralash]
⚠️ Kripto prognoz: [Likvidlik qayerga qarab ketyapti: BTC yoki Altkoinlar? Ehtimoliy harakatlar]
🎯 Yakuniy xulosa: [Bozor moyilligi (Bias): Bullish/Bearish/Wait va joriy risk darajasi (Past/O'rta/Yuqori)]
"""
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, model.generate_content, prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini API xatosi (Macro): {e}")
        return "❌ Kechirasiz, makro tahlilni generatsiya qilishda xatolik yuz berdi."

async def macro_reporter_loop(telegram_bot):
    """
    Har kuni NY Open (18:30) va NY Close (01:00) da makro hisobot yuboradi.
    Shanba va Yakshanba kunlari bozor yopiq bo'lgani uchun ishlamaydi.
    """
    logger.info("📈 Macro Engine ishga tushdi! (NY Open va NY Close kutilmoqda)")
    while True:
        try:
            now = datetime.now()
            # Dushanbadan Jumagacha (0=Monday, 4=Friday). Ammo 01:00 Seshanbadan-Shanbagacha tushishi mumkin, buni hisobga olamiz.
            is_weekday = now.weekday() < 5
            is_saturday_morning = now.weekday() == 5 and now.hour == 1
            
            if is_weekday or is_saturday_morning:
                is_ny_open = (now.hour == 18 and 30 <= now.minute <= 35)
                is_ny_close = (now.hour == 1 and 0 <= now.minute <= 5)
                
                if is_ny_open or is_ny_close:
                    event_name = "New York OPEN 🗽" if is_ny_open else "New York CLOSE 🌃"
                    logger.info(f"Macro Engine: {event_name} kiritilmoqda...")
                    
                    spx, dxy, us10y = get_macro_data()
                    if spx is not None:
                        analysis = await generate_macro_analysis(spx, dxy, us10y)
                        msg = f"🔔 <b>{event_name} - Makro Tahlil</b>\n\n{analysis}"
                        
                        # Faqat makro olishni xohlaganlarga jo'natamiz
                        macro_users = await get_users_for_macro()
                        for u in macro_users:
                            try:
                                await telegram_bot.send_message(chat_id=u, text=msg, parse_mode="HTML")
                            except Exception as e:
                                logger.error(f"Makro xabarni {u} ga yuborishda xato: {e}")
                                
                    # 1 soat uxlatamiz, qayta ishga tushmasligi uchun
                    await asyncio.sleep(3600)
                    continue
                    
        except Exception as e:
            logger.error(f"Macro reporter xatosi: {e}")
            
        await asyncio.sleep(60) # Har daqiqada tekshiradi
