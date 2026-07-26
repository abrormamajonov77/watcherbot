import asyncio
import logging
from datetime import datetime, timedelta
from database import get_pending_signals, update_signal_status, update_signal_sl, get_all_users, get_weekly_signals_stats

logger = logging.getLogger(__name__)

async def background_checker(mexc, telegram_notifier_func):
    """
    Kutayotgan (PENDING, TP1_HIT) signallarni tekshirib boradi, agar TP yoki SL urilsa xabar beradi.
    """
    logger.info("🛡 MonitorBot ishga tushdi! Ochiq signallar nazorat qilinmoqda...")
    while True:
        try:
            pending_signals = await get_pending_signals()
            for sig in pending_signals:
                try:
                    ticker = await mexc.fetch_ticker(sig['symbol'])
                    current_price = ticker['last']
                    
                    sig_id = sig['id']
                    status = sig['status']
                    sig_type = sig['type']
                    entry = sig['entry']
                    tp1 = sig['tp']
                    tp2 = sig['tp2']
                    sl = sig['sl']
                    
                    msg_type = None
                    new_status = None
                    new_sl = None
                    
                    if status == 'PENDING':
                        sig_time_dt = datetime.fromisoformat(sig['timestamp'])
                        # Time-decay for Scalping (2-stars) -> 3 hours
                        if sig['stars'] == 2 and (datetime.now() - sig_time_dt) > timedelta(hours=3):
                            await update_signal_status(sig_id, 'EXPIRED')
                            logger.info(f"{sig['symbol']} Scalp signali eskirgani uchun (3 soat) yopildi.")
                            continue
                            
                        if sig_type == 'LONG':
                            if current_price >= tp1:
                                msg_type = 'TP1'
                                new_status = 'TP1_HIT'
                                new_sl = entry
                            elif current_price <= sl:
                                msg_type = 'LOSS'
                                new_status = 'LOSS'
                        elif sig_type == 'SHORT':
                            if current_price <= tp1:
                                msg_type = 'TP1'
                                new_status = 'TP1_HIT'
                                new_sl = entry
                            elif current_price >= sl:
                                msg_type = 'LOSS'
                                new_status = 'LOSS'
                                
                    elif status == 'TP1_HIT':
                        if sig_type == 'LONG':
                            if tp2 and current_price >= tp2:
                                msg_type = 'WIN'
                                new_status = 'WIN'
                            elif current_price <= sl:
                                msg_type = 'BREAK_EVEN'
                                new_status = 'BREAK_EVEN'
                        elif sig_type == 'SHORT':
                            if tp2 and current_price <= tp2:
                                msg_type = 'WIN'
                                new_status = 'WIN'
                            elif current_price >= sl:
                                msg_type = 'BREAK_EVEN'
                                new_status = 'BREAK_EVEN'
                                
                    if new_status:
                        await update_signal_status(sig_id, new_status)
                        if new_sl:
                            await update_signal_sl(sig_id, new_sl)
                            
                        sig_time_str = datetime.fromisoformat(sig['timestamp']).strftime('%Y-%m-%d %H:%M')
                        
                        if msg_type == 'TP1':
                            emo = "🎯"
                            res_str = "Take-Profit 1 (TP1) urildi! 🥳\nSL kirish narxiga (Break-even) surildi."
                        elif msg_type == 'WIN':
                            emo = "🏆"
                            res_str = "Take-Profit 2 (TP2) urildi! To'liq foyda 💸"
                        elif msg_type == 'LOSS':
                            emo = "🛑"
                            res_str = "Stop-Loss urildi (Zarar bilan yopildi)."
                        elif msg_type == 'BREAK_EVEN':
                            emo = "🛡"
                            res_str = "Zararsiz yopildi (Break-even). TP1 dan keyin narx orqaga qaytdi."
                        
                        msg = (
                            f"{emo} <b>{sig['symbol']}</b> | {sig_type} signali yangilandi!\n"
                            f"Natija: {res_str}\n\n"
                            f"🕒 Signal vaqti: {sig_time_str}\n"
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
            
            data = {
                5: {'WIN': 0, 'LOSS': 0, 'BREAK_EVEN': 0},
                3: {'WIN': 0, 'LOSS': 0, 'BREAK_EVEN': 0},
                2: {'WIN': 0, 'LOSS': 0, 'BREAK_EVEN': 0}
            }
            
            for row in stats:
                stars, status, count = row[0], row[1], row[2]
                if stars in data and status in data[stars]:
                    data[stars][status] += count
                    
            report_parts = ["📊 <b>HAFTALIK SAVDO HISOBOTI</b> 📊\n━━━━━━━━━━━━━━━━━━━━━\n"]
            
            for star in [5, 3, 2]:
                wins = data[star]['WIN']
                losses = data[star]['LOSS']
                bes = data[star]['BREAK_EVEN']
                total = wins + losses + bes
                
                if total > 0:
                    win_rate = (wins / total) * 100
                    star_icon = "⭐⭐⭐⭐⭐ (Spot)" if star == 5 else "⭐⭐⭐ (Snayper)" if star == 3 else "⭐⭐ (Scalping)"
                    report_parts.append(
                        f"🔹 <b>{star_icon}</b>\n"
                        f"Jami yopilgan: {total} ta\n"
                        f"🎯 TP: {wins} | 🛑 SL: {losses} | 🛡 BE: {bes}\n"
                        f"🏆 Aniqlik: <b>{win_rate:.1f}%</b>\n"
                        "━━━━━━━━━━━━━━━━━━━━━\n"
                    )
            
            if len(report_parts) > 1:
                await telegram_notifier_func("".join(report_parts), None)
            
            await asyncio.sleep(3600)
        else:
            await asyncio.sleep(60)

from database import get_pending_signals, update_signal_status, get_all_users, get_weekly_signals_stats, get_daily_coin_stats
import google.generativeai as genai
from config import GEMINI_KEY

# Gemini sozlamalari AI xulosasi uchun
genai.configure(api_key=GEMINI_KEY)
ai_model = genai.GenerativeModel('gemini-1.5-flash')

async def generate_ai_summary(total_stats_text):
    try:
        prompt = (
            f"Sen kriptovalyuta savdo boti tahlilchisisan. Bugungi natijalar:\n"
            f"{total_stats_text}\n"
            f"Shu natijaga qarab treyderga 1-2 ta gapdan iborat qisqa, "
            f"kreativ va motivatsion AI xulosasini yozib ber."
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
        if now.hour == 17 and 0 <= now.minute <= 9:
            yesterday_iso = (now - timedelta(days=1)).isoformat()
            
            # Umumiy statistika
            stats = await get_weekly_signals_stats(yesterday_iso)
            data = {
                5: {'WIN': 0, 'LOSS': 0, 'BREAK_EVEN': 0},
                3: {'WIN': 0, 'LOSS': 0, 'BREAK_EVEN': 0},
                2: {'WIN': 0, 'LOSS': 0, 'BREAK_EVEN': 0}
            }
            total_signals = 0
            
            for row in stats:
                stars, status, count = row[0], row[1], row[2]
                if stars in data and status in data[stars]:
                    data[stars][status] += count
                    total_signals += count
            
            if total_signals > 0:
                coin_stats = await get_daily_coin_stats(yesterday_iso)
                coins_data = {5: {}, 3: {}, 2: {}}
                
                for row in coin_stats:
                    stars, sym, status, count = row[0], row[1], row[2], row[3]
                    if stars in coins_data:
                        if sym not in coins_data[stars]:
                             coins_data[stars][sym] = {'WIN': 0, 'LOSS': 0, 'BREAK_EVEN': 0}
                        coins_data[stars][sym][status] += count
                
                report_parts = [
                    "📊 <b>OXIRGI 24 SOATLIK SAVDO HISOBOTI</b> 📊\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                ]
                
                stats_for_ai = ""
                
                for star in [5, 3, 2]:
                    wins = data[star]['WIN']
                    losses = data[star]['LOSS']
                    bes = data[star]['BREAK_EVEN']
                    total = wins + losses + bes
                    
                    if total > 0:
                        win_rate = (wins / total) * 100
                        star_icon = "⭐⭐⭐⭐⭐ (Spot)" if star == 5 else "⭐⭐⭐ (Snayper)" if star == 3 else "⭐⭐ (Scalping)"
                        
                        coins_str_list = []
                        for sym, cdata in coins_data[star].items():
                            coins_str_list.append(
                                f"🔸 {sym}: {cdata['WIN']}✅ | {cdata['LOSS']}❌ | {cdata['BREAK_EVEN']}🛡"
                            )
                        coins_text = "\n".join(coins_str_list)
                        
                        stats_for_ai += f"{star} Yulduz: {wins} Foyda, {losses} Zarar. Winrate: {win_rate:.1f}%\n"
                        
                        report_parts.append(
                            f"🔹 <b>{star_icon}</b>\n"
                            f"Jami: {total} ta | 🎯 TP: {wins} | 🛑 SL: {losses} | 🛡 BE: {bes}\n"
                            f"🏆 Aniqlik: <b>{win_rate:.1f}%</b>\n\n"
                            f"🪙 <b>Tangalar bo'yicha:</b>\n"
                            f"{coins_text}\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        )
                
                ai_conclusion = await generate_ai_summary(stats_for_ai)
                report_parts.append(
                    "🤖 <b>AI Xulosasi:</b>\n"
                    f"<i>💬 {ai_conclusion}</i>"
                )
                
                await telegram_notifier_func("".join(report_parts), None)
            
            await asyncio.sleep(3600)
        else:
            await asyncio.sleep(60)
