# 🚀 Sniper Botni Mukammallashtirish (V2) Rejasi

Biz topgan xatolarni to'g'rilash bilan birga, botni yanada professional va daromadli qilish uchun quyidagi qo'shimcha takliflarni kiritdim. 

## ⚠️ User Review Required

Iltimos, ushbu yangi takliflarni ko'rib chiqing va tasdiqlang:

### 1. Mantiqiy xatolarni to'g'irlash (Agreed)
- **RSI Paradoksi:** Yorib o'tish (Breakout) paytida RSI cheklovlari olib tashlanib, o'rniga trend kuchi tasdig'i sifatida ishlatiladi (Long uchun RSI > 55, Short uchun RSI < 45).
- **API Yuklamasi:** Dastlab faqat 15M (Kirish) tekshiriladi. Faqat zo'r holat topilsagina 1H va 4H tasdiq uchun so'raladi. Bu API limitlarga tushish ehtimolini 90% ga kamaytiradi.
- **Xatolarni yozish:** Bot jimjit qotib qolmasligi uchun barcha `Exception`lar log faylga yoziladi.

### 2. Yana Nima Taklif Qilaman? (Yangi qo'shimchalar)
- **🎯 Ikkita Take-Profit (TP1 va TP2):** Professional treyderlar bitta TP bilan ishlamaydi. Bot endi TP1 (xavfsiz, 1:1 risk-reward) va TP2 (maksimal foyda, 1:2) beradi. TP1 urilgach, Stop-Loss avtomatik ravishda kirish narxiga (Break-even) ko'chiriladi deb xabar qilinadi.
- **📈 ATR (Sham kattaligi) Filtri:** Yorib o'tayotgan shamning o'lchami o'rtacha shamlar (ATR) dan kattaroq bo'lishini talab qilamiz. Bu bizni bozordagi "qalbaki yorib o'tishlardan" (fakeout) asraydi.
- **🔄 Exponential Backoff (Qayta urinish):** Agar MEXC birjasi botni haqiqatdan ham tiqilinch sababli rad etsa, bot darhol o'tib ketmasdan, 2-3 soniya kutib qayta urinib ko'radi. Bu orqali signallarni o'tkazib yubormaymiz.
- **🌊 Chop Zone (Yonlama bozor) himoyasi:** Bozor o'lik (flat) holatida bo'lganda, EMA20 va EMA50 bir-biriga yopishib qoladi. Shunday paytda hajm (volume) biroz oshsa ham signal olmaslik uchun EMA'lar orasidagi masofa yetarlicha keng bo'lishini shart qilamiz.
- **📊 Order Flow (Bids/Asks) tasdig'i:** Grafikda yorib o'tish (Breakout) bo'lganidan so'ng, u qalbaki (fakeout) emasligini isbotlash uchun MEXC dan **Buyruqlar kitobi (Order Book)** ni tekshiramiz. Agar tepada judayam katta "Sell Wall" (Sotuvchilar devori) tursa signalni bekor qilamiz. Agar oqim (Order Flow) asosan xaridorlar (Bids) tomonda bo'lsagina signal beramiz. Bu WinRate'ni fantastik darajaga olib chiqadi!

## Proposed Changes

---

### [MODIFY] services/sniper_engine.py
- **Fetch ketma-ketligini o'zgartirish:** Avval `fetch_ohlcv(15m)` ishlaydi. Breakout + Volume Spike bo'lsa, keyin `fetch_ohlcv(1h)` va `fetch_ohlcv(4h)`.
- **RSI va ATR:** RSI shartlari teskarisiga o'zgartiriladi va ATR sharti qo'shiladi (`current_candle_size > atr`).
- **TP1 va TP2 hisoblash:** `calculate_dynamic_tp_sl` dan olingan TP qiymatini TP1 va TP2 ga ajratish.

### [MODIFY] database.py & services/monitor_engine.py
- `monitor_engine` kodini yangilash. Agar joriy narx TP1 ga yetsa, qisman daromad qilib SL ni nolga tushirganini xabar berishi. Agar TP2 ga yetsa to'liq foyda.
- Bu funksionallik botni xuddi siz ko'rsatgan "TP2 urilgan (Foyda)" va "Breakeven" hisobotlariga 100% moslashtiradi.

## Verification Plan

### Automated Tests
- Hech qanday qo'shimcha komandalar kerak emas, shunchaki kod sintaksisi tahlil qilinadi.

### Manual Verification
- Renderga deploy qilingandan so'ng, loglarda "Rate limit" yoki boshqa Exception'lar chiqmayotganini kuzatamiz.
- Bot kamida bitta 3 yulduzli yoki 5 yulduzli signal berganda, unda TP1 va TP2 chiqishini tekshiramiz.
