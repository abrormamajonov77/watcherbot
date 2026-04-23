import ccxt
import time
import requests
import pandas as pd

# ==========================================
# ⚙️ ASOSIY SOZLAMALAR
# ==========================================
# Tahlil parametrlari (1H taymfreym uchun)
MIN_24H_VOLUME = 1_000_000   # 24 soatlik minimal savdo aylanmasi ($1M)
MIN_PRICE_JUMP = 1.5        # 1 soat ichidagi minimal narx o'sishi (%)
VOLUME_SPIKE_X = 2.0         # O'rtacha hajmdan necha barobar ko'p bo'lishi kerak

# Telegram sozlamalari
TELEGRAM_BOT_TOKEN = '8041515869:AAEbPmoFzh_LZLxZzpR-DP1epc4E3eDTQsg'
TELEGRAM_CHAT_ID = '88808651'

# 🛡 DIQQAT: API kalitlar olib tashlandi. Birjaga faqat ochiq (Public) rejimda ulanamiz.
mexc = ccxt.mexc({'enableRateLimit': True})

# ==========================================
# 📩 TELEGRAM XABARNOMA Dvigateli
# ==========================================
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": text, 
        "parse_mode": "HTML", 
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegramga yuborishda xatolik: {e}")

# ==========================================
# 📊 ASOSIY TAHLIL ALGORITMI
# ==========================================
def run_scanner():
    print(f"[{time.strftime('%H:%M:%S')}] MEXC bozorini 1H taymfreymda tahlil qilish boshlandi...")
    try:
        tickers = mexc.fetch_tickers()
        markets = mexc.load_markets()
        
        valid_symbols = []
        for symbol, ticker in tickers.items():
            if symbol.endswith('/USDT') and markets.get(symbol, {}).get('spot'):
                quote_volume = ticker.get('quoteVolume', 0)
                if quote_volume and quote_volume >= MIN_24H_VOLUME:
                    valid_symbols.append(symbol)
        
        for symbol in valid_symbols:
            try:
                # O'rtacha hajmni hisoblash va EMA-50 uchun ma'lumotlar
                ohlcv = mexc.fetch_ohlcv(symbol, timeframe='1h', limit=100)
                if len(ohlcv) < 50:
                    continue
                
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                # EMA-50 (Trend indikatori)
                df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
                
                current_candle = df.iloc[-1]
                prev_candles = df.iloc[-24:-1] # So'nggi 23 soat tarixi
                
                current_price = current_candle['close']
                current_ema50 = current_candle['EMA_50']
                
                # 🛡 1-Filtr: Trend tasdig'i (Narx EMA-50 chizig'idan yuqorida bo'lishi shart)
                if current_price < current_ema50:
                    continue
                
                avg_volume = prev_candles['volume'].mean()
                current_volume = current_candle['volume']
                
                price_change = ((current_price - current_candle['open']) / current_candle['open']) * 100
                
                # 📈 2 va 3-Filtrlar: Hajm anomal darajada oshdimi va narx o'sdimi?
                if price_change >= MIN_PRICE_JUMP and current_volume >= (avg_volume * VOLUME_SPIKE_X):
                    volume_spike = current_volume / avg_volume
                    
                    # Premium va minimalistik xabar formati
                    msg = (
                        f"🟢 <b>{symbol}</b> | 1H\n\n"
                        f"💵 <b>Narx:</b> ${current_price:.4f}\n"
                        f"📈 <b>O'sish:</b> +{price_change:.2f}%\n"
                        f"📊 <b>Hajm:</b> {volume_spike:.1f}x\n"
                        f"🛡 <b>Trend:</b> EMA-50 (Tasdiqlandi)\n\n"
                        f"⚡️ WATCHER GURU.UZ | Skaner"
                    )
                    send_telegram_message(msg)
                    print(f"✅ Signal yuborildi: {symbol}")
                
                time.sleep(0.1) # Serverni zo'riqtirmaslik uchun pauza
                
            except Exception:
                continue
                
    except Exception as e:
        print(f"Kritik xatolik yuz berdi: {e}")

# Dasturni doimiy ravishda ishlatish aylanas (Loop)
if __name__ == "__main__":
    while True:
        run_scanner()
        print("Skanerlash yakunlandi. Keyingi siklgacha 15 daqiqa kutilmoqda...\n")
        time.sleep(900) # 15 daqiqa dam olish