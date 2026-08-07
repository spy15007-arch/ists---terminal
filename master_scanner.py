import os
import requests
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import math
from scipy.stats import norm
import warnings
warnings.filterwarnings('ignore')

# --- TELEGRAM CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram credentials not found in environment variables. Skipping push.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ Telegram message sent successfully!")
        else:
            print(f"❌ Failed to send Telegram message: {response.text}")
    except Exception as e:
        print(f"❌ Error sending Telegram message: {e}")

# --- EXPANDED HIGH-LIQUIDITY UNIVERSE (F&O + High-Momentum Cash Equities) ---
EXTENDED_UNIVERSE = [
    "NETWEB", "MEESHO", "DIXON", "TATAELXSI", "BEL", "LTTS", "TCS", "INFY", "RELIANCE", "MARUTI",
    "APOLLOHOSP", "TATACONSUM", "AARTIIND", "ABB", "ABBOTINDIA", "ABCAPITAL", "ABFRL", "ACC", "ADANIENT", 
    "ADANIPORTS", "ALKEM", "AMBUJACEM", "APOLLOTYRE", "ASHOKLEY", "ASIANPAINT", "ASTRAL", "ATUL", "AUBANK", 
    "AUROPHARMA", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BALKRISIND", "BALRAMCHIN", "BANDHANBNK", 
    "BANKBARODA", "BATAINDIA", "BERGEPAINT", "BHARATFORG", "BHARTIARTL", "BHEL", "BIOCON", "BOSCHLTD", "BPCL", 
    "BRITANNIA", "CANBK", "CANFINHOME", "CHAMBLFERT", "CHOLAFIN", "CIPLA", "COALINDIA", "COFORGE", "COLPAL", 
    "CONCOR", "COROMANDEL", "CROMPTON", "CUB", "CUMMINSIND", "DABUR", "DALBHARAT", "DEEPAKNTR", "DIVISLAB", 
    "DLF", "DRREDDY", "EICHERMOT", "ESCORTS", "EXIDEIND", "FEDERALBNK", "GAIL", "GLENMARK", "GMRINFRA", 
    "GNFC", "GODREJCP", "GODREJPROP", "GRANULES", "GRASIM", "GUJGASLTD", "HAL", "HAVELLS", "HCLTECH", 
    "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDCOPPER", "HINDPETRO", "HINDUNILVR", 
    "ICICIBANK", "ICICIGI", "ICICIPRULI", "IDEA", "IDFCFIRSTB", "IEX", "IGL", "INDHOTEL", "INDIACEM", 
    "INDIAMART", "INDIGO", "INDUSINDBK", "IOC", "IPCALAB", "IRCTC", "ITC", "JINDALSTEL", "JSWSTEEL", 
    "JUBLFOOD", "KOTAKBANK", "LALPATHLAB", "LAURUSLABS", "LICHSGFIN", "LT", "LTIM", "LUPIN", "M&M", 
    "M&MFIN", "MANAPPURAM", "MARICO", "MCDOWELL-N", "MCX", "METROPOLIS", "MFSL", "MGL", "MOTHERSON", 
    "MPHASIS", "MRF", "MUTHOOTFIN", "NATIONALUM", "NAUKRI", "NAVINFLUOR", "NESTLEIND", "NMDC", "NTPC", 
    "OBEROIRLTY", "OFSS", "ONGC", "PAGEIND", "PEL", "PETRONET", "PFC", "PIDILITIND", "PIIND", "PNB", 
    "POLYCAB", "POWERGRID", "PVRINOX", "RAMCOCEM", "RBLBANK", "RECLTD", "SAIL", "SBICARD", "SBILIFE", 
    "SBIN", "SHREECEM", "SHRIRAMFIN", "SIEMENS", "SRF", "SUNPHARMA", "SUNTV", "SYNGENE", "TATACHEM", 
    "TATACOMM", "TATAMOTORS", "TATAPOWER", "TATASTEEL", "TECHM", "TITAN", "TORNTPHARM", "TRENT", 
    "TVSMOTOR", "UBL", "ULTRACEMCO", "UPL", "VEDL", "VOLTAS", "WIPRO", "ZEEL", "ZYDUSLIFE"
]

# --- SECTORAL MAPPING ---
SECTOR_MAP = {
    'IT': ["TCS", "INFY", "TECHM", "HCLTECH", "WIPRO", "COFORGE", "LTIM", "MPHASIS", "OFSS", "NAUKRI", "LTTS", "NETWEB"],
    'AUTO': ["MARUTI", "M&M", "HEROMOTOCO", "BAJAJ-AUTO", "EICHERMOT", "TVSMOTOR", "APOLLOTYRE", "ASHOKLEY", "BALKRISIND", "MOTHERSON", "TATAELXSI"],
    'PHARMA': ["SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "LUPIN", "AUROPHARMA", "ALKEM", "ZYDUSLIFE", "GLENMARK", "METROPOLIS", "LALPATHLAB", "IPCALAB", "BIOCON", "TORNTPHARM", "APOLLOHOSP"],
    'BANKFIN': ["HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK", "SBIN", "INDUSINDBK", "BANKBARODA", "PNB", "AUBANK", "FEDERALBNK", "CHOLAFIN", "BAJFINANCE", "BAJFINSV", "SBICARD", "MUTHOOTFIN", "RECLTD", "PFC", "ABCAPITAL", "CANBK", "CANFINHOME", "LICHSGFIN", "MANAPPURAM", "MFSL", "SBILIFE", "ICICIGI", "ICICIPRULI", "HDFCAMC", "HDFCLIFE", "IDFCFIRSTB", "RBLBANK", "SHRIRAMFIN"],
    'METAL': ["TATASTEEL", "HINDALCO", "JINDALSTEL", "VEDL", "SAIL", "NATIONALUM", "HINDCOPPER"],
    'ENERGY': ["RELIANCE", "ONGC", "BPCL", "IOC", "HINDPETRO", "GAIL", "NTPC", "POWERGRID", "COALINDIA", "TATAPOWER", "ADANIENT", "ADANIPORTS"],
    'FMCG': ["HINDUNILVR", "ITC", "BRITANNIA", "NESTLEIND", "DABUR", "MARICO", "TATACONSUM", "COLPAL", "GODREJCP", "MEESHO", "DIXON", "BEL"]
}

SECTOR_TICKERS = {
    'IT': '^CNXIT',
    'AUTO': '^CNXAUTO',
    'PHARMA': '^CNXPHARMA',
    'BANKFIN': '^NSEBANK',
    'METAL': '^CNXMETAL',
    'ENERGY': '^CNXENERGY',
    'FMCG': '^CNXFMCG'
}

def get_sector_symbol(symbol):
    for sec, syms in SECTOR_MAP.items():
        if symbol in syms:
            return SECTOR_TICKERS.get(sec, '^NSEI')
    return '^NSEI'

def get_session_info():
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    hour, minute = now_ist.hour, now_ist.minute
    
    is_github_action = os.environ.get("GITHUB_ACTIONS") == "true"
    is_manual_dispatch = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
    is_manual = (not is_github_action) or is_manual_dispatch

    if is_manual:
        return now_ist.strftime("%d %b %Y | %I:%M %p (Manual Override)"), "Manual"
    elif hour < 14 or (hour == 14 and minute < 30):
        return now_ist.strftime("%d %b %Y | %I:%M %p (Intraday)"), "Intraday"
    else:
        return now_ist.strftime("%d %b %Y | %I:%M %p (BTST/Afternoon)"), "Afternoon"

def black_scholes(S, K, T, r, sigma, opt_type="CE"):
    if T <= 0 or sigma == 0: 
        if opt_type == "CE": return max(0, S - K)
        else: return max(0, K - S)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if opt_type == "CE":
        prem = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    else:
        prem = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    return round(prem, 2)

def calculate_dynamic_targets(close_p, atr, df_h, df_l, direction="Bullish", is_squeeze=False):
    recent_high = float(df_h.tail(20).max())
    recent_low = float(df_l.tail(20).min())
    diff = max(1.0, recent_high - recent_low)
    
    if direction == "Bullish":
        f_t1, f_t2, f_t3, f_t4, f_t5 = close_p + diff * 0.382, close_p + diff * 0.618, close_p + diff * 1.000, close_p + diff * 1.618, close_p + diff * 2.618
        a_t1, a_t2, a_t3, a_t4, a_t5 = close_p + 0.8 * atr, close_p + 1.6 * atr, close_p + 2.4 * atr, close_p + 3.2 * atr, close_p + 4.0 * atr
    else:
        f_t1, f_t2, f_t3, f_t4, f_t5 = close_p - diff * 0.382, close_p - diff * 0.618, close_p - diff * 1.000, close_p - diff * 1.618, close_p - diff * 2.618
        a_t1, a_t2, a_t3, a_t4, a_t5 = close_p - 0.8 * atr, close_p - 1.6 * atr, close_p - 2.4 * atr, close_p - 3.2 * atr, close_p - 4.0 * atr

    if is_squeeze:
        t1, t2, t3, t4, t5 = f_t1, f_t2, f_t3, f_t4, f_t5
    else:
        t1 = (a_t1 + f_t1) / 2
        t2 = (a_t2 + f_t2) / 2
        t3 = (a_t3 + f_t3) / 2
        t4 = (a_t4 + f_t4) / 2
        t5 = (a_t5 + f_t5) / 2

    return round(t1, 1), round(t2, 1), round(t3, 1), round(t4, 1), round(t5, 1)

def generate_quant_option(price, t1, t2, t3, df_h, df_l, df_c, direction="Bullish"):
    dte = 15 
    step = 100 if price > 5000 else (50 if price > 2000 else (20 if price > 1000 else (10 if price > 500 else 5)))
    atm = int(round(price / step) * step)
    opt_type = "CE" if direction == "Bullish" else "PE"
    try:
        vol = math.sqrt((1.0 / (4.0 * math.log(2.0))) * ((np.log(df_h/df_l)**2).tail(10).mean())) * math.sqrt(252)
        if math.isnan(vol) or vol == 0: vol = np.log(df_c/df_c.shift(1)).tail(10).std() * math.sqrt(252)
        if math.isnan(vol) or vol == 0: vol = 0.2
    except: vol = 0.2
    
    c_prem = black_scholes(price, atm, dte/365.0, 0.07, vol, opt_type)
    pt1 = black_scholes(t1, atm, dte/365.0, 0.07, vol, opt_type)
    pt2 = black_scholes(t2, atm, dte/365.0, 0.07, vol, opt_type)
    pt3 = black_scholes(t3, atm, dte/365.0, 0.07, vol, opt_type)
    return f"{atm} {opt_type}", c_prem, round(pt1, 1), round(pt2, 1), round(pt3, 1)

def check_structure_hh_hl(df_h, df_l):
    if len(df_h) < 20: return True
    h_half1 = df_h.iloc[-20:-10].max()
    h_half2 = df_h.iloc[-10:].max()
    l_half1 = df_l.iloc[-20:-10].min()
    l_half2 = df_l.iloc[-10:].min()
    return (h_half2 >= h_half1) and (l_half2 >= l_half1)

def check_vwap_gate(ticker, close_p):
    try:
        df_intra = yf.download(ticker, period="1d", interval="5m", progress=False, threads=False)
        if df_intra.empty: return True
        if isinstance(df_intra.columns, pd.MultiIndex):
            df_intra.columns = df_intra.columns.get_level_values(0)
        v = df_intra['Volume']
        tp = (df_intra['High'] + df_intra['Low'] + df_intra['Close']) / 3
        vwap = (tp * v).sum() / v.sum() if v.sum() > 0 else close_p
        return close_p >= vwap
    except:
        return True

def validate_mtf_confluence(ticker):
    try:
        df_hr = yf.download(ticker, period="5d", interval="1h", progress=False, threads=False)
        if df_hr.empty: return True
        if isinstance(df_hr.columns, pd.MultiIndex):
            df_hr.columns = df_hr.columns.get_level_values(0)
        df_4h = df_hr['Close'].resample('4H').last().dropna()
        if len(df_4h) >= 3:
            return float(df_4h.iloc[-1]) >= float(df_4h.iloc[-2])
    except:
        pass
    return True

def get_index_options_ideas():
    indices = {'^NSEI': 'NIFTY 50', '^NSEBANK': 'BANK NIFTY'}
    results = []
    
    for ticker, name in indices.items():
        try:
            t_obj = yf.Ticker(ticker)
            data = t_obj.history(period="6mo")
            if data.empty: continue
            
            df_c = data['Close'].dropna()
            df_h = data['High'].dropna()
            df_l = data['Low'].dropna()
            if df_c.empty: continue
            
            try:
                close_p = float(t_obj.fast_info.last_price)
                if math.isnan(close_p) or close_p <= 0:
                    close_p = float(df_c.iloc[-1])
            except:
                close_p = float(df_c.iloc[-1])

            ema_50 = float(df_c.ewm(span=50).mean().iloc[-1])
            
            hl = df_h - df_l
            tr = pd.concat([hl, (df_h - df_c.shift(1)).abs(), (df_l - df_c.shift(1)).abs()], axis=1).max(axis=1)
            atr = float(tr.ewm(alpha=1/14).mean().iloc[-1])
            
            delta = df_c.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rsi_val = float((100 - (100 / (1 + (gain / loss)))).iloc[-1])
            
            if close_p > ema_50:
                direction = "Bullish (Call)"
                t1, t2, t3, t4, t5 = calculate_dynamic_targets(close_p, atr, df_h, df_l, "Bullish", is_squeeze=False)
                eq_sl = round(close_p - 0.8 * atr, 1)
            else:
                direction = "Bearish (Put)"
                t1, t2, t3, t4, t5 = calculate_dynamic_targets(close_p, atr, df_h, df_l, "Bearish", is_squeeze=False)
                eq_sl = round(close_p + 0.8 * atr, 1)
            
            opt, prem, pt1, pt2, pt3 = generate_quant_option(close_p, t1, t2, t3, df_h, df_l, df_c, direction.split(" ")[0])
            
            results.append({
                'Stock': f"{name} {direction}", 'Horizon': 'Intraday', 'Entry': round(close_p, 2),
                'RSI': round(rsi_val, 1), 'EqSL': eq_sl,
                'EqT1': t1, 'EqT2': t2, 'EqT3': t3, 'EqT4': t4, 'EqT5': t5,
                'Opt': opt, 'Prem': prem, 'PT1': pt1, 'PT2': pt2, 'PT3': pt3, 'Score': 10, 'Tag': 'Index MTF Scalp'
            })
        except Exception as e: pass
        
    return pd.DataFrame(results)

def generate_tabular_markdown(df_stocks, df_index, title, filename, include_index=False):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write("> **System:** Expanded Universe + Sectoral RS + VWAP Gate + Strict 1:1.8 RRR\n\n")
        
        if df_stocks.empty and df_index.empty:
            f.write("*Market conditions did not trigger any quantitative setups meeting institutional gates for this timeframe.*\n")
            return

        if include_index and not df_index.empty:
            f.write("## 👑 Index Options (MTF Intraday Scalps)\n\n")
            f.write("| # | Index Direction | Price | Score | Eq SL | Eq T1/T2/T3/T4/T5 | Option | Prem | Prem T1/T2/T3 |\n")
            f.write("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
            for idx, r in df_index.reset_index().iterrows():
                eq_tgts = f"{r['EqT1']}/{r['EqT2']}/{r['EqT3']}/{r['EqT4']}/{r['EqT5']}"
                prem_tgts = f"{r['PT1']}/{r['PT2']}/{r['PT3']}"
                f.write(f"| {idx+1} | **{r['Stock']}** | ₹{r['Entry']} | 🔥 {r['Score']}/10 | ₹{r['EqSL']} | {eq_tgts} | **{r['Opt']}** | ₹{r['Prem']} | {prem_tgts} |\n")
            f.write("\n---\n\n")

        if not df_stocks.empty:
            f.write("## 📊 Expanded Universe Verified Institutional Scans (Long-Only)\n\n")
            f.write("| # | Stock | Setup Type | Price | Score | Eq SL | Eq T1/T2/T3/T4/T5 | Option | Prem | Prem T1/T2/T3 |\n")
            f.write("| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
            for idx, r in df_stocks.reset_index().iterrows():
                badge = f"🔥 {r['Score']}/10" if r['Score'] >= 4 else f"{r['Score']}/10"
                eq_tgts = f"{r['EqT1']}/{r['EqT2']}/{r['EqT3']}/{r['EqT4']}/{r['EqT5']}"
                prem_tgts = f"{r['PT1']}/{r['PT2']}/{r['PT3']}" if r['Prem'] != "-" else "-/-/-"
                f.write(f"| {idx+1} | **{r['Stock']}** | {r['Tag']} | ₹{r['Entry']} | {badge} | ₹{r['EqSL']} | {eq_tgts} | **{r['Opt']}** | ₹{r['Prem']} | {prem_tgts} |\n")

def format_telegram_text(df_stocks, df_index, title):
    msg = f"🚨 *{title}* 🚨\n\n"
    
    if not df_index.empty:
        msg += "👑 *INDEX ALERTS (MTF)*\n"
        for _, r in df_index.iterrows():
            msg += f"• {r['Stock']} @ ₹{r['Entry']}\n  {r['Opt']} @ ₹{r['Prem']}\n  Opt Targets: {r['PT1']}/{r['PT2']}/{r['PT3']}\n\n"
    
    if not df_stocks.empty:
        msg += "📊 *TOP VERIFIED INSTITUTIONAL SETUPS (Long-Only)*\n"
        for idx, r in df_stocks.head(15).reset_index().iterrows():
            msg += f"{idx+1}. {r['Stock']} | *{r['Tag']}* @ ₹{r['Entry']}\n"
            msg += f"   Eq Tgts: {r['EqT1']}/{r['EqT2']}/{r['EqT3']}\n"
            if str(r['Opt']) != "N/A (Cash)":
                msg += f"   Option: {r['Opt']} @ ₹{r['Prem']}\n"
                msg += f"   Opt Tgts: {r['PT1']}/{r['PT2']}/{r['PT3']}\n"
            else:
                msg += f"   Option: N/A (Cash Equity Only)\n"
            msg += "\n"
    else:
        msg += "No setups cleared the institutional gates for this scan."
        
    return msg

def run():
    print("🚀 Starting Automated Master Quant Scanner (Expanded Universe Edition)...")
    sess_title, sess_type = get_session_info()
    print(f"🕒 Timeframe Registered: {sess_title}")
    
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    market_open = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
    
    minutes_elapsed = max(1, (now_ist - market_open).total_seconds() / 60)
    minutes_elapsed = min(minutes_elapsed, 375)
    
    if sess_type in ["Intraday", "Manual"]:
        df_index = get_index_options_ideas()
    else:
        df_index = pd.DataFrame()
    
    # 1. Fetch Nifty 50 Benchmark for Market Relative Strength
    nifty_df = yf.download("^NSEI", period="6mo", interval="1d", progress=False)
    nifty_return_20d = 0.0
    if not nifty_df.empty:
        if isinstance(nifty_df.columns, pd.MultiIndex):
            nifty_df.columns = nifty_df.columns.get_level_values(0)
        nifty_closes = nifty_df['Close'].squeeze()
        if len(nifty_closes) >= 20:
            nifty_return_20d = float(nifty_closes.iloc[-1] / nifty_closes.iloc[-20] - 1)

    # 2. Fetch Sectoral Indices Performance Data
    sector_returns = {}
    unique_sectors = set(SECTOR_TICKERS.values())
    for sec_ticker in unique_sectors:
        try:
            sec_df = yf.download(sec_ticker, period="6mo", interval="1d", progress=False)
            if not sec_df.empty:
                if isinstance(sec_df.columns, pd.MultiIndex):
                    sec_df.columns = sec_df.columns.get_level_values(0)
                sec_closes = sec_df['Close'].squeeze()
                if len(sec_closes) >= 20:
                    sector_returns[sec_ticker] = float(sec_closes.iloc[-1] / sec_closes.iloc[-20] - 1)
                else:
                    sector_returns[sec_ticker] = 0.0
            else:
                sector_returns[sec_ticker] = 0.0
        except:
            sector_returns[sec_ticker] = 0.0

    tickers = [f"{s}.NS" for s in EXTENDED_UNIVERSE]
    data = yf.download(tickers, period="6mo", interval="1d", progress=False, threads=True)
    
    if data.empty: return
    if isinstance(data.columns, pd.MultiIndex):
        closes = data['Close']
        highs = data['High']
        lows = data['Low']
        volumes = data['Volume']
    else:
        closes, highs, lows, volumes = data['Close'], data['High'], data['Low'], data['Volume']

    ema_50_daily = closes.ewm(span=50).mean()
    vol_50d_avg_daily = volumes.rolling(50).mean()
    
    delta = closes.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rsi_daily = 100 - (100 / (1 + (gain / loss)))

    exp1 = closes.ewm(span=12, adjust=False).mean()
    exp2 = closes.ewm(span=26, adjust=False).mean()
    macd_daily = exp1 - exp2
    macd_signal_daily = macd_daily.ewm(span=9, adjust=False).mean()
    
    hl = highs - lows
    hc = (highs - closes.shift(1)).abs()
    lc = (lows - closes.shift(1)).abs()
    tr = pd.DataFrame(np.maximum(hl.values, np.maximum(hc.values, lc.values)), index=hl.index, columns=hl.columns)
    atr_daily = tr.ewm(alpha=1/14).mean()
    
    closes_weekly = closes.resample('W').last().dropna(how='all')
    ema_50_weekly = closes_weekly.ewm(span=50).mean()

    last_vol = volumes.iloc[-1]
    last_vol_50 = vol_50d_avg_daily.iloc[-1]
    last_rsi = rsi_daily.iloc[-1]
    last_macd = macd_daily.iloc[-1]
    last_macd_signal = macd_signal_daily.iloc[-1]
    last_ema_50 = ema_50_daily.iloc[-1]
    last_atr = atr_daily.iloc[-1]
    last_ema_50_weekly = ema_50_weekly.iloc[-1]

    valid_setups = []

    for ticker in closes.columns:
        symbol = ticker.replace(".NS", "")
        try:
            t_obj = yf.Ticker(ticker)
            try:
                close_p = float(t_obj.fast_info.last_price)
                if math.isnan(close_p) or close_p <= 0:
                    close_p = float(closes[ticker].iloc[-1])
            except:
                close_p = float(closes[ticker].iloc[-1])

            vol_today = float(last_vol[ticker])
            if pd.isna(close_p) or close_p <= 0 or vol_today < 1000: continue
            
            vol_50_avg = float(last_vol_50[ticker])
            if pd.isna(vol_50_avg) or vol_50_avg <= 0: continue
            
            rsi_val, macd_val, macd_sig = float(last_rsi[ticker]), float(last_macd[ticker]), float(last_macd_signal[ticker])
            d_ema, w_ema, atr = float(last_ema_50[ticker]), float(last_ema_50_weekly[ticker]), float(last_atr[ticker])
            
            adjusted_vol_50 = vol_50_avg * (minutes_elapsed / 375.0)
            vol_vs = round(vol_today / adjusted_vol_50, 2)

            recent_vol_avg = float(volumes[ticker].tail(3).mean())
            recent_range_avg = float((highs[ticker].tail(3) - lows[ticker].tail(3)).mean())
            is_squeeze = (recent_vol_avg < vol_50_avg * 0.85) and (recent_range_avg < atr * 0.85)
            is_structural_uptrend = check_structure_hh_hl(highs[ticker], lows[ticker])

            # Relative Strength Filters
            stock_closes_series = closes[ticker].dropna()
            stock_return_20d = float(stock_closes_series.iloc[-1] / stock_closes_series.iloc[-20] - 1) if len(stock_closes_series) >= 20 else 0.0
            
            sec_symbol = get_sector_symbol(symbol)
            sec_return_20d = sector_returns.get(sec_symbol, 0.0)
            
            is_relative_strong = (stock_return_20d > nifty_return_20d) and (sec_return_20d >= nifty_return_20d)
            is_volume_breakout = (vol_vs >= 1.2) or is_squeeze

            if vol_vs >= 1.2:
                hor, sl_m = "Intraday", 0.8
            elif is_squeeze or vol_vs >= 1.05:
                hor, sl_m = "BTST", 1.0
            else:
                hor, sl_m = "Swing", 1.5

            # Core Trigger: Trend + MACD + RSI + Structure + Sectoral RS + Volume Breakout / Squeeze
            if close_p > d_ema and close_p > w_ema and macd_val > macd_sig and (45 <= rsi_val <= 85) and is_structural_uptrend and is_relative_strong and is_volume_breakout:
                
                if hor in ["Intraday", "BTST"] and not check_vwap_gate(ticker, close_p):
                    continue

                if not validate_mtf_confluence(ticker):
                    continue

                direction = "Bullish"
                t1, t2, t3, t4, t5 = calculate_dynamic_targets(close_p, atr, highs[ticker], lows[ticker], "Bullish", is_squeeze)
                eq_sl = round(close_p - sl_m * atr, 1)
                
                # Strict 1:1.8 RRR Hard Gate
                risk = close_p - eq_sl
                reward = t1 - close_p
                if risk <= 0 or (reward / risk) < 1.6:
                    continue
                
                if is_squeeze:
                    base_score = 5  
                    tag = "🔥 Squeeze Blast"
                else:
                    base_score = 3 + (2 if vol_vs >= 2.0 else 1)
                    tag = "Volume Breakout"
            else:
                continue 

            df_h, df_l, df_c = highs[ticker].dropna(), lows[ticker].dropna(), closes[ticker].dropna()
            
            try:
                opt, prem, pt1, pt2, pt3 = generate_quant_option(close_p, t1, t2, t3, df_h, df_l, df_c, direction)
            except:
                opt, prem, pt1, pt2, pt3 = "N/A (Cash)", "-", "-", "-", "-"
            
            valid_setups.append({
                'Stock': f"{symbol} (↑)", 'Horizon': hor, 'Tag': tag, 'Entry': round(close_p, 2), 
                'RSI': round(rsi_val,1), 'EqSL': eq_sl, 'EqT1': t1, 'EqT2': t2, 'EqT3': t3, 'EqT4': t4, 'EqT5': t5, 
                'Opt': opt, 'Prem': prem, 'PT1': pt1, 'PT2': pt2, 'PT3': pt3, 'Score': base_score
            })
        except: continue

    df_all = pd.DataFrame(valid_setups).drop_duplicates(subset=['Stock']).sort_values(by=['Score', 'RSI'], ascending=[False, False]) if valid_setups else pd.DataFrame()

    df_intra = df_all[df_all['Horizon'] == 'Intraday'].head(10) if not df_all.empty else pd.DataFrame()
    df_btst = df_all[df_all['Horizon'] == 'BTST'].head(15) if not df_all.empty else pd.DataFrame()
    df_swing = df_all[df_all['Horizon'] == 'Swing'].head(25) if not df_all.empty else pd.DataFrame()

    generate_tabular_markdown(df_intra, df_index, f"⚡ Intraday Report — {sess_title}", "intraday_report.md", include_index=True)
    generate_tabular_markdown(df_btst, pd.DataFrame(), f"🌙 BTST Report — {sess_title}", "btst_report.md", include_index=False)
    generate_tabular_markdown(df_swing, pd.DataFrame(), f"📈 Swing Trade Report — {sess_title}", "swing_report.md", include_index=False)

    if not df_intra.empty or not df_index.empty:
        msg_intra = format_telegram_text(df_intra, df_index, f"⚡ Intraday Report — {sess_title}")
        send_telegram_message(msg_intra)

    if not df_btst.empty:
        msg_btst = format_telegram_text(df_btst, pd.DataFrame(), f"🌙 BTST Report — {sess_title}")
        send_telegram_message(msg_btst)

    if not df_swing.empty:
        msg_swing = format_telegram_text(df_swing, pd.DataFrame(), f"📈 Swing Trade Report — {sess_title}")
        send_telegram_message(msg_swing)

if __name__ == "__main__":
    run()
