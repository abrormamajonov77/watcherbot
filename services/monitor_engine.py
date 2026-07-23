import asyncio
import logging
from datetime import datetime, timedelta
from database import get_pending_signals, update_signal_status, get_all_users, get_weekly_signals_stats

logger = logging.getLogger(__name__)

async def background_checker(mexc, telegram_notifier_func):
    """
    Kutayotgan (PENDING) signallarni tekshirib boradi, agar TP yoki SL urilsa xabar beradi.
    """
    logger.info("🛡 MonitorBot ishga tushdi! Ochiq signallar nazorat qilinmoqda...")
    while True:
        try:
            pending_signals = await get_pending_signals()
            for sig in pending_signals:
                try:
                    ticker = await mexc.fetch_ticker(sig['symbol'])
                    current_price = ticker['last']
                    
                    hit_tp = False
                    hit_sl = False
                    
                    if sig['type'] == 'LONG':
                        if current_price >= sig['tp']: hit_tp = True
                        elif current_price <= sig['sl']: hit_sl = True
                    elif sig['type'] == 'SHORT':
                        if current_price <= sig['tp']: hit_tp = True
                        elif current_price >= sig['sl']: hit_sl = True
                            
                    if hit_tp or hit_sl:
                        new_status = 'WIN' if hit_tp else 'LOSS'
                        await update_signal_status(sig['id'], new_status)
                        
                        sig_time = datetime.fromisoformat(sig['timestamp']).strftime('%Y-%m-%d %H:%M')
                        emo = "✅" if hit_tp else "❌"
                        res_str = "Take-Profit urildi 🎯" if hit_tp else "Stop-Loss urildi 🛑"
                        
                        msg = (
                            f"{emo} <b>{sig['symbol']}</b> | {sig['type']} signali yopildi!\n"
                            f"Natija: {res_str}\n\n"
                            f"🕒 Signal vaqti: {sig_time}\n"
                            f"💰 Joriy narx: ${current_price:.5f}"
                        )
                        
                        # Xabarni foydalanuvchilarga jo'natish (reply orqali)
                        import json
                        msg_ids = json.loads(sig['message_ids']) if sig['message_ids'] else {}
                        await telegram_notifier_func(msg, sig['symbol'], msg_ids)
                        
                except Exception as e:
                    logger.error(f"Narxni tekshirishda xato {sig['symbol']}: {e}")
                    
        except Exception as e:
            logger.error(f"Background checker xatosi: {e}")
            
        await asyncio.sleep(60) # Har daqiqada tekshiradi

async def weekly_reporter(telegram_notifier_func):
    """
    Har yakshanba kechasi haftalik hisobot yuboradi.
    """
    while True:
        now = datetime.now()
        # Yakshanba (6) soat 23:50 da hisobot
        if now.weekday() == 6 and now.hour == 23 and 50 <= now.minute <= 59:
            last_week_iso = (now - timedelta(days=7)).isoformat()
            stats = await get_weekly_signals_stats(last_week_iso)
            
            wins = 0
            losses = 0
            break_evens = 0
            for row in stats:
                if row[0] == 'WIN': wins = row[1]
                elif row[0] == 'LOSS': losses = row[1]
                elif row[0] == 'BREAK_EVEN': break_evens = row[1]
                
            total = wins + losses + break_evens
            if total > 0:
                win_rate = (wins / total) * 100
                report_msg = (
                    "📊 <b>HAFTALIK SAVDO HISOBOTI</b> 📊\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🔹 <b>Jami yopilgan signallar:</b> {total} ta\n\n"
                    f"🎯 <b>Foyda (TP urilgan):</b> {wins} ta\n"
                    f"🛑 <b>Zarar (SL urilgan):</b> {losses} ta\n"
                    f"🛡 <b>Zararsiz yopilgan (BE):</b> {break_evens} ta\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🏆 <b>Umumiy Aniqlik (WinRate): {win_rate:.1f}%</b> 🚀"
                )
                await telegram_notifier_func(report_msg, None)
            
            await asyncio.sleep(3600) # Keyingi soatgacha uxlaydi
        else:
            await asyncio.sleep(60)

from database import get_pending_signals, update_signal_status, get_all_users, get_weekly_signals_stats, get_daily_coin_stats
import google.generativeai as genai
from config import GEMINI_KEY

# Gemini sozlamalari AI xulosasi uchun
genai.configure(api_key=GEMINI_KEY)
ai_model = genai.GenerativeModel('gemini-1.5-flash')

async def generate_ai_summary(wins, losses, break_evens, win_rate):
    try:
        prompt = (
            f"Sen kriptovalyuta savdo boti tahlilchisisan. Bugun {wins} ta foyda, {losses} ta zarar va {break_evens} ta zararsiz (nolga) "
            f"savdo yopildi. WinRate: {win_rate:.1f}%. Shu natijaga qarab treyderga 1-2 ta gapdan iborat qisqa, "
            f"kreativ va motivatsion AI xulosasini yozib ber. (Masalan, xatolar ko'p bo'lsa intizomga chaqir, "
            f"foyda ko'p bo'lsa tabriklab risk-menejmentni eslat)."
        )
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, ai_model.generate_content, prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"AI Summary xatosi: {e}")
        return "Tavakkalchilikni me'yorda ushlagan holda, intizom bilan davom etish tavsiya qilinadi."

async def daily_reporter(telegram_notifier_func):
    """
    Har kuni 17:00 da kunlik kreativ hisobot yuboradi.
    """
    while True:
        now = datetime.now()
        # Har kuni soat 17:00 da hisobot
        if now.hour == 17 and 0 <= now.minute <= 9:
            yesterday_iso = (now - timedelta(days=1)).isoformat()
            
            # Umumiy statistika
            stats = await get_weekly_signals_stats(yesterday_iso)
            wins, losses, break_evens = 0, 0, 0
            for row in stats:
                if row[0] == 'WIN': wins = row[1]
                elif row[0] == 'LOSS': losses = row[1]
                elif row[0] == 'BREAK_EVEN': break_evens = row[1]
                
            total = wins + losses + break_evens
            
            if total > 0:
                win_rate = (wins / total) * 100
                
                # Tangalar bo'yicha statistika
                coin_stats = await get_daily_coin_stats(yesterday_iso)
                coins_data = {}
                for sym, status, count in coin_stats:
                    if sym not in coins_data:
                        coins_data[sym] = {'WIN': 0, 'LOSS': 0, 'BREAK_EVEN': 0}
                    coins_data[sym][status] = count
                
                # Tangalar ro'yxatini shakllantirish
                coins_str_list = []
                for sym, data in coins_data.items():
                    coins_str_list.append(
                        f"🔸 <b>{sym}:</b> {data['WIN']} ✅ | {data['LOSS']} ❌ | {data['BREAK_EVEN']} 🛡"
                    )
                coins_text = "\n".join(coins_str_list)
                
                # AI Xulosasi
                ai_conclusion = await generate_ai_summary(wins, losses, break_evens, win_rate)
                
                report_msg = (
                    "📊 <b>OXIRGI 24 SOATLIK SAVDO HISOBOTI</b> 📊\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"📈 <b>Jami yopilgan signallar:</b> {total} ta\n\n"
                    f"🎯 <b>Foyda (TP urilgan):</b> {wins} ta\n"
                    f"🛡 <b>Zararsiz yopilgan (BE):</b> {break_evens} ta\n"
                    f"🛑 <b>Zarar (SL urilgan):</b> {losses} ta\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🏆 <b>Kunlik Aniqlik (WinRate): {win_rate:.1f}%</b>\n\n"
                    "🪙 <b>Tangalar bo'yicha natijalar:</b>\n"
                    f"{coins_text}\n\n"
                    "🤖 <b>AI Xulosasi:</b>\n"
                    f"<i>💬 {ai_conclusion}</i>"
                )
                await telegram_notifier_func(report_msg, None)
            
            await asyncio.sleep(3600) # Keyingi soatgacha uxlaydi
        else:
            await asyncio.sleep(60)
