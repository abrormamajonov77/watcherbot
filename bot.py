import ccxt
import time
import requests
import pandas as pd
from flask import Flask
from threading import Thread

# ==========================================
# 🌐 VEB-SERVER (Budilnik uchun eshik)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Breakout-Snayper 24/7 faol holatda ishlamoqda!"

def run_server():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_server)
    t.start()

# ==========================================
# ⚙️ ASOSIY SOZLAMALAR
# ==========================================
MIN_24H_VOLUME = 1_000_000   
TIMEFRAME = '15m'            # Tezkor reaksiya uchun 15 daqiqalik radar
VOLUME_SPIKE_X = 2.5         # Shovqinni kesish uchun kuchli hajm (2.5 barobar)
PAST_CANDLES = 16            # Oxirgi 4 soatlik tarixni tekshirish (16 ta 15m shamcha = 4 soat)

TELEGRAM_BOT_TOKEN = '8041515869:AAEbPmoFzh_LZLxZzpR-DP1epc4E3eDTQsg'
TELEGRAM_CHAT_ID = '88808651'

mexc = ccxt.mexc({'enableRateLimit': True})

# ==========================================
# 📩 TELEGRAM XABARNOMA (TradingView tugmasi bilan)
# ==========================================
def send_telegram_message(text, symbol):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    tv_symbol = symbol.replace('/', '')
    tv_url = f"https://www.tradingview.com/chart/?symbol=MEXC:{tv_symbol}"
    
    reply_markup = {
        "inline_keyboard": [[
            {"text": "📈 TradingView'da ko'rish", "url": tv_url}
        ]]
    }
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": text, 
        "parse_mode": "HTML", 
        "disable_web_page_preview": True,
        "reply_markup": reply_markup
    }
    
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram xatolik: {e}")

# ==========================================
# 📊 "BREAKOUT" (Yorib o'tish) TAHLIL ALGORITMI
# ==========================================
def run_scanner():
    print(f"[{time.strftime('%H:%M:%S')}] MEXC bozorini 15M (Breakout) strategiyasi bo'yicha tahlil qilish boshlandi...")
    try:
        tickers = mexc.fetch_tickers()
        markets = mexc.load_markets()
        
        valid_symbols = [s for s, t in tickers.items() if s.endswith('/USDT') and markets.get(s, {}).get('spot') and t.get('quoteVolume', 0) >= MIN_24H_VOLUME]
        
        for symbol in valid_symbols:
            try:
                # 30 ta shamcha yuklab olamiz (ehtiyot shart)
                ohlcv = mexc.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=30)
                if len(ohlcv) < (PAST_CANDLES + 2): continue
                
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                # Joriy va o'tgan shamchalarni ajratib olish
                current_candle = df.iloc[-1]
                prev_candles = df.iloc[-(PAST_CANDLES+1):-1] # Oxirgi 4 soatlik tarix
                
                # QOIDALAR:
                current_close = current_candle['close']
                current_volume = current_candle['volume']
                avg_volume = prev_candles['volume'].mean()
                
                # 4 soatlik Shift (Qarshilik) va Pol (Qo'llab-quvvatlash)
                resistance_high = prev_candles['high'].max()
                support_low = prev_candles['low'].min()
                
                # Hajm yetarli bo'lmasa, hisobni shu yerda to'xtatamiz
                if current_volume < (avg_volume * VOLUME_SPIKE_X):
                    continue
                    
                volume_spike = current_volume / avg_volume
                
                # 🟢 1-Holat: O'SISH ("Faqat tanani ko'r" - Close yorib o'tishi shart)
                if current_close > resistance_high:
                    msg = (
                        f"🚀 <b>{symbol}</b> | 15M (Breakout)\n\n"
                        f"💵 <b>Hozirgi Narx:</b> ${current_close:.4f}\n"
                        f"🧱 <b>Yorilgan Shift:</b> ${resistance_high:.4f}\n"
                        f"📊 <b>Kirgan hajm:</b> {volume_spike:.1f}x\n"
                        f"🛡 <b>Trend:</b> 4 soatlik qarshilik tana bilan yorildi!\n\n"
                        f"⚡️ WATCHER GURU.UZ | Skaner"
                    )
                    send_telegram_message(msg, symbol)
                    print(f"✅ Breakout (O'sish) signali yuborildi: {symbol}")
                    
                # 🔴 2-Holat: QULASH ("Faqat tanani ko'r" - Close pastga tushib yopilishi shart)
                elif current_close < support_low:
                    msg = (
                        f"🩸 <b>{symbol}</b> | 15M (Breakdown)\n\n"
                        f"💵 <b>Hozirgi Narx:</b> ${current_close:.4f}\n"
                        f"🧱 <b>Yorilgan Pol:</b> ${support_low:.4f}\n"
                        f"📊 <b>Chiqib ketgan hajm:</b> {volume_spike:.1f}x\n"
                        f"🛡 <b>Trend:</b> 4 soatlik tayanch tana bilan sindirildi!\n\n"
                        f"⚡️ WATCHER GURU.UZ | Skaner"
                    )
                    send_telegram_message(msg, symbol)
                    print(f"🚨 Breakdown (Qulash) signali yuborildi: {symbol}")
                    
                time.sleep(0.1) 
            except Exception: continue
    except Exception as e:
        print(f"Kritik xatolik yuz berdi: {e}")

if __name__ == "__main__":
    keep_alive()
    while True:
        run_scanner()
        print("Skanerlash yakunlandi. Yangi 15M shamcha tahlili uchun 3 daqiqa kutilmoqda...\n")
        time.sleep(180)
