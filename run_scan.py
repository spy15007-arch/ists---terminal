import yfinance as yf
import pandas as pd
import numpy as np
import requests
import io
import datetime
import math
import time
from scipy.stats import norm

def get_session_info():
    hour = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)).hour
    return ("🌅 MORNING STRICT SCAN (09:15-09:45 IST)", "Intraday") if hour < 12 else ("🌙 PRE-CLOSE STRICT SCAN (15:15 IST)", "BTST")

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(series):
    exp1 = series.ewm(span=12, adjust=False).mean()
    exp2 = series.ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

def calculate_lorentzian_distance(current_rsi, current_vol_vs, ideal_rsi=70.0, ideal_vol=2.0):
    dist_rsi = math.log(1 + abs(current_rsi - ideal_rsi))
    dist_vol = math.log(1 + abs(current_vol_vs - ideal_vol))
    return round(dist_rsi + dist_vol, 2)

def black_scholes(S, K, T, r, sigma):
    if T <= 0 or sigma == 0: return max(0, S - K), 1.0 if S > K else 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    return round(S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d1 - sigma * math.sqrt(T)), 2), round(norm.cdf(d1), 2)

def generate_quant_option(price, df, dte=15):
    step = 100 if price > 5000 else (50 if price > 2000 else (20 if price > 1000 else (10 if price > 500 else 5)))
    atm = int(round(price / step) * step)
    try:
        vol = math.sqrt((1.0 / (4.0 * math.log(2.0))) * ((np.log(df['High']/df['Low'])**2).tail(10).mean())) * math.sqrt(252)
        if math.isnan(vol) or vol == 0: vol = np.log(df['Close']/df['Close'].shift(1)).tail(10).std() * math.sqrt(252)
        if math.isnan(vol) or vol == 0: vol = 0.2
    except: vol = 0.2
    prem, delta = black_scholes(price, atm, dte/365.0, 0.07, vol)
    return f"{atm} CE", prem, delta, round(price*0.985, 1), round(price*1.02, 1), round(price*1.04, 1), round(price*1.06, 1)

def get_fno_symbols():
    try:
        url = "https://archives.nseindia.com/content/fo/fo_mktlots.csv"
        df = pd.read_csv(url)
        cols = [c.strip() for c in df.columns]
        df.columns = cols
        if 'SYMBOL' in df.columns: return [str(x).strip().upper() for x in df['SYMBOL'].tolist()]
    except: pass
    return ["RELIANCE", "SBIN", "HDFCBANK", "ICICIBANK", "INFY"]

def get_all_nse_tickers():
    try:
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        df = pd.read_csv(io.StringIO(response.text))
        return [f"{str(s).strip()}.NS" for s in df['SYMBOL'].tolist()]
    except: return ['RELIANCE.NS', 'SBIN.NS', 'HDFCBANK.NS', 'ICICIBANK.NS']

def get_index_options_ideas():
    ideas = []
    for name, symbol, step in [('NIFTY 50', '^NSEI', 50), ('BANK NIFTY', '^NSEBANK', 100)]:
        try:
            df = yf.download(symbol, period="1mo", interval="1d", progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if df.empty: continue
            close_p = float(df['Close'].iloc[-1])
            ema_20 = float(df['Close'].ewm(span=20).mean().iloc[-1])
            atm_strike = int(round(close_p / step) * step)
            
            hl_log_sq = (np.log(df['High'] / df['Low']) ** 2).tail(10)
            vol = math.sqrt((1.0 / (4.0 * math.log(2.0))) * hl_log_sq.mean()) * math.sqrt(252)
            if math.isnan(vol) or vol == 0:
                df['Log_Ret'] = np.log(df['Close'] / df['Close'].shift(1))
                vol = df['Log_Ret'].tail(10).std() * math.sqrt(252)

            if close_p >= ema_20:
                ideas.append({'Index': name, 'Spot': round(close_p, 2), 'Bias': "🟢 BULLISH", 'Opt': f"BUY {atm_strike} CE", 'SL': round(close_p*0.995, 1), 'T1': round(close_p*1.005, 1), 'T2': round(close_p*1.010, 1), 'T3': round(close_p*1.015, 1)})
            else:
                ideas.append({'Index': name, 'Spot': round(close_p, 2), 'Bias': "🔴 BEARISH", 'Opt': f"BUY {atm_strike} PE", 'SL': round(close_p*1.005, 1), 'T1': round(close_p*0.995, 1), 'T2': round(close_p*0.990, 1), 'T3': round(close_p*0.985, 1)})
        except: continue
    return pd.DataFrame(ideas)

def run():
    sess_title, sess_type = get_session_info()
    df_index = get_index_options_ideas()
    fno_list = get_fno_symbols()
    tickers = get_all_nse_tickers()
    
    results = []
    chunk_size = 400
    
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        try:
            data = yf.download(" ".join(chunk), period="3mo", interval="1d", progress=False, threads=True)
            if data.empty: continue
            
            closes = data['Close']
            highs = data['High']
            lows = data['Low']
            volumes = data['Volume']

            for ticker in chunk:
                try:
                    if ticker not in closes.columns: continue
                    df_c = closes[ticker].dropna()
                    if len(df_c) < 50: continue
                    
                    df_h, df_l, df_v = highs[ticker].dropna(), lows[ticker].dropna(), volumes[ticker].dropna()
                    
                    close_p = float(df_c.iloc[-1])
                    high_p, low_p = float(df_h.iloc[-1]), float(df_l.iloc[-1])
                    if high_p == low_p or close_p <= 0: continue
                    
                    # Strict EMA 50 Filter
                    ema_50 = float(df_c.ewm(span=50).mean().iloc[-1])
                    if close_p < ema_50: continue
                    
                    vol_today = float(df_v.iloc[-1])
                    vol_50d_avg = float(df_v.rolling(50).mean().iloc[-1])
                    if vol_50d_avg <= 0: continue
                    
                    rsi_series = calculate_rsi(df_c)
                    rsi_val = float(rsi_series.iloc[-1])
                    if math.isnan(rsi_val) or rsi_val > 80: continue

                    macd, macd_signal = calculate_macd(df_c)
                    if macd.iloc[-1] < macd_signal.iloc[-1]: continue

                    pos = round(((close_p - low_p) / (high_p - low_p)) * 100, 1)
                    vol_vs = round(vol_today / vol_50d_avg, 2)

                    if sess_type == "Intraday": hor = "⚡ Intraday" if vol_vs >= 1.3 or pos >= 70 else "📈 Swing"
                    else: hor = "🌙 BTST" if pos >= 75 and vol_vs >= 1.2 else "📈 Swing"

                    score = (2 if rsi_val>=60 else 0) + (2 if vol_vs>=2 else 0)
                    lorentzian_score = calculate_lorentzian_distance(rsi_val, vol_vs)
                    if lorentzian_score > 1.5: score -= 1 
                    elif lorentzian_score < 0.5: score += 1 

                    if score < 2: continue 

                    hl, hc, lc = df_h - df_l, np.abs(df_h - df_c.shift()), np.abs(df_l - df_c.shift())
                    atr = float(pd.concat([hl, hc, lc], axis=1).max(axis=1).ewm(alpha=1/14).mean().iloc[-1])
                    
                    symbol = ticker.replace(".NS", "")
                    df_temp = pd.DataFrame({'High': df_h, 'Low': df_l, 'Close': df_c})
                    if symbol in fno_list:
                        opt, prem, delta, osl, ot1, ot2, ot3 = generate_quant_option(close_p, df_temp)
                    else:
                        opt, prem, delta, osl, ot1, ot2, ot3 = "N/A (Cash)", "-", "-", "-", "-", "-", "-"
                    
                    results.append({'Stock': symbol, 'Horizon': hor, 'Entry': round(close_p, 2), 'RSI': round(rsi_val,1), 'Score': score, 'EqSL': round(close_p-1.5*atr,1), 'EqT1': round(close_p+1.5*atr,1), 'EqT2': round(close_p+3.0*atr,1), 'EqT3': round(close_p+4.5*atr,1), 'Opt': opt, 'Prem': prem, 'Delta': delta, 'OSL': osl, 'OT1': ot1, 'OT2': ot2, 'OT3': ot3})
                except: continue
        except: continue

    df_r = pd.DataFrame(results).sort_values(by=['Score', 'RSI'], ascending=[False, False]).head(25) if results else pd.DataFrame()
    
    md = f"# 📊 Strict Quant Setups (All NSE) — {sess_title}\n\n"
    
    if not df_index.empty:
        md += "## 🏛️ Index Options\n"
        for _, r in df_index.iterrows():
            md += f"📌 **{r['Index']}** ({r['Bias']})\n"
            md += f"• Spot: ₹{r['Spot']} | Option: **{r['Opt']}**\n"
            md += f"• Targets: T1: ₹{r['T1']} | T2: ₹{r['T2']} | T3: ₹{r['T3']} | SL: ₹{r['SL']}\n\n"
        md += "---\n\n"

    for h_name, h_filter in [("⚡ Intraday Setups", "Intraday"), ("🌙 BTST Setups", "BTST"), ("📈 Swing Setups", "Swing")]:
        dff = df_r[df_r['Horizon'].str.contains(h_filter)] if not df_r.empty else pd.DataFrame()
        if not dff.empty:
            md += f"## {h_name}\n\n"
            for _, r in dff.iterrows():
                prem_disp = f"₹{r['Prem']}" if str(r['Prem']) != '-' else '-'
                md += f"🟢 **{r['Stock']}** (Score: {r['Score']} | RSI: {r['RSI']})\n"
                md += f"• **Entry:** ₹{r['Entry']} | **Eq SL:** ₹{r['EqSL']}\n"
                md += f"• **Targets:** T1: ₹{r['EqT1']} | T2: ₹{r['EqT2']} | T3: ₹{r['EqT3']}\n"
                if str(r['Opt']) != 'N/A (Cash)':
                    md += f"• **Option:** {r['Opt']} (Prem: {prem_disp} | Delta: {r['Delta']})\n"
                md += "\n"
            md += "---\n\n"

    with open("breakoutsummary.md", "w", encoding="utf-8") as f: f.write(md)

if __name__ == "__main__": run()
