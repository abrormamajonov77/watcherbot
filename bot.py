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
MIN_PRICE_JUMP = 1.5         
MIN_PRICE_DROP = -1.5        
VOLUME_SPIKE_X = 2.0         

TELEGRAM_BOT_TOKEN = '8041515869:AAEbPmoFzh_LZLxZzpR-DP1epc4E3eDTQsg'
TELEGRAM_CHAT_ID = '88808651'

mexc = ccxt.mexc({'enableRateLimit': True})

# ==========================================
# 📩 TELEGRAM XABARNOMA (Tugma bilan)
# ==========================================
def send_telegram_message(text, symbol):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # Koin nomini MEXC ssilkasi uchun to'g'rilash (masalan: BTC/USDT -> BTC_USDT)
    mexc_symbol = symbol.replace('/', '_')
    mexc_url = f"https://www.mexc.com/exchange/{mexc_symbol}"
    
    # Interaktiv tugma (Minimalist dizayn)
    reply_markup = {
        "inline_keyboard": [[
            {"text": "📊 Grafikni ko'rish", "url": mexc_url}
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
# 🛡 4 SOATLIK (4H) TREND FILTRI
# ==========================================
def check_4h_trend(symbol, is_pump):
    try:
        ohlcv_4h = mexc.fetch_ohlcv(symbol, timeframe='4h', limit=100)
        if len(ohlcv_4h) < 50: return False
        
        df_4h = pd.DataFrame(ohlcv_4h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_4h['EMA_50'] = df_4h['close'].ewm(span=50, adjust=False).mean()
        
        current_price = df_4h.iloc[-1]['close']
        current_ema50_4h = df_4h.iloc[-1]['EMA_50']
        
        if is_pump:
            return current_price > current_ema50_4h  # O'sish uchun 4H trend ham tepaga bo'lishi shart
        else:
            return current_price < current_ema50_4h  # Qulash uchun 4H trend ham pastga bo'lishi shart
    except Exception:
        return False

# ==========================================
# 📊 ASOSIY TAHLIL ALGORITMI (1H)
# ==========================================
def run_scanner():
    print(f"[{time.strftime('%H:%M:%S')}] MEXC skaneri (1H + 4H Filtr) ishga tushdi...")
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
                current_ema50_1h = current_candle['EMA_50']
                
                avg_volume = prev_candles['volume'].mean()
                current_volume = current_candle['volume']
                price_change = ((current_price - current_candle['open']) / current_candle['open']) * 100
                
                # Hajm yetarli bo'lmasa, keyingi koinga o'tamiz
                if current_volume < (avg_volume * VOLUME_SPIKE_X):
                    continue
                    
                volume_spike = current_volume / avg_volume
                
                # 🟢 1-Holat: O'SISH (Nasos) - Avval 1H tekshiriladi, keyin 4H ga so'rov yuboriladi
                if price_change >= MIN_PRICE_JUMP and current_price > current_ema50_1h:
                    if check_4h_trend(symbol, is_pump=True):
                        msg = (
                            f"🟢 <b>{symbol}</b> | 1H (Nasos)\n\n"
                            f"💵 <b>Narx:</b> ${current_price:.4f}\n"
                            f"📈 <b>O'sish:</b> +{price_change:.2f}%\n"
                            f"📊 <b>Kirgan hajm:</b> {volume_spike:.1f}x\n"
                            f"🛡 <b>Trend (1H+4H):</b> Tasdiqlandi (Uptrend)\n\n"
                            f"⚡️ WATCHER GURU.UZ | Skaner"
                        )
                        send_telegram_message(msg, symbol)
                        print(f"✅ O'sish signali yuborildi: {symbol}")
                    
                # 🔴 2-Holat: QULASH (Damp) - Avval 1H tekshiriladi, keyin 4H ga so'rov yuboriladi
                elif price_change <= MIN_PRICE_DROP and current_price < current_ema50_1h:
                    if check_4h_trend(symbol, is_pump=False):
                        msg = (
                            f"🔴 <b>{symbol}</b> | 1H (Damp)\n\n"
                            f"💵 <b>Narx:</b> ${current_price:.4f}\n"
                            f"📉 <b>Qulash:</b> {price_change:.2f}%\n"
                            f"📊 <b>Chiqib ketgan hajm:</b> {volume_spike:.1f}x\n"
                            f"🛡 <b>Trend (1H+4H):</b> Tasdiqlandi (Downtrend)\n\n"
                            f"⚡️ WATCHER GURU.UZ | Skaner"
                        )
                        send_telegram_message(msg, symbol)
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
