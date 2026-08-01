import yfinance as yf
import pandas as pd
import numpy as np
import requests
import io
import datetime
import math
from scipy.stats import norm

def get_session_info():
    hour = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)).hour
    return ("🌅 MORNING STRICT SCAN (09:15-09:45 IST)", "Intraday") if hour < 12 else ("🌙 PRE-CLOSE STRICT SCAN (15:15 IST)", "BTST")

def black_scholes(S, K, T, r, sigma):
    if T <= 0 or sigma == 0: return max(0, S - K), 1.0 if S > K else 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    return round(S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d1 - sigma * math.sqrt(T)), 2), round(norm.cdf(d1), 2)

def generate_quant_option(price, df, dte=15):
    step = 100 if price > 5000 else (50 if price > 2000 else (20 if price > 1000 else (10 if price > 500 else 5)))
    atm = int(round(price / step) * step)
    vol = math.sqrt((1.0 / (4.0 * math.log(2.0))) * ((np.log(df['High']/df['Low'])**2).tail(10).mean())) * math.sqrt(252)
    if math.isnan(vol) or vol == 0: vol = np.log(df['Close']/df['Close'].shift(1)).tail(10).std() * math.sqrt(252)
    prem, delta = black_scholes(price, atm, dte/365.0, 0.07, vol)
    return f"{atm} CE", prem, delta, round(price*0.985, 1), round(price*1.02, 1), round(price*1.04, 1), round(price*1.06, 1)

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
    
    try:
        df = pd.read_csv(io.StringIO(requests.get("https://archives.nseindia.com/content/indices/ind_nifty500list.csv", headers={'User-Agent': 'Mozilla/5.0'}, timeout=10).text))
        tickers = [f"{s}.NS" for s in df['Symbol'].tolist()]
    except: tickers = ['RELIANCE.NS', 'SBIN.NS']
    
    data = yf.download(tickers, period="6mo", interval="1d", group_by='ticker', progress=False)
    results = []

    for ticker in tickers:
        try:
            df = data[ticker].dropna() if len(tickers) > 1 else data.dropna()
            if len(df) < 60: continue
            close_p = float(df['Close'].iloc[-1])
            if close_p < float(df['Close'].ewm(span=50).mean().iloc[-1]): continue
            
            high_p, low_p = float(df['High'].iloc[-1]), float(df['Low'].iloc[-1])
            pos = round(((close_p - low_p) / (high_p - low_p)) * 100, 1) if high_p != low_p else 50.0
            vol_vs = round(float(df['Volume'].iloc[-1]) / float(df['Volume'].rolling(50).mean().iloc[-1]), 2)
            
            df['RSI'] = 100 - (100 / (1 + (df['Close'].diff().where(df['Close'].diff()>0,0).rolling(14).mean() / -df['Close'].diff().where(df['Close'].diff()<0,0).rolling(14).mean())))
            rsi = float(df['RSI'].iloc[-1])

            if sess_type == "Intraday": hor = "⚡ Intraday" if vol_vs >= 1.3 or pos >= 70 else "📈 Swing"
            else: hor = "🌙 BTST" if pos >= 75 and vol_vs >= 1.2 else "📈 Swing"

            score = (2 if rsi>=60 else 0)+(2 if vol_vs>=2 else 0)
            if score < 2: continue # Basic Conviction Filter

            hl, hc, lc = df['High']-df['Low'], np.abs(df['High']-df['Close'].shift()), np.abs(df['Low']-df['Close'].shift())
            atr = float(pd.concat([hl, hc, lc], axis=1).max(axis=1).ewm(alpha=1/14).mean().iloc[-1])
            opt, prem, delta, osl, ot1, ot2, ot3 = generate_quant_option(close_p, df)
            
            results.append({'Stock': ticker.replace(".NS", ""), 'Horizon': hor, 'Entry': round(close_p, 2), 'RSI': round(rsi,1), 'Score': score, 'EqSL': round(close_p-1.5*atr,1), 'EqT1': round(close_p+1.5*atr,1), 'EqT2': round(close_p+3.0*atr,1), 'EqT3': round(close_p+4.5*atr,1), 'Opt': opt, 'Prem': prem, 'Delta': delta, 'OSL': osl, 'OT1': ot1, 'OT2': ot2, 'OT3': ot3})
        except: continue

    # STRICTLY CAP AT TOP 20
    df_r = pd.DataFrame(results).sort_values(by=['Score', 'RSI'], ascending=[False, False]).head(20) if results else pd.DataFrame()
    
    md = f"# 📊 Top 20 Quant Setups — {sess_title}\n\n"
    
    if not df_index.empty:
        df_index.insert(0, 'S.No', range(1, len(df_index) + 1))
        md += "## 🏛️ Index Options (Nifty 50 & Bank Nifty CEs/PEs)\n| S.No | Index | Spot | Bias | Option | Spot SL | Spot T1 | Spot T2 | Spot T3 |\n|---|---|---|---|---|---|---|---|---|\n"
        for _, r in df_index.iterrows(): md += f"| {r['S.No']} | **{r['Index']}** | ₹{r['Spot']} | {r['Bias']} | **{r['Opt']}** | ₹{r['SL']} | ₹{r['T1']} | ₹{r['T2']} | ₹{r['T3']} |\n"
        md += "\n---\n"

    for h_name, h_filter in [("Intraday (Morning Only)", "Intraday"), ("BTST (Pre-Close Only)", "BTST"), ("Positional Swing", "Swing")]:
        dff = df_r[df_r['Horizon'].str.contains(h_filter)] if not df_r.empty else pd.DataFrame()
        if not dff.empty:
            dff.insert(0, 'S.No', range(1, len(dff) + 1)) # Re-Index perfectly for Markdown
            md += f"## {h_name}\n| S.No | Stock | Entry | RSI | Eq SL | Target 1 | Target 2 | Target 3 | CE Option | Est Prem | Delta | Opt SL | Spot T1 | Spot T2 | Spot T3 |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
            for _, r in dff.iterrows(): md += f"| {r['S.No']} | **{r['Stock']}** | ₹{r['Entry']} | {r['RSI']} | ₹{r['EqSL']} | ₹{r['EqT1']} | ₹{r['EqT2']} | ₹{r['EqT3']} | **{r['Opt']}** | ₹{r['Prem']} | {r['Delta']} | ₹{r['OSL']} | ₹{r['OT1']} | ₹{r['OT2']} | ₹{r['OT3']} |\n"
            md += "\n---\n"
    with open("breakoutsummary.md", "w") as f: f.write(md)

if __name__ == "__main__": run()
