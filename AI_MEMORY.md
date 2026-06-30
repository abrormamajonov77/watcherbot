# AI CONTEXT MEMORY (SnayperBot & WatcherBot)

 Ushbu fayl kelajakda AI (men) yoki dasturchi uchun loyiha tarixini va mantiqini eslatish maqsadida yaratilgan.

## 1. Loyiha Haqida
Loyiha ikkita asosiy qismdan iborat bo'lgan kripto-bot:
*   **SnayperBot:** MEXC birjasida USDT juftliklarini 15M (kirish uchun) va 4H (makro trend uchun) taymfreymlarda tahlil qiladi. RSI, EMA9, va Hajm o'sishi (Volume Spike) asosida LONG yoki SHORT signallarni qidiradi.
*   **WatcherBot:** Watcher Guru RSS orqali yangiliklarni kuzatadi, ularni Gemini AI orqali o'zbek tiliga o'girib, kanalga yuboradi.

## 2. Asosiy Texnologiyalar
*   **Til:** Python 3
*   **Kutubxonalar:** `aiogram`, `ccxt`, `pandas`, `pandas_ta`, `motor` (MongoDB), `google.generativeai` (Gemini), `feedparser`, `Flask` (Render Web Service uchun).
*   **Baza:** MongoDB (Users, Signals, Memory kolleksiyalari).

## 3. Oxirgi Kiritilgan Muhim O'zgarishlar (ATR Integratsiyasi)
Oldingi 0.5% lik qat'iy Stop-Loss qoidasi o'chirildi. Uning o'rniga dinamik **ATR (Average True Range)** tizimi qo'shildi:
*   Agar `(ATR / Joriy narx) * 100 > 0.5%` bo'lsa, bozor **"VOLATILE" (Kuchli tebranish)** holatida deb o'qiladi.
*   **Stop-Loss:** Kirish narxidan `ATR * 1.5` masofaga qo'yiladi.
*   **Take-Profit:** Xavfdan 2 barobar uzoqroqqa, ya'ni `ATR * 3.0` masofaga qo'yiladi.
*   **AI Izohi:** AI prompti shunday sozlangan-ki, u "VOLATILE" bozorda nima uchun Stop-Loss kengroq olinganini obunachilarga ishonchli izohlab beradi.

## 4. Infratuzilma (Deploy)
*   **Hosting:** Render.com (Web Service)
*   **Muammo va Yechim:** Render'da Zero-Downtime Deployment sababli `TelegramConflictError` kelib chiqqan edi (eski va yangi bot birga ishlab). Yechim sifatida `Suspend Web Service` -> `Resume Web Service` qilingan va muammo bartaraf etilgan.
*   **Keep Alive:** Bot Render'da Web Service sifatida yashashi uchun `keep_alive.py` orqali Flask serveri 10000-portda ishlab turadi.

Ushbu ma'lumotlar orqali keyingi suhbatni bemalol shu yerdan davom ettirishimiz mumkin!
