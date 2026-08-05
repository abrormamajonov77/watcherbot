import os
from dotenv import load_dotenv

load_dotenv()

# --- TOKENS & API KEYS ---
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WATCHER_TOKEN = os.getenv('BOT_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_KEY')

if not TELEGRAM_BOT_TOKEN or not WATCHER_TOKEN or not GEMINI_KEY:
    print("XATOLIK: .env faylida tokenlar (TELEGRAM_BOT_TOKEN, BOT_TOKEN, GEMINI_KEY) to'liq kiritilmagan!")
    exit(1)

# --- WATCHER SETTINGS ---
TARGET_CHANNEL = os.getenv('TARGET_CHANNEL', '@watcherguruuz')
RSS_URL = os.getenv('RSS_URL', 'https://watcher.guru/news/feed')

# --- TRADING SETTINGS ---
MIN_24H_VOLUME = 1_500_000 # Oldin 300k edi, shovqinni (noise) kamaytirish uchun 1.5M qildik
VOLUME_SPIKE_X = 2.5
CONCURRENT_REQUESTS = 5

# Hardcoded stablecoins to filter out immediately before dynamic filtering
KNOWN_STABLECOINS = {
    'USDC/USDT', 'TUSD/USDT', 'USDD/USDT', 'DAI/USDT', 
    'FDUSD/USDT', 'PYUSD/USDT', 'BUSD/USDT', 'USDP/USDT', 'EURT/USDT'
}
