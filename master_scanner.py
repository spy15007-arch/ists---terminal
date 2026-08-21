import os
import requests
import json
import time
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import math
from scipy.stats import norm
import warnings
warnings.filterwarnings('ignore')

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
BASE_CAPITAL_PER_TRADE = 50000  
HIGH_CONVICTION_MULTIPLIER = 2  

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True})
    except Exception: pass

def maintenance_purge():
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    if now_ist.weekday() >= 5: 
        if os.path.exists("sent_alerts.json"):
            os.remove("sent_alerts.json")
            print("🧹 Weekend Maintenance: Purged sent_alerts.json memory file.")

def is_market_open():
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    if now_ist.weekday() >= 5: return False 
    nse_holidays = ["01-26", "03-24", "04-14", "05-01", "08-15", "10-02", "12-25"]
    today_str = now_ist.strftime("%m-%d")
    if today_str in nse_holidays: return False
    return True

STATIC_FNO = [
    "AARTIIND", "ABB", "ABBOTINDIA", "ABCAPITAL", "ABFRL", "ACC", "ACCELYA", "ACTIONCONST", "ADANIENSOL", "ADANIENT", 
    "ADANIGREEN", "ADANIPORTS", "ADANIPOWER", "ALKEM", "AMBUJACEM", "APOLLOHOSP", "APOLLOTYRE", "ASHOKLEY", "ASIANPAINT", 
    "ASTRAL", "ATUL", "AUBANK", "AUROPHARMA", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BALKRISIND", 
    "BALRAMCHIN", "BANDHANBNK", "BANKBARODA", "BATAINDIA", "BEL", "BERGEPAINT", "BHARATFORG", "BHARTIARTL", "BHEL", 
    "BIOCON", "BOSCHLTD", "BPCL", "BRITANNIA", "CANBK", "CANFINHOME", "CHAMBLFERT", "CHOLAFIN", "CIPLA", "COALINDIA", 
    "COFORGE", "COLPAL", "CONCOR", "COROMANDEL", "CROMPTON", "CUB", "CUMMINSIND", "DABUR", "DALBHARAT", "DEEPAKNTR", 
    "DIVISLAB", "DIXON", "DLF", "DRREDDY", "EICHERMOT", "ESCORTS", "EXIDEIND", "FEDERALBNK", "GAIL", "GLENMARK", 
    "GMRINFRA", "GNFC", "GODREJCP", "GODREJPROP", "GRANULES", "GRASIM", "GUJGASLTD", "HAL", "HAVELLS", "HCLTECH", 
    "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDCOPPER", "HINDPETRO", "HINDUNILVR", "ICICIBANK", 
    "ICICIGI", "ICICIPRULI", "IDEA", "IDFCFIRSTB", "IEX", "IGL", "INDHOTEL", "INDIACEM", "INDIAMART", "INDIGO", 
    "INDUSINDBK", "INFY", "IOC", "IPCALAB", "IRCTC", "ITC", "JINDALSTEL", "JSWSTEEL", "JUBLFOOD", "KOTAKBANK", 
    "LALPATHLAB", "LAURUSLABS", "LICHSGFIN", "LT", "LTIM", "LTTS", "LUPIN", "M&M", "M&MFIN", "MANAPPURAM", "MARICO", 
    "MARUTI", "MCDOWELL-N", "MCX", "METROPOLIS", "MFSL", "MGL", "MOTHERSON", "MPHASIS", "MRF", "MUTHOOTFIN", "NATIONALUM", 
    "NAUKRI", "NAVINFLUOR", "NESTLEIND", "NMDC", "NTPC", "OBEROIRLTY", "OFSS", "ONGC", "PAGEIND", "PEL", "PETRONET", 
    "PFC", "PIDILITIND", "PIIND", "PNB", "POLYCAB", "POWERGRID", "PVRINOX", "RAMCOCEM", "RBLBANK", "RECLTD", "RELIANCE", 
    "SAIL", "SBICARD", "SBILIFE", "SBIN", "SHREECEM", "SHRIRAMFIN", "SIEMENS", "SRF", "SUNPHARMA", "SUNTV", "SYNGENE", 
    "TATACHEM", "TATACOMM", "TATACONSUM", "TATAMOTORS", "TATAPOWER", "TATASTEEL", "TCS", "TECHM", "TITAN", "TORNTPHARM", 
    "TRENT", "TVSMOTOR", "UBL", "ULTRACEMCO", "UPL", "VEDL", "VOLTAS", "WIPRO", "ZEEL", "ZYDUSLIFE"
]

raw_symbols_fallback = ("360ONE 3IINFOTECH 3MINDIA 5PAISA 63MOONS AARTIIND ACC ADANIENT ADANIPORTS APOLLOHOSP ASIANPAINT AXISBANK BAJAJ-AUTO BAJFINANCE BEL BHARTIARTL COALINDIA HDFCBANK INFY ITC LT MARUTI RELIANCE SBIN TCS TITAN TRENT WIPRO")
EXTENDED_UNIVERSE_FALLBACK = list(set(raw_symbols_fallback.split()))

def get_complete_nse_universe():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    symbols = set()
    urls = [
        "https://archives.nseindia.com/content/equities/EQUITY_L.csv",
        "https://archives.nseindia.com/content/indices/ind_niftytotalmarket_list.csv",
        "https://archives.nseindia.com/content/indices/ind_niftymicrocap250_list.csv"
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                for line in r.text.splitlines()[1:]:
                    parts = line.split(',')
                    if parts and parts[0].strip():
                        sym = parts[0].strip().replace('"', '')
                        if sym.isalnum() and not sym.startswith("SGB") and not sym.startswith("EBB"):
                            symbols.add(sym)
        except Exception: continue
    if len(symbols) > 300: return sorted(list(symbols))
    return sorted(list(set(STATIC_FNO + EXTENDED_UNIVERSE_FALLBACK)))

def download_in_chunks(tickers, chunk_size=300):
    closes_list, highs_list, lows_list, vols_list = [], [], [], []
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i+chunk_size]
        print(f"📡 Downloading chunk {i//chunk_size + 1}/{math.ceil(len(tickers)/chunk_size)}...")
        d = yf.download(chunk, period="1y", interval="1d", progress=False, threads=True)
        if not d.empty:
            if isinstance(d.columns, pd.MultiIndex):
                if 'Close' in d.columns.levels[0]: closes_list.append(d['Close'])
                if 'High' in d.columns.levels[0]: highs_list.append(d['High'])
                if 'Low' in d.columns.levels[0]: lows_list.append(d['Low'])
                if 'Volume' in d.columns.levels[0]: vols_list.append(d['Volume'])
            else: 
                sym = chunk[0]
                closes_list.append(d[['Close']].rename(columns={'Close': sym}))
                highs_list.append(d[['High']].rename(columns={'High': sym}))
                lows_list.append(d[['Low']].rename(columns={'Low': sym}))
                vols_list.append(d[['Volume']].rename(columns={'Volume': sym}))
        time.sleep(0.5)
        
    closes = pd.concat(closes_list, axis=1) if closes_list else pd.DataFrame()
    highs = pd.concat(highs_list, axis=1) if highs_list else pd.DataFrame()
    lows = pd.concat(lows_list, axis=1) if lows_list else pd.DataFrame()
    volumes = pd.concat(vols_list, axis=1) if vols_list else pd.DataFrame()
    
    closes = closes.loc[:,~closes.columns.duplicated()]
    highs = highs.loc[:,~highs.columns.duplicated()]
    lows = lows.loc[:,~lows.columns.duplicated()]
    volumes = volumes.loc[:,~volumes.columns.duplicated()]
    return closes, highs, lows, volumes

def get_new_alerts(df, category_name):
    if df.empty: return df
    today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    alert_file = "sent_alerts.json"
    
    try:
        if os.path.exists(alert_file):
            with open(alert_file, "r") as f: alerts_db = json.load(f)
        else: alerts_db = {}
    except: alerts_db = {}
        
    if alerts_db.get("date") != today_str:
        alerts_db = {"date": today_str, "sent": []}
        
    new_rows = []
    for idx, row in df.iterrows():
        alert_id = f"{row['Stock']}_{row['Tag']}_{category_name}"
        if alert_id not in alerts_db["sent"]:
            new_rows.append(row)
            alerts_db["sent"].append(alert_id)
            
    with open(alert_file, "w") as f: json.dump(alerts_db, f)
    return pd.DataFrame(new_rows)

def get_session_info():
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    is_github_action = os.environ.get("GITHUB_ACTIONS") == "true"
    is_manual = (not is_github_action) or (os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch")

    if is_manual: return now_ist.strftime("%d %b %Y | %I:%M %p (Manual Override)"), "Manual"
    elif now_ist.hour < 14 or (now_ist.hour == 14 and now_ist.minute < 30): return now_ist.strftime("%d %b %Y | %I:%M %p (Intraday)"), "Intraday"
    else: return now_ist.strftime("%d %b %Y | %I:%M %p (BTST/Afternoon)"), "Afternoon"

def black_scholes(S, K, T, r, sigma, opt_type="CE"):
    if T <= 0 or sigma == 0: return max(0, S - K) if opt_type == "CE" else max(0, K - S)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if opt_type == "CE": return round(S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2), 2)
    else: return round(K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1), 2)

def get_index_dte(ticker):
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    target_day = 2 if "BANK" in ticker else 3 
    days_to_expiry = target_day - now_ist.weekday()
    if days_to_expiry < 0: days_to_expiry += 7
    if days_to_expiry == 0 and now_ist.hour >= 15: days_to_expiry = 7
    return max(0.5, days_to_expiry)

def calculate_dynamic_targets(close_p, atr, df_h, df_l, direction="Bullish", is_squeeze=False):
    diff = max(2.0, float(df_h.tail(20).max()) - float(df_l.tail(20).min()))
    if direction == "Bullish":
        return (round((close_p + 0.8*atr + close_p + diff*0.236)/2, 1), round((close_p + 1.6*atr + close_p + diff*0.382)/2, 1), 
                round((close_p + 2.4*atr + close_p + diff*0.618)/2, 1), round((close_p + 3.2*atr + close_p + diff*1.0)/2, 1), 
                round((close_p + 4.0*atr + close_p + diff*1.618)/2, 1))
    return (0,0,0,0,0)

def generate_quant_option(symbol, price, t1, t2, t3, t4, t5, eq_sl, df_h, df_l, df_c, direction="Bullish"):
    if "^NSE" in symbol or symbol in ["NIFTY", "BANKNIFTY"]:
        dte = get_index_dte(symbol)
        step = 100 if "BANK" in symbol else 50
        vol = 0.14 
    else:
        dte = 15 
        step = 100 if price > 5000 else (50 if price > 2000 else (20 if price > 1000 else (10 if price > 500 else 5)))
        try:
            vol = math.sqrt((1.0 / (4.0 * math.log(2.0))) * ((np.log(df_h/df_l)**2).tail(10).mean())) * math.sqrt(252)
            if math.isnan(vol) or vol == 0: vol = np.log(df_c/df_c.shift(1)).tail(10).std() * math.sqrt(252)
            if math.isnan(vol) or vol == 0: vol = 0.2
        except: vol = 0.2
    
    atm = int(round(price / step) * step)
    opt_type = "CE" if direction == "Bullish" else "PE"
    c_prem = black_scholes(price, atm, dte/365.0, 0.07, vol, opt_type)
    return (f"{atm} {opt_type}", c_prem, round(black_scholes(t1, atm, dte/365.0, 0.07, vol, opt_type), 1), 
            round(black_scholes(t2, atm, dte/365.0, 0.07, vol, opt_type), 1), round(black_scholes(t3, atm, dte/365.0, 0.07, vol, opt_type), 1), 
            round(black_scholes(t4, atm, dte/365.0, 0.07, vol, opt_type), 1), round(black_scholes(t5, atm, dte/365.0, 0.07, vol, opt_type), 1), 
            max(5.0, round(black_scholes(eq_sl, atm, dte/365.0, 0.07, vol, opt_type), 1)))

def check_structure_hh_hl(df_h, df_l):
    if len(df_h) < 20: return True
    return (df_h.iloc[-10:].max() >= df_h.iloc[-20:-10].max()) and (df_l.iloc[-10:].min() >= df_l.iloc[-20:-10].min())

def check_bullish_divergence(closes, rsi):
    try:
        if len(closes) < 30: return False
        w1_c, w2_c = closes.iloc[-25:-10], closes.iloc[-10:]
        p1, p2 = w1_c.min(), w2_c.min()
        r1, r2 = rsi.loc[w1_c.idxmin()], rsi.loc[w2_c.idxmin()]
        if (p2 < p1 and r2 > r1) or (p2 > p1 and r2 < r1): return True
    except: pass
    return False

def check_ttm_squeeze(df_c, df_h, df_l, period=20):
    try:
        if len(df_c) < period: return False, False
        sma = df_c.rolling(window=period).mean()
        std = df_c.rolling(window=period).std()
        ema = df_c.ewm(span=period, adjust=False).mean()
        atr = pd.concat([df_h - df_l, (df_h - df_c.shift(1)).abs(), (df_l - df_c.shift(1)).abs()], axis=1).max(axis=1).rolling(window=period).mean()
        
        sqz_series = ((sma + 2*std) < (ema + 1.5*atr)) & ((sma - 2*std) > (ema - 1.5*atr))
        return bool(sqz_series.iloc[-1]), bool(sqz_series.iloc[-5:-1].any() and not sqz_series.iloc[-1])
    except: return False, False

def get_index_options_ideas():
    indices = {'^NSEI': 'NIFTY 50', '^NSEBANK': 'BANK NIFTY'}
    results = []
    for ticker, name in indices.items():
        try:
            data = yf.download(ticker, period="5d", interval="5m", progress=False, threads=False)
            if data.empty: continue
            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
            
            df_c, df_h, df_l = data['Close'].dropna(), data['High'].dropna(), data['Low'].dropna()
            if df_c.empty: continue
            
            close_p = float(df_c.iloc[-1])
            ema_20_5m = float(df_c.ewm(span=20).mean().iloc[-1])
            atr_5m = float(pd.concat([df_h - df_l, (df_h - df_c.shift(1)).abs(), (df_l - df_c.shift(1)).abs()], axis=1).max(axis=1).ewm(alpha=1/14).mean().iloc[-1])
            
            delta = df_c.diff()
            rsi_val = float((100 - (100 / (1 + ((delta.where(delta > 0, 0)).rolling(14).mean() / (-delta.where(delta < 0, 0)).rolling(14).mean())))).iloc[-1])
            
            direction = "Bullish" if close_p > ema_20_5m else "Bearish"
            t1, t2, t3, t4, t5 = round(close_p + 0.8*atr_5m, 1), round(close_p + 1.6*atr_5m, 1), round(close_p + 2.4*atr_5m, 1), round(close_p + 3.2*atr_5m, 1), round(close_p + 4.0*atr_5m, 1)
            if direction == "Bearish": t1, t2, t3, t4, t5 = round(close_p - 0.8*atr_5m, 1), round(close_p - 1.6*atr_5m, 1), round(close_p - 2.4*atr_5m, 1), round(close_p - 3.2*atr_5m, 1), round(close_p - 4.0*atr_5m, 1)
            eq_sl = round(close_p - 1.0*atr_5m, 1) if direction == "Bullish" else round(close_p + 1.0*atr_5m, 1)
            
            opt, prem, pt1, pt2, pt3, pt4, pt5, opt_sl = generate_quant_option(ticker, close_p, t1, t2, t3, t4, t5, eq_sl, df_h, df_l, df_c, direction)
            results.append({
                'Stock': f"{name} ({'Call' if direction == 'Bullish' else 'Put'})", 'RawStock': "NIFTY" if "NIFTY 50" in name else "BANKNIFTY", 
                'Horizon': 'Intraday', 'Entry': round(close_p, 2), 'RSI': round(rsi_val, 1), 'EqSL': eq_sl,
                'EqT1': t1, 'EqT2': t2, 'EqT3': t3, 'EqT4': t4, 'EqT5': t5,
                'Opt': opt, 'Prem': prem, 'PT1': pt1, 'PT2': pt2, 'PT3': pt3, 'PT4': pt4, 'PT5': pt5, 'OptSL': opt_sl, 'Score': 10, 'Tag': 'Index 5m Scalp'
            })
        except Exception: pass
    return pd.DataFrame(results)

def generate_tabular_markdown(df_stocks, df_index, title, filename, regime="Neutral", include_index=False):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(f"> **Market Regime Filter:** {regime} | **System:** 1800+ Mega Universe\n\n")
        if df_stocks.empty and df_index.empty:
            f.write("*Market conditions did not trigger any quantitative setups meeting institutional gates for this timeframe.*\n")
            return
        if include_index and not df_index.empty:
            f.write("## 👑 Index Options (5M Scalps)\n\n")
            f.write("| # | Index Signal | Price | Option | Buy Above | Targets | SL |\n")
            f.write("| :--- | :--- | :---: | :---: | :---: | :---: | :---: |\n")
            for idx, r in df_index.reset_index().iterrows():
                tgts = f"T1: ₹{r['PT1']}<br>T2: ₹{r['PT2']}<br>T3: ₹{r['PT3']}<br>T4: ₹{r['PT4']}<br>T5: ₹{r['PT5']}+"
                f.write(f"| {idx+1} | **{r['Stock']}** | ₹{r['Entry']} | **{r['Opt']}** | **₹{r['Prem']}** | {tgts} | ₹{r['OptSL']} |\n")
            f.write("\n---\n\n")
        if not df_stocks.empty:
            f.write("## 📊 Validated Setups & Options\n\n")
            f.write("| # | Stock | Setup Type | Buy Above | Score | Qty | Risk | Execution Strategy & Targets |\n")
            f.write("| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |\n")
            for idx, r in df_stocks.reset_index().iterrows():
                badge = f"🔥 {r['Score']}/10"
                eq_block = f"<b>Equity Targets:</b> T1:₹{r['EqT1']} // T2:₹{r['EqT2']} // T3:₹{r['EqT3']}"
                if "N/A" not in str(r['Opt']) and str(r['Prem']) not in ["-", "nan"]:
                    strat_info = f"{eq_block}<br><b>Option:</b> {r['Opt']} (Buy > ₹{r['Prem']})<br><b>Opt Targets:</b> T1:₹{r['PT1']} // T2:₹{r['PT2']} // T3:₹{r['PT3']}"
                else: strat_info = f"<b>Mode:</b> Cash Equity Only<br>{eq_block}"
                
                f.write(f"| {idx+1} | **{r['Stock']}** | {r['Tag']} | **₹{r['Entry']}** | {badge} | {r['Qty']} | ₹{r['Risk']} | {strat_info} |\n")

def format_telegram_text(df_stocks, df_index, title, regime="Neutral"):
    msg = f"🚨 *{title}* 🚨\n"
    msg += f"🧭 Market Regime: *{regime}*\n\n"
    if not df_index.empty:
        msg += "👑 *INDEX OPTIONS SIGNALS*\n"
        for _, r in df_index.iterrows():
            idx_name = "NIFTY" if "NIFTY 50" in r['Stock'] else "BANKNIFTY"
            msg += f"*{idx_name} {r['Opt']}*\n"
            msg += f"⚡ Buy Above: {r['Prem']}\n"
            msg += f"🎯 TGT: T1:{r['PT1']} | T2:{r['PT2']} | T3:{r['PT3']}\n"
            msg += f"🛡️ SL: {r['OptSL']}\n\n"
            
    if not df_stocks.empty:
        msg += "📊 *TOP POSITION SIZED SETUPS*\n"
        for idx, r in df_stocks.head(25).reset_index().iterrows():
            stock_clean = r['Stock'].replace(" (↑)", "")
            msg += f"{idx+1}. *{stock_clean}* | *{r['Tag']}* (Score: *{r['Score']}/10*)\n"
            msg += f"   ⚡ *Buy Above: ₹{r['Entry']}* | SL: ₹{r['EqSL']}\n"
            msg += f"   🎯 TGT: T1:{r['EqT1']} | T2:{r['EqT2']} | T3:{r['EqT3']}\n"
            
            if "N/A" not in str(r['Opt']) and str(r['Prem']) not in ["-", "nan"]:
                msg += f"   🔹 *Option:* {r['Opt']} @ Buy > ₹{r['Prem']}\n"
            msg += f"   🔗 [TradingView](https://in.tradingview.com/chart/?symbol=NSE:{r['RawStock']})\n\n"
    return msg

def generate_ai_deep_dive(top_candidates):
    if not GEMINI_API_KEY or not top_candidates:
        with open("deep_dive_analysis.md", "w", encoding="utf-8") as f:
            f.write("# 🔬 Institutional Deep Dive Analysis\n\n*Pending Analysis: Waiting for active market setups.*")
        return

    print("🤖 Initiating Automated AI 14-Pillar Fundamental Analysis...")
    all_dossiers = []

    for candidate in top_candidates[:2]:
        sym, entry, eq_sl = candidate['RawStock'], candidate['Entry'], candidate['EqSL']
        t1, t2, t3, tag, score = candidate['EqT1'], candidate['EqT2'], candidate['EqT3'], candidate['Tag'], candidate['Score']
        
        try:
            info = yf.Ticker(f"{sym}.NS").info
            pe, fpe, pb, roe, de = info.get('trailingPE', 'N/A'), info.get('forwardPE', 'N/A'), info.get('priceToBook', 'N/A'), info.get('returnOnEquity', 'N/A'), info.get('debtToEquity', 'N/A')
            sector, industry = info.get('sector', 'N/A'), info.get('industry', 'N/A')
        except: pe, fpe, pb, roe, de, sector, industry = "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"

        prompt = f"""
You are an Elite Institutional Equity Research Analyst. Write a rigorous 14-section institutional research report on **{sym} (NSE: {sym})**.
Context: Setup Type: {tag} (Score: {score}/10) | Buy Trigger: ₹{entry} | SL: ₹{eq_sl} | Targets: ₹{t1}/₹{t2}/₹{t3} | Sector: {sector} | P/E: {pe}

Format EXACTLY as:
# Detailed Stock Analysis: {sym} (NSE: {sym})
---
### 1. Technical Analysis
### 2. Why Did the Stock Fall Earlier?
### 3. Has the Company Recovered?
### 4. Latest News & Business Developments
### 5. Fundamental Analysis
### 6. Shareholding Pattern
### 7. Quarterly & Annual Financial Performance
### 8. Five-Year Financial Trend
### 9. Valuation Summary
### 10. Key Risks
### 11. Key Growth Triggers
### 12. Final Scorecard
### 13. Final Investment View
### 14. Executive Summary
"""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
            res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60)
            if res.status_code == 200: all_dossiers.append(res.json()['candidates'][0]['content']['parts'][0]['text'])
        except Exception: pass

    with open("deep_dive_analysis.md", "w", encoding="utf-8") as f:
        f.write("\n\n---\n\n".join(all_dossiers) if all_dossiers else "# 🔬 Analysis Completed.")

def run():
    print("🚀 Starting Automated Master Quant Scanner...")
    maintenance_purge()
    
    is_github_action = os.environ.get("GITHUB_ACTIONS") == "true"
    is_manual = (not is_github_action) or (os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch")
    
    if is_github_action and not is_manual:
        if not is_market_open(): 
            print("🛑 Market is closed. Exiting.")
            return

    sess_title, sess_type = get_session_info()
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    
    is_options_window = now_ist.hour < 14 or (now_ist.hour == 14 and now_ist.minute <= 45)
    df_index = get_index_options_ideas() if (sess_type in ["Intraday", "Manual"] and is_options_window) else pd.DataFrame()
    
    nifty_df = yf.download("^NSEI", period="1y", interval="1d", progress=False)
    nifty_return_20d, nifty_regime = 0.0, "Neutral"
    if not nifty_df.empty:
        if isinstance(nifty_df.columns, pd.MultiIndex): nifty_df.columns = nifty_df.columns.get_level_values(0)
        nifty_closes = nifty_df['Close'].dropna()
        if len(nifty_closes) >= 50:
            nifty_return_20d = float(nifty_closes.iloc[-1] / nifty_closes.iloc[-20] - 1)
            n_ema20, n_ema50, n_close = float(nifty_closes.ewm(span=20).mean().iloc[-1]), float(nifty_closes.ewm(span=50).mean().iloc[-1]), float(nifty_closes.iloc[-1])
            if n_close > n_ema20 and n_ema20 > n_ema50: nifty_regime = "Bullish"
            elif n_close < n_ema50: nifty_regime = "Bearish"

    universe = get_complete_nse_universe()
    closes, highs, lows, volumes = download_in_chunks([f"{s}.NS" for s in universe], chunk_size=400)
    if closes.empty: return

    portfolio_file = "portfolio.csv"
    if os.path.exists(portfolio_file): pf = pd.read_csv(portfolio_file)
    else: pf = pd.DataFrame(columns=['Stock', 'RawStock', 'Entry', 'Qty', 'Current_SL', 'T1', 'T2', 'T3', 'Status'])
        
    trail_alerts = []
    if not pf.empty:
        for i, row in pf.iterrows():
            if row['Status'] != 'Active': continue
            sym = row['RawStock']
            ticker = f"{sym}.NS"
            if ticker in closes.columns:
                latest_p, curr_sl, entry_p, t1, t2 = float(closes[ticker].iloc[-1]), float(row['Current_SL']), float(row['Entry']), float(row['T1']), float(row['T2'])
                if latest_p < curr_sl:
                    pf.at[i, 'Status'] = 'Closed'
                    trail_alerts.append(f"🔴 *STOP OUT:* {sym} closed below SL (₹{curr_sl}).")
                elif latest_p >= t2 and curr_sl < t1:
                    pf.at[i, 'Current_SL'] = t1
                    trail_alerts.append(f"🟢 *TRAIL SL WIN:* {sym} hit T2! Moved SL to lock in profit at T1 (₹{t1}).")
                elif latest_p >= t1 and curr_sl < entry_p:
                    pf.at[i, 'Current_SL'] = entry_p
                    trail_alerts.append(f"🟡 *TRAIL SL RISK-FREE:* {sym} hit T1! Moved SL to Breakeven (₹{entry_p}).")
        pf.to_csv(portfolio_file, index=False)
        if trail_alerts: send_telegram_message("🔔 *ATR TRAILING STOP ENGINE*\n\n" + "\n".join(trail_alerts))

    ema_50_daily, ema_20_daily, ema_200_daily = closes.ewm(span=50).mean(), closes.ewm(span=20).mean(), closes.ewm(span=200).mean()
    vol_50d_avg_daily = volumes.rolling(50).mean()
    delta = closes.diff()
    gain, loss = (delta.where(delta > 0, 0)).rolling(14).mean(), (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi_daily = 100 - (100 / (1 + (gain / loss)))
    macd_daily = closes.ewm(span=12, adjust=False).mean() - closes.ewm(span=26, adjust=False).mean()
    macd_signal_daily = macd_daily.ewm(span=9, adjust=False).mean()
    atr_daily = pd.DataFrame(np.maximum((highs - lows).values, np.maximum((highs - closes.shift(1)).abs().values, (lows - closes.shift(1)).abs().values)), index=highs.index, columns=highs.columns).ewm(alpha=1/14).mean()
    ema_50_weekly = closes.resample('W').last().dropna(how='all').ewm(span=50).mean()

    valid_setups = []
    for ticker in closes.columns:
        symbol = ticker.replace(".NS", "")
        try:
            df_c, df_h, df_l = closes[ticker].dropna(), highs[ticker].dropna(), lows[ticker].dropna()
            if len(df_c) < 20: continue
            
            close_p, vol_today, vol_50_avg = float(df_c.iloc[-1]), float(volumes.iloc[-1][ticker]), float(vol_50d_avg_daily.iloc[-1][ticker])
            turnover_avg = close_p * vol_50_avg
            
            # 1. Base Liquidity Floor & Penny Stock Filter
            if close_p < 20 or turnover_avg < 15000000 or vol_50_avg < 50000: continue
            
            is_micro_tier = turnover_avg < 50000000 # Tier 2: Between 1.5 Cr and 5 Cr
            
            vol_vs = round(vol_today / vol_50_avg, 2) if vol_50_avg > 0 else 1.0
            
            # 2. ANTI-DUMP FILTER: Massive upper wick rejection on extreme volume
            daily_range = float(df_h.iloc[-1] - df_l.iloc[-1])
            prev_close = float(df_c.iloc[-2]) if len(df_c) > 1 else close_p
            if daily_range > 0:
                upper_wick_ratio = (float(df_h.iloc[-1]) - max(close_p, prev_close)) / daily_range
                if upper_wick_ratio > 0.5 and vol_vs > 2.0 and close_p < prev_close:
                    continue # Operator dump detected
                    
            # 3. ANTI-PUMP FILTER: Exhaustion chasing
            recent_10d_return = (close_p / float(df_c.iloc[-10])) - 1 if len(df_c) >= 10 else 0
            if recent_10d_return > 0.40 and vol_vs > 3.0 and close_p < float(df_h.iloc[-1]):
                continue # Exhausted parabolic pump
            
            rsi_val, macd_val, macd_sig = float(rsi_daily.iloc[-1][ticker]), float(macd_daily.iloc[-1][ticker]), float(macd_signal_daily.iloc[-1][ticker])
            d_ema, w_ema, atr = float(ema_50_daily.iloc[-1][ticker]), float(ema_50_weekly.iloc[-1][ticker]), float(atr_daily.iloc[-1][ticker])
            d_ema20, d_ema200 = float(ema_20_daily.iloc[-1][ticker]), float(ema_200_daily.iloc[-1][ticker]) if not pd.isna(ema_200_daily.iloc[-1][ticker]) else 0.0
            
            recent_vol_avg, recent_range_avg = float(volumes[ticker].tail(3).mean()), float((highs[ticker].tail(3) - lows[ticker].tail(3)).mean())
            recent_high = float(highs[ticker].tail(20).max())
            
            is_squeeze = (recent_vol_avg < vol_50_avg * 0.85) and (recent_range_avg < atr * 0.85)
            is_relative_strong = (float(df_c.iloc[-1] / df_c.iloc[-20] - 1) > nifty_return_20d) if len(df_c) >= 20 else False
            
            is_pre_breakout = (0.002 <= ((recent_high - close_p)/close_p) <= 0.035) and (close_p > d_ema20) and (vol_vs <= 1.25)
            is_200ma_retest = (d_ema200 > 0) and (abs(close_p - d_ema200)/d_ema200 <= 0.025) and (vol_vs <= 1.0) and (close_p >= d_ema200)
            is_swing_retest = (0.025 <= ((recent_high - close_p)/close_p) <= 0.15) and (0.0 <= ((close_p - d_ema20)/d_ema20) <= 0.04) and (vol_vs <= 1.0)
            
            recent_daily_high = float(df_h.iloc[-1])
            is_btst = (close_p >= 0.98 * recent_daily_high) and (close_p > prev_close) and (close_p > d_ema20) and (vol_vs >= 1.0) and (50 <= rsi_val <= 75)

            is_rsi_div = check_bullish_divergence(df_c, rsi_daily[ticker].dropna())
            sqz_on, sqz_fired = check_ttm_squeeze(df_c, df_h, df_l)

            if sqz_fired: hor, sl_m, tag = "Pre-Breakout", 1.0, "🔥 Squeeze Breakout"
            elif sqz_on and is_pre_breakout: hor, sl_m, tag = "Pre-Breakout", 1.0, "🗜️ TTM Squeeze Coil"
            elif is_pre_breakout: hor, sl_m, tag = "Pre-Breakout", 1.0, "💥 Pre-Breakout Coil"
            elif is_200ma_retest: hor, sl_m, tag = "Swing", 1.5, "🏦 200 MA Retest"
            elif is_swing_retest: hor, sl_m, tag = "Swing", 1.2, "🔄 Breakout Retest"
            elif is_btst: hor, sl_m, tag = "BTST", 1.0, "🌙 Strong Close BTST"
            elif vol_vs >= 1.5: hor, sl_m, tag = "Intraday", 0.8, "🚀 Volume Breakout"
            else: continue
            
            if is_rsi_div: tag += " (📉 +RSI Div)"

            if (close_p > d_ema and close_p > w_ema and check_structure_hh_hl(df_h, df_l)) and ((macd_val > macd_sig) if hor not in ["Pre-Breakout", "Swing"] else True) and (45 <= rsi_val <= 85) and (is_relative_strong if hor not in ["Pre-Breakout", "Swing"] else True):
                t1, t2, t3, t4, t5 = calculate_dynamic_targets(close_p, atr, df_h, df_l, "Bullish", is_squeeze)
                eq_sl = round(close_p - sl_m * atr, 1)
                
                if (close_p - eq_sl) <= 0: continue
                
                score = min(10, sum([
                    1 if close_p > d_ema else 0,
                    1 if close_p > w_ema else 0,
                    2 if 55 <= rsi_val <= 70 else (1 if 45 <= rsi_val <= 85 else 0),
                    1 if macd_val > macd_sig else 0,
                    1 if macd_val > 0 else 0,
                    1 if is_relative_strong else 0,
                    2 if sqz_on else (3 if sqz_fired else 0),
                    1 if is_rsi_div else 0
                ]))
                
                active_base_capital = BASE_CAPITAL_PER_TRADE * 0.5 if nifty_regime == "Bearish" else BASE_CAPITAL_PER_TRADE
                
                # Apply Micro-Tier Tag and Risk Penalty
                if is_micro_tier:
                    tag += " ⚠️[Micro-Risk]"
                    score = max(0, score - 1)
                    cash_qty = int((active_base_capital * 0.5) / close_p) # Half position sizing
                else:
                    if score >= 8 and hor not in ["Pre-Breakout", "Swing"]: 
                        tag += " (⭐ 2x Size)"
                        cash_qty = int((active_base_capital * HIGH_CONVICTION_MULTIPLIER) / close_p)
                    else:
                        cash_qty = int(active_base_capital / close_p)

                opt_info = generate_quant_option(symbol, close_p, t1, t2, t3, t4, t5, eq_sl, df_h, df_l, df_c, "Bullish") if symbol in STATIC_FNO else ("N/A (Cash)", "-", "-", "-", "-", "-", "-", "-")
                
                valid_setups.append({
                    'Stock': f"{symbol} (↑)", 'RawStock': symbol, 'Horizon': hor, 'Tag': tag, 'Entry': round(close_p, 2), 
                    'Qty': cash_qty, 'Risk': round(cash_qty * (close_p - eq_sl), 2), 'RSI': round(rsi_val,1), 'Vol vs 50d': vol_vs,
                    'EqSL': eq_sl, 'EqT1': t1, 'EqT2': t2, 'EqT3': t3, 'EqT4': t4, 'EqT5': t5, 
                    'Opt': opt_info[0], 'Prem': opt_info[1], 'PT1': opt_info[2], 'PT2': opt_info[3], 'PT3': opt_info[4], 'PT4': opt_info[5], 'PT5': opt_info[6], 'OptSL': opt_info[7], 'Score': score
                })
        except: continue

    df_all = pd.DataFrame(valid_setups).drop_duplicates(subset=['Stock']).sort_values(by=['Score', 'Vol vs 50d'], ascending=[False, False]) if valid_setups else pd.DataFrame()
    if not df_all.empty: df_all.to_csv("all_setups.csv", index=False)
    else: pd.DataFrame(columns=['Stock','RawStock','Horizon','Tag','Entry','Qty','Risk','RSI','Vol vs 50d','EqSL','EqT1','EqT2','EqT3','EqT4','EqT5','Opt','Prem','PT1','PT2','PT3','PT4','PT5','OptSL','Score']).to_csv("all_setups.csv", index=False)
    
    if not df_index.empty: df_index.to_csv("index_setups.csv", index=False)
    else: pd.DataFrame(columns=['Stock','RawStock','Horizon','Entry','RSI','EqSL','EqT1','EqT2','EqT3','EqT4','EqT5','Opt','Prem','PT1','PT2','PT3','PT4','PT5','OptSL','Score','Tag']).to_csv("index_setups.csv", index=False)

    df_pre = df_all[df_all['Horizon'] == 'Pre-Breakout'].sort_values(by=['Score', 'RSI'], ascending=[False, False]).head(25) if not df_all.empty else pd.DataFrame()
    df_intra = df_all[df_all['Horizon'] == 'Intraday'].sort_values(by=['Score', 'Vol vs 50d'], ascending=[False, False]).head(25) if not df_all.empty else pd.DataFrame()
    df_btst = df_all[df_all['Horizon'] == 'BTST'].sort_values(by=['Score', 'Vol vs 50d'], ascending=[False, False]).head(25) if not df_all.empty else pd.DataFrame()
    df_swing = df_all[df_all['Horizon'] == 'Swing'].sort_values(by=['Score', 'RSI'], ascending=[False, False]).head(25) if not df_all.empty else pd.DataFrame()

    generate_tabular_markdown(df_pre, pd.DataFrame(), f"💥 Soon to Breakout Report (Top 25) — {sess_title}", "prebreakout_report.md", nifty_regime, False)
    generate_tabular_markdown(df_intra, df_index, f"⚡ Intraday Report (Top 25) — {sess_title}", "intraday_report.md", nifty_regime, True)
    generate_tabular_markdown(df_btst, pd.DataFrame(), f"🌙 BTST Report (Top 25) — {sess_title}", "btst_report.md", nifty_regime, False)
    generate_tabular_markdown(df_swing, pd.DataFrame(), f"📈 Swing Trade Retest Report (Top 25) — {sess_title}", "swing_report.md", nifty_regime, False)

    if not df_all.empty:
        top_candidates = sorted(valid_setups, key=lambda x: (x['Score'], x['Horizon'] == 'Swing'), reverse=True)
        generate_ai_deep_dive(top_candidates)
    else: generate_ai_deep_dive([])

    if not df_pre.empty: 
        new_pre = get_new_alerts(df_pre.head(25), "PreBreakout")
        if not new_pre.empty: send_telegram_message(format_telegram_text(new_pre, pd.DataFrame(), f"💥 Soon to Breakout — {sess_title}", nifty_regime))
        
    if (not df_intra.empty or not df_index.empty) and (is_options_window or is_manual): 
        new_intra = get_new_alerts(df_intra.head(25), "Intraday")
        new_idx = get_new_alerts(df_index, "Index") if is_options_window else pd.DataFrame()
        if not new_intra.empty or not new_idx.empty:
            send_telegram_message(format_telegram_text(new_intra, new_idx, f"⚡ Intraday Report — {sess_title}", nifty_regime))
            
    if not df_btst.empty and (not is_options_window or is_manual): 
        new_btst = get_new_alerts(df_btst.head(25), "BTST")
        if not new_btst.empty: send_telegram_message(format_telegram_text(new_btst, pd.DataFrame(), f"🌙 BTST Report — {sess_title}", nifty_regime))
        
    if not df_swing.empty and (not is_options_window or is_manual): 
        new_swing = get_new_alerts(df_swing.head(25), "Swing")
        if not new_swing.empty: send_telegram_message(format_telegram_text(new_swing, pd.DataFrame(), f"📈 Swing Trade (Retest) Report — {sess_title}", nifty_regime))

if __name__ == "__main__":
    run()
