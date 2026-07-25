# 📊 Signallarni Toifalarga Ajratish (5-Yulduzli va 3-Yulduzli)

Bu reja signallarni xavf (risk) darajasiga ko'ra ajratib, har xil turdagi treyderlarga qulaylik yaratishni maqsad qiladi. Shuningdek, kunlik hisobotlarni shunga qarab ikkita jadvalga bo'lamiz.

## ⚠️ User Review Required

Quyidagi o'zgarishlar tasdiqlanishi kerak:
1. **Baza (SQLite) yangilanadi**: Eski ma'lumotlar saqlab qolinadi, faqat jadvalga `stars` ustuni qo'shiladi.
2. **Kategoriya Shartlari**:
   - ⭐⭐⭐⭐⭐ **5-Yulduzli (O'ta ishonchli):** 4H (Macro) + 1H (Oraliq) + 15M trend bir xil yo'nalishda. Hajm (volume) o'sishi kamida **2.0 barobar**.
   - ⭐⭐⭐ **3-Yulduzli (O'rta / Risky):** 4H trend tasdig'i shart emas. Faqat 1H va 15M trend mos kelishi kifoya. Hajm o'sishi kamida **1.5 barobar**.
3. **Hisobot shakli**: Kunlik hisobot xuddi kechagidek chiqadi, lekin unda ikkita blok bo'ladi: biri 5 yulduzli signallar uchun, ikkinchisi 3 yulduzli signallar uchun. O'ziga xos tarzda har biri uchun `WinRate` alohida hisoblanadi.

## Proposed Changes

---

### Database (Ma'lumotlar Bazasi)
- Jadvalga yangi ustun qo'shish kerak: `stars` (necha yulduzli ekani).
- Saqlash (add_signal) va o'qish (stats) funksiyalariga `stars` ma'lumotini qo'shish.

#### [MODIFY] database.py
- `init_db()` ichiga `ALTER TABLE signals ADD COLUMN stars INTEGER DEFAULT 5` qatori xavfsiz holda (`try/except`) qo'shiladi.
- `add_signal` va statistikani yig'uvchi so'rovlarga (`get_weekly_signals_stats`, `get_daily_coin_stats`) `stars` kiritiladi.

---

### Engines (Skanerlar)
- Sniper bot ichidagi mantiqni o'zgartirib, endi shartlarni 2 xil toifaga qarab baholashga o'tamiz.
- Spot bot doim 5 yulduzli bo'ladi (chunki 1 kunlik grafik o'z-o'zidan kuchli).

#### [MODIFY] services/sniper_engine.py
- Mantiq ikkiga bo'linadi. Agar 5-yulduz shartini bajarsa, signal turi 5 bo'ladi. Agar qat'iy shart bajarilmay, faqat 3-yulduz sharti bajarsa, signal turi 3 yulduzli bo'ladi.
- Xabar matniga ⭐⭐⭐⭐⭐ yoki ⭐⭐⭐ vizual bezaklari qo'shiladi, foydalanuvchi qanday xavfga kirayotganini aniq bilishi uchun.

#### [MODIFY] services/spot_engine.py
- Bazaga qo'shilayotgan signalda `stars=5` deb o'tkazib yuboriladi.

---

### Monitor va Hisobot
- Monitoring tizimi `stars` ma'lumotlarini farqlay oladi va kun oxiridagi hisobotda ularni 2 ta alohida ro'yxatga ajratib ko'rsatadi.
- (Eslatma: Replay / Javob qaytarish orqali TP/SL urilganini bildirish funksiyasi ayni paytda normal ishlab turibdi va bunga ta'sir qilmaydi).

#### [MODIFY] services/monitor_engine.py
- `daily_reporter` barcha signallarni o'qigach, ularni `5-Yulduz` va `3-Yulduz` degan 2 xil lug'atga (dict) ajratadi.
- AI (Gemini) ga ham shu xildagi (risky va ishonchli yopilgan) natijalar alohida kiritib beriladi.

## Verification Plan

### Manual Verification
1. O'zgarishlar GitHub'ga yuklanadi.
2. Render'da redeploy muvaffaqiyatli o'tgani log'da tekshiriladi (bazaga alter table muvaffaqiyatli bo'lganligi).
3. Bot 3 va 5 yulduzli signallar yuborganida uning dizayni to'g'riligi baholanadi.
