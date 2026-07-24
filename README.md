# CryptoHajmBot

> **Kriptovalyuta signallari va yangiliklar Telegram boti**

## Loyiha Haqida

CryptoHajmBot — MEXC birjasini real vaqt rejimida skanerlab, texnik tahlil asosida savdo signallari beruvchi va kripto yangiliklar tarjima qilib kanalga yuboruvchi Telegram bot.

## Imkoniyatlar

- 🎯 **Snayper Signallari (15M/1H):** Hajm o'sishi va ko'p taymfreymli texnik tahlil asosida qisqa muddatli breakout signallari
- 💎 **Spot Signallari (1D):** EMA200, Golden Cross va hajm tahlili asosida uzoq muddatli pozitsiya signallari
- 📐 **Dinamik TP/SL:** Statik foizlar o'rniga ATR (bozor volatilligi) va Swing High/Low strukturasiga asoslangan ongli Stop-Loss va Take-Profit
- 🛡 **Stablecoin Filtri:** Taniqli va dinamik ravishda aniqlangan stablecoinlar avtomatik o'tkazib yuboriladi
- 📊 **Kunlik Hisobot (17:00):** Har kuni tangalar bo'yicha natijalar va AI tahlili bilan hisobot
- 📈 **Haftalik Hisobot:** Yakshanba kechasi umumiy winrate statistikasi
- 📰 **Yangiliklar:** Watcher.guru RSS tasmasidan yangiliklar o'zbek tiliga tarjima qilinib kanalga yuboriladi

## Texnologiyalar

| Kutubxona | Vazifasi |
|---|---|
| `aiogram` | Telegram Bot API |
| `ccxt` | MEXC birjasiga ulanish |
| `pandas` / `pandas_ta` | Texnik indikatorlar (ATR, EMA, RSI) |
| `aiosqlite` | Asinxron SQLite ma'lumotlar bazasi |
| `aiohttp` | Asinxron HTTP so'rovlar (RSS) |
| `google-generativeai` | Gemini AI (yangilik tarjimasi va hisobot) |

## Loyiha Tuzilmasi

```
cryptohajmbot/
│
├── main.py                  # Asosiy ishga tushiruvchi
├── config.py                # Sozlamalar (.env o'qish)
├── database.py              # SQLite baza amaliyotlari
├── keep_alive.py            # Render uchun web server
├── Procfile                 # Render/Heroku ishga tushirish buyrug'i
├── requirements.txt         # Python kutubxonalari
│
├── services/
│   ├── sniper_engine.py     # Snayper skaneri (15M/1H)
│   ├── spot_engine.py       # Spot skaneri (1D)
│   ├── watcher_engine.py    # Yangiliklar (RSS + Gemini)
│   └── monitor_engine.py    # Signal monitoring va hisobotlar
│
└── utils/
    └── indicators.py        # ATR, Swing High/Low hisoblash
```

## O'rnatish

### 1. .env fayl yarating
```env
TELEGRAM_BOT_TOKEN=your_sniper_bot_token
BOT_TOKEN=your_watcher_bot_token
GEMINI_KEY=your_gemini_api_key
TARGET_CHANNEL=@your_channel_username
RSS_URL=https://watcher.guru/news/feed
```

### 2. Kutubxonalarni o'rnating
```bash
pip install -r requirements.txt
```

### 3. Botni ishga tushiring
```bash
python main.py
```

## Render'da Deploy

Ushbu bot Render.com'da **Worker** sifatida ishga tushirilishi uchun mo'ljallangan. Environment Variables bo'limiga `.env` dagi barcha kalitlarni kiriting.

---
> ⚠️ **Ogohlantirish:** Bot signallari moliyaviy maslahat emas. Har bir signalni mustaqil tahlil qiling.
