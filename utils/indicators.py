import pandas_ta as ta

def calculate_dynamic_tp_sl(df, current_close, is_long: bool, is_scalp: bool = False):
    """
    Kiritilgan DataFrame asosida dinamik (ATR va Swings) orqali Stop-Loss va Take-Profit hisoblaydi.
    df - pandas DataFrame (koinning oxirgi 100 ta shamlari)
    """
    # ATR hisoblash (volatillik o'lchovi)
    atr = ta.atr(df['high'], df['low'], df['close'], length=14)
    current_atr = atr.iloc[-2] if not atr.isna().iloc[-2] else (df['close'].iloc[-2] * 0.01) # fallback 1%
    
    if is_scalp:
        # Skalping uchun torroq va tezroq risk menejmenti
        risk = current_atr * 0.8
        if is_long:
            sl = current_close - risk
            tp1 = current_close + risk
            tp2 = current_close + (risk * 1.5)
        else:
            sl = current_close + risk
            tp1 = current_close - risk
            tp2 = current_close - (risk * 1.5)
        return float(tp1), float(tp2), float(sl), float(current_atr)

    # Kichik xavfsizlik (soya - wick) masofasi
    buffer = current_atr * 0.5 
    
    if is_long:
        # Long uchun SL = Oxirgi 15 ta shamning eng pastki nuqtasi (Swing Low) - buffer
        swing_low = df['low'].tail(15).min()
        sl = swing_low - buffer
        
        # Risk (zarar) miqdori
        risk = current_close - sl
        
        # Take Profit 1 = Risk * 1 (Risk/Reward 1:1)
        tp1 = current_close + risk
        # Take Profit 2 = Risk * 2 (Risk/Reward 1:2)
        tp2 = current_close + (risk * 2)
    else:
        # Short uchun SL = Oxirgi 15 ta shamning eng yuqori nuqtasi (Swing High) + buffer
        swing_high = df['high'].tail(15).max()
        sl = swing_high + buffer
        
        # Risk (zarar) miqdori
        risk = sl - current_close
        
        # Take Profit 1 = Risk * 1
        tp1 = current_close - risk
        # Take Profit 2 = Risk * 2
        tp2 = current_close - (risk * 2)
        
    return float(tp1), float(tp2), float(sl), float(current_atr)

def is_stablecoin(symbol: str, tickers_data: dict) -> bool:
    """
    Narxi 1$ atrofida doimiy bo'lgan tangalarni aniqlash.
    """
    from config import KNOWN_STABLECOINS
    if symbol in KNOWN_STABLECOINS:
        return True
        
    ticker = tickers_data.get(symbol, {})
    last_price = ticker.get('last', 0)
    high_24 = ticker.get('high', 0)
    low_24 = ticker.get('low', 0)
    
    # Agar narx roppa-rosa 1$ atrofida bo'lsa (0.98 - 1.02)
    if last_price and (0.98 <= last_price <= 1.02):
        # 24 soatlik volatilligini tekshiramiz (eng baland va eng past narx farqi)
        if high_24 and low_24:
            volatility = (high_24 - low_24) / low_24
            # Agar 24 soat ichida narx 1% dan kam o'zgargan bo'lsa -> Bu albatta Stablecoin
            if volatility < 0.01:
                return True
                
    return False
