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
    return ("🌅 MORNING SCAN (09:15-09:45 IST)", "Intraday") if hour < 12 else ("🌙 PRE-CLOSE SCAN (15:15 IST)", "BTST")

def calculate_lorentzian_distance(current_rsi, current_vol_vs, ideal_rsi=70.0, ideal_vol=2.0):
    dist_rsi = math.log(1 + abs(current_rsi - ideal_rsi))
    dist_vol = math.log(1 + abs(current_vol_vs - ideal_vol))
    return round(dist_rsi + dist_vol, 2)

def black_scholes(S, K, T, r, sigma):
    if T <= 0 or sigma == 0: return max(0, S - K), 1.0 if S > K else 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    return round(S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d1 - sigma * math.sqrt(T)), 2), round(norm.cdf(d1), 2)

def generate_quant_option(price, df_h, df_l, df_c, dte=15):
    step = 100 if price > 5000 else (50 if price > 2000 else (20 if price > 1000 else (10 if price > 500 else 5)))
    atm = int(round(price / step) * step)
    try:
        vol = math.sqrt((1.0 / (4.0 * math.log(2.0))) * ((np.log(df_h/df_l)**2).tail(10).mean())) * math.sqrt(252)
        if math.isnan(vol) or vol == 0: vol = np.log(df_c/df_c.shift(1)).tail(10).std() * math.sqrt(252)
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
        # Critical speedup: Only fetch actual companies (EQ), ignore bonds, REITs, etc.
        if ' SERIES' in df.columns:
            df = df[df[' SERIES'].str.strip() == 'EQ']
        elif 'SERIES' in df.columns:
            df = df[df['SERIES'].str.strip() == 'EQ']
        return [f"{str(s).strip()}.NS" for s in df['SYMBOL'].tolist()]
    except: return ['RELIANCE.NS', 'SBIN.NS']

def get_index_options_ideas():
    ideas = []
    for name, symbol, step in [('NIFTY 50', '^NSEI', 50), ('BANK NIFTY', '^NSEBANK', 100)]:
        try:
            df = yf.download(symbol, period="1mo", interval="1d", progress=False, threads=False)
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

def generate_markdown(df_results, df_index, title, filename):
    md = f"# {title}\n\n"
    if not df_index.empty:
        md += "## 🏛️ Index Options\n"
        for _, r in df_index.iterrows():
            md += f"📌 **{r['Index']}** ({r['Bias']})\n"
            md += f"• Spot: ₹{r['Spot']} | Option: **{r['Opt']}**\n"
            md += f"• Targets: T1: ₹{r['T1']} | T2: ₹{r['T2']} | T3: ₹{r['T3']} | SL: ₹{r['SL']}\n\n"
        md += "---\n\n"

    for h_name, h_filter in [("⚡ Intraday Setups", "Intraday"), ("🌙 BTST Setups", "BTST"), ("📈 Swing Setups", "Swing")]:
        dff = df_results[df_results['Horizon'].str.contains(h_filter)] if not df_results.empty else pd.DataFrame()
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
    with open(filename, "w", encoding="utf-8") as f: f.write(md)

def run():
    sess_title, sess_type = get_session_info()
    df_index = get_index_options_ideas()
    fno_list = get_fno_symbols()
    tickers = get_all_nse_tickers()
    
    # ONE SINGLE MASSIVE DOWNLOAD - Let yfinance handle the threading optimally
    data = yf.download(tickers, period="3mo", interval="1d", progress=False, threads=True)
    if data.empty: return
    
    closes, highs, lows, volumes = data['Close'], data['High'], data['Low'], data['Volume']
    
    # -------------------------------------------------------------
    # PURE VECTORIZATION MATRIX MATH ON THE ENTIRE MARKET AT ONCE
    # -------------------------------------------------------------
    ema_50_all = closes.ewm(span=50).mean()
    vol_50d_avg_all = volumes.rolling(50).mean()
    
    # RSI Matrix
    delta = closes.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rsi_all = 100 - (100 / (1 + (gain / loss)))

    # MACD Matrix
    exp1 = closes.ewm(span=12, adjust=False).mean()
    exp2 = closes.ewm(span=26, adjust=False).mean()
    macd_all = exp1 - exp2
    macd_signal_all = macd_all.ewm(span=9, adjust=False).mean()
    
    # ATR Matrix
    hl = highs - lows
    hc = (highs - closes.shift(1)).abs()
    lc = (lows - closes.shift(1)).abs()
    tr = pd.DataFrame(np.maximum(hl.values, np.maximum(hc.values, lc.values)), index=hl.index, columns=hl.columns)
    atr_all = tr.ewm(alpha=1/14).mean()

    # Get only the very last row for all calculations
    last_close = closes.iloc[-1]
    last_high = highs.iloc[-1]
    last_low = lows.iloc[-1]
    last_vol = volumes.iloc[-1]
    last_vol_50 = vol_50d_avg_all.iloc[-1]
    last_rsi = rsi_all.iloc[-1]
    last_macd = macd_all.iloc[-1]
    last_macd_signal = macd_signal_all.iloc[-1]
    last_ema_50 = ema_50_all.iloc[-1]
    last_atr = atr_all.iloc[-1]

    res_strict, res_aggressive, res_budget = [], [], []

    # Extremely fast loop over the final scalar values
    for ticker in closes.columns:
        try:
            close_p = float(last_close[ticker])
            high_p = float(last_high[ticker])
            low_p = float(last_low[ticker])
            vol_today = float(last_vol[ticker])
            
            # Base filters
            if pd.isna(close_p) or close_p <= 0 or high_p == low_p or vol_today < 1000: continue
            
            vol_50_avg = float(last_vol_50[ticker])
            if pd.isna(vol_50_avg) or vol_50_avg <= 0: continue
            
            rsi_val = float(last_rsi[ticker])
            # 1. Hard Ceiling: Reject anything already in the extreme overbought zone
            if pd.isna(rsi_val) or rsi_val > 72.0: continue
            
            macd_val = float(last_macd[ticker])
            macd_sig = float(last_macd_signal[ticker])
            if macd_val < macd_sig: continue
            
            ema_50 = float(last_ema_50[ticker])
            passes_ema = close_p >= ema_50
            atr = float(last_atr[ticker])

            pos = round(((close_p - low_p) / (high_p - low_p)) * 100, 1)
            
            # 2. Correction Filter: Reject stocks closing in the bottom half of their daily candle
            if pos < 55.0: continue 

            vol_vs = round(vol_today / vol_50_avg, 2)

            if sess_type == "Intraday": hor = "⚡ Intraday" if vol_vs >= 1.3 else "📈 Swing"
            else: hor = "🌙 BTST" if vol_vs >= 1.2 else "📈 Swing"

            # 3. Sweet Spot Scoring: Only reward RSI if it is in the early momentum phase (55 to 68)
            base_score = (2 if 55 <= rsi_val <= 68 else 0) + (2 if vol_vs>=2 else 0)
            
            lorentzian_score = calculate_lorentzian_distance(rsi_val, vol_vs)
            if lorentzian_score > 1.5: base_score -= 1 
            elif lorentzian_score < 0.5: base_score += 1 

            symbol = ticker.replace(".NS", "")
            if symbol in fno_list:
                df_h, df_l, df_c = highs[ticker].dropna(), lows[ticker].dropna(), closes[ticker].dropna()
                opt, prem, delta, osl, ot1, ot2, ot3 = generate_quant_option(close_p, df_h, df_l, df_c)
            else:
                opt, prem, delta, osl, ot1, ot2, ot3 = "N/A (Cash)", "-", "-", "-", "-", "-", "-"
            
            record = {'Stock': symbol, 'Horizon': hor, 'Entry': round(close_p, 2), 'RSI': round(rsi_val,1), 'EqSL': round(close_p-1.5*atr,1), 'EqT1': round(close_p+1.5*atr,1), 'EqT2': round(close_p+3.0*atr,1), 'EqT3': round(close_p+4.5*atr,1), 'Opt': opt, 'Prem': prem, 'Delta': delta, 'OSL': osl, 'OT1': ot1, 'OT2': ot2, 'OT3': ot3}

            if passes_ema and base_score >= 2:
                rec_strict = record.copy()
                rec_strict['Score'] = base_score
                res_strict.append(rec_strict)
                if close_p < 500: res_budget.append(rec_strict)

            agg_score = base_score + 2
            if agg_score >= 2:
                rec_agg = record.copy()
                rec_agg['Score'] = agg_score
                res_aggressive.append(rec_agg)
        except: continue

    df_strict = pd.DataFrame(res_strict).sort_values(by=['Score', 'RSI'], ascending=[False, False]).head(25) if res_strict else pd.DataFrame()
    df_agg = pd.DataFrame(res_aggressive).sort_values(by=['Score', 'RSI'], ascending=[False, False]).head(25) if res_aggressive else pd.DataFrame()
    df_bud = pd.DataFrame(res_budget).sort_values(by=['Score', 'RSI'], ascending=[False, False]).head(25) if res_budget else pd.DataFrame()

    generate_markdown(df_strict, df_index, f"📊 Strict Quant Setups — {sess_title}", "breakoutsummary.md")
    generate_markdown(df_agg, df_index, f"🚀 Aggressive Quant Setups — {sess_title}", "aggressivesummary.md")
    generate_markdown(df_bud, df_index, f"💡 Budget Setups (< ₹500) — {sess_title}", "budgetsummary.md")

if __name__ == "__main__": run()
