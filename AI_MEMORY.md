# AI CONTEXT MEMORY (SnayperBot & WatcherBot)

 Ushbu fayl kelajakda AI (men) yoki dasturchi uchun loyiha tarixini va mantiqini eslatish maqsadida yaratilgan.

## 1. Loyiha Haqida
Loyiha ikkita asosiy qismdan iborat bo'lgan kripto-bot:
*   **SnayperBot:** MEXC birjasida USDT juftliklarini 15M (kirish uchun) va 4H (makro trend uchun) taymfreymlarda tahlil qiladi. RSI, EMA50 (Oldin EMA9 edi), ADX va Hajm o'sishi asosida LONG/SHORT signallarni qidiradi.
*   **WatcherBot:** Watcher Guru RSS orqali yangiliklarni kuzatadi, ularni Gemini AI orqali o'zbek tiliga o'girib, kanalga yuboradi.

## 2. Asosiy Texnologiyalar
*   **Til:** Python 3
*   **Kutubxonalar:** `aiogram`, `ccxt`, `pandas`, `pandas_ta`, `motor` (MongoDB), `google.generativeai` (Gemini), `feedparser`, `Flask` (Render Web Service).
*   **Baza:** MongoDB (Users, Signals, Memory kolleksiyalari).

## 3. Oxirgi Kiritilgan Muhim O'zgarishlar (Strategiya Yangilanishi - 2026 iyun oxiri)
WinRate juda past (24%) bo'lib ketgani va "Soxta yorib o'tishlarga" aldanmaslik uchun qator yangi filtrlar kiritildi:
*   **ATR Dinamik Stop-Loss:** Oldingi 0.5% lik qat'iy SL o'rniga dinamik ATR tizimi. (SL = ATR * 1.5, TP = ATR * 3.0). Agar ATR/Narx > 0.5% bo'lsa bozor "VOLATILE" deyiladi.
*   **EMA 50 (Makro Trend):** 4H dagi EMA 9 o'rniga endi ishonchli EMA 50 qo'llanadi.
*   **ADX Filtri:** 15M da `ADX(14) < 25` bo'lsa (yassi bozor), signal qat'iyan berilmaydi.
*   **"Sifatli Pump" Bypass Qoidasi:** Agar hajm o'sishi (`volume_spike`) 5.0x dan katta bo'lsa VA ushbu bitta 15M shamchaning USDT aylanmasi kamida **$100,000** bo'lsa, ADX va EMA50 filtrlari aylanib o'tiladi. Bu arzon manipulyatsiyalarga aldanmasdan faqat "Haqiqiy pul" qatnashgan pumplarni ushlab qolish uchun kiritildi.
*   **AI Professional Xulosasi:** Gemini 1.5 promti yangilandi. Endi u "Robotdek" emas, balki "Tirik Wall Street Tahlilchisi" kabi har doim o'zgaruvchan 3 ta qism (Bozor Konyukturasi, Risk Menejmenti, Kutilayotgan Harakat) dan iborat chuqur matn yozadi. Agar signal Bypass (Pump) orqali ushlangan bo'lsa, matn boshiga "DIQQAT KATTA HAJM..." ogohlantirishi qo'shiladi.

## 4. Infratuzilma (Deploy)
*   **Hosting:** Render.com (Web Service)
*   **Muammo va Yechim:** Render'da Zero-Downtime Deployment sababli `TelegramConflictError` kelib chiqqan edi. Yechim: `Suspend Web Service` -> `Resume Web Service`.
*   Bot faqat **1 Million dollardan ($1,000,000)** yuqori kunlik hajmi bor tangalarni tekshiradi.

## 5. Yangilanishlar (2026 Iyul boshlari)
*   **AI Prompting (Persona o'zgarishi):** Gemini 1.5 xavfsizlik filtriga tushib bloklanmaslik uchun botdagi AI roli "Wall Street Trader"dan "Data Analyst"ga (Ma'lumotlar tahlilchisi) o'zgartirildi. AI ga qat'iyan moliyaviy maslahat bermasligi uqtirildi va u endi faqat raqamlarga asoslangan ta'limiy, sof statistik xulosalar yozishga o'tdi.
*   **Haftalik Hisobotda Tangalarni Guruhlash:** `weekly_reporter` funksiyasiga lug'at (`coin_stats`) algoritmi qo'shildi. Bu orqali haftalik hisobotda har bir tanga kesimida alohida nechta muvaffaqiyatli (WIN) va nechta muvaffaqiyatsiz (LOSS) savdo bo'lgani guruhlab chiqariladi (Masalan: `▪️ BTC/USDT: 3 ✅ | 1 ❌`). 

Ushbu ma'lumotlar orqali keyingi suhbatlarni xuddi shu yerdan bemalol davom ettirishimiz mumkin!
