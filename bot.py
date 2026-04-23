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
    return "Bot 24/7 faol holatda ishlamoqda!"

def run_server():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_server)
    t.start()

# ==========================================
# ⚙️ ASOSIY SOZLAMALAR
# ==========================================
MIN_24H_VOLUME = 1_000_000   
MIN_PRICE_JUMP = 1.5         # O'sish signali uchun minimal foiz (+)
MIN_PRICE_DROP = -1.5        # Qulash signali uchun minimal foiz (-)
VOLUME_SPIKE_X = 2.0         # Har ikki holatda ham hajm necha barobar oshishi kerakligi

TELEGRAM_BOT_TOKEN = '8041515869:AAEbPmoFzh_LZLxZzpR-DP1epc4E3eDTQsg'
TELEGRAM_CHAT_ID = '88808651'

mexc = ccxt.mexc({'enableRateLimit': True})

# ==========================================
# 📩 TELEGRAM XABARNOMA
# ==========================================
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram xatolik: {e}")

# ==========================================
# 📊 ASOSIY TAHLIL ALGORITMI
# ==========================================
def run_scanner():
    print(f"[{time.strftime('%H:%M:%S')}] MEXC bozorini 1H taymfreymda tahlil qilish (O'sish va Qulash) boshlandi...")
    try:
        tickers = mexc.fetch_tickers()
        markets = mexc.load_markets()
        
        valid_symbols = [s for s, t in tickers.items() if s.endswith('/USDT') and markets.get(s, {}).get('spot') and t.get('quoteVolume', 0) >= MIN_24H_VOLUME]
        
        for symbol in valid_symbols:
            try:
                ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1h', limit=100)
                if len(ohlcv) < 50: continue
                
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
                
                current_candle = df.iloc[-1]
                prev_candles = df.iloc[-24:-1] 
                
                current_price = current_candle['close']
                current_ema50 = current_candle['EMA_50']
                
                avg_volume = prev_candles['volume'].mean()
                current_volume = current_candle['volume']
                price_change = ((current_price - current_candle['open']) / current_candle['open']) * 100
                
                # Agar hajm odatdagidan kam bo'lsa, qolgan hisob-kitoblarni qilib o'tirish shart emas
                if current_volume < (avg_volume * VOLUME_SPIKE_X):
                    continue
                    
                volume_spike = current_volume / avg_volume
                
                # 🟢 1-Holat: O'SISH (Hajm kirishi va narx ko'tarilishi)
                if price_change >= MIN_PRICE_JUMP and current_price > current_ema50:
                    msg = (
                        f"🟢 <b>{symbol}</b> | 1H (Nasos)\n\n"
                        f"💵 <b>Narx:</b> ${current_price:.4f}\n"
                        f"📈 <b>O'sish:</b> +{price_change:.2f}%\n"
                        f"📊 <b>Kirgan hajm:</b> {volume_spike:.1f}x\n"
                        f"🛡 <b>Trend:</b> EMA-50 dan yuqori\n\n"
                        f"⚡️ WATCHER GURU.UZ | Skaner"
                    )
                    send_telegram_message(msg)
                    print(f"✅ O'sish signali yuborildi: {symbol}")
                    
                # 🔴 2-Holat: QULASH (Hajm chiqib ketishi va vahimali sotuv)
                elif price_change <= MIN_PRICE_DROP and current_price < current_ema50:
                    msg = (
                        f"🔴 <b>{symbol}</b> | 1H (Damp)\n\n"
                        f"💵 <b>Narx:</b> ${current_price:.4f}\n"
                        f"📉 <b>Qulash:</b> {price_change:.2f}%\n"
                        f"📊 <b>Chiqib ketgan hajm:</b> {volume_spike:.1f}x\n"
                        f"🛡 <b>Trend:</b> EMA-50 dan pastga tushdi\n\n"
                        f"⚡️ WATCHER GURU.UZ | Skaner"
                    )
                    send_telegram_message(msg)
                    print(f"🚨 Qulash signali yuborildi: {symbol}")
                    
                time.sleep(0.1) 
            except Exception: continue
    except Exception as e:
        print(f"Kritik xatolik yuz berdi: {e}")

if __name__ == "__main__":
    keep_alive()
    while True:
        run_scanner()
        print("Skanerlash yakunlandi. 15 daqiqa kutilmoqda...\n")
        time.sleep(900)
