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
    return ("🌅 MORNING (09:15-09:45 IST)", "Intraday") if hour < 12 else ("🌙 PRE-CLOSE (15:15 IST)", "BTST")

def calculate_lorentzian_distance(current_rsi, current_vol_vs, ideal_rsi=70.0, ideal_vol=2.0):
    dist_rsi = math.log(1 + abs(current_rsi - ideal_rsi))
    dist_vol = math.log(1 + abs(current_vol_vs - ideal_vol))
    return round(dist_rsi + dist_vol, 2)

def black_scholes(S, K, T, r, sigma):
    if T <= 0 or sigma == 0: return max(0, S - K), max(0, K - S), 1.0 if S > K else 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    call_prem = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    put_prem = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    return round(call_prem, 2), round(put_prem, 2), round(norm.cdf(d1), 2)

def generate_quant_option(price, t1, t2, t3, df_h, df_l, df_c):
    # Stock options default to monthly expiry estimates (~15-20 DTE average assumption)
    dte = 15 
    step = 100 if price > 5000 else (50 if price > 2000 else (20 if price > 1000 else (10 if price > 500 else 5)))
    atm = int(round(price / step) * step)
    try:
        vol = math.sqrt((1.0 / (4.0 * math.log(2.0))) * ((np.log(df_h/df_l)**2).tail(10).mean())) * math.sqrt(252)
        if math.isnan(vol) or vol == 0: vol = np.log(df_c/df_c.shift(1)).tail(10).std() * math.sqrt(252)
        if math.isnan(vol) or vol == 0: vol = 0.2
    except: vol = 0.2
    
    call_prem, _, _ = black_scholes(price, atm, dte/365.0, 0.07, vol)
    pt1, _, _ = black_scholes(t1, atm, dte/365.0, 0.07, vol)
    pt2, _, _ = black_scholes(t2, atm, dte/365.0, 0.07, vol)
    pt3, _, _ = black_scholes(t3, atm, dte/365.0, 0.07, vol)
    
    return f"{atm} CE [Monthly]", call_prem, round(pt1, 1), round(pt2, 1), round(pt3, 1)

def get_fno_symbols():
    # Hardcoded complete FNO list to bypass NSE server blocking automated downloads
    static_fno = ["AARTIIND", "ABB", "ABBOTINDIA", "ABCAPITAL", "ABFRL", "ACC", "ADANIENT", "ADANIPORTS", "ALKEM", "AMBUJACEM", "APOLLOHOSP", "APOLLOTYRE", "ASHOKLEY", "ASIANPAINT", "ASTRAL", "ATUL", "AUBANK", "AUROPHARMA", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BALKRISIND", "BALRAMCHIN", "BANDHANBNK", "BANKBARODA", "BATAINDIA", "BEL", "BERGEPAINT", "BHARATFORG", "BHARTIARTL", "BHEL", "BIOCON", "BOSCHLTD", "BPCL", "BRITANNIA", "CANBK", "CANFINHOME", "CHAMBLFERT", "CHOLAFIN", "CIPLA", "COALINDIA", "COFORGE", "COLPAL", "CONCOR", "COROMANDEL", "CROMPTON", "CUB", "CUMMINSIND", "DABUR", "DALBHARAT", "DEEPAKNTR", "DIVISLAB", "DIXON", "DLF", "DRREDDY", "EICHERMOT", "ESCORTS", "EXIDEIND", "FEDERALBNK", "GAIL", "GLENMARK", "GMRINFRA", "GNFC", "GODREJCP", "GODREJPROP", "GRANULES", "GRASIM", "GUJGASLTD", "HAL", "HAVELLS", "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDCOPPER", "HINDPETRO", "HINDUNILVR", "ICICIBANK", "ICICIGI", "ICICIPRULI", "IDEA", "IDFCFIRSTB", "IEX", "IGL", "INDHOTEL", "INDIACEM", "INDIAMART", "INDIGO", "INDUSINDBK", "INFY", "IOC", "IPCALAB", "IRCTC", "ITC", "JINDALSTEL", "JSWSTEEL", "JUBLFOOD", "KOTAKBANK", "LALPATHLAB", "LAURUSLABS", "LICHSGFIN", "LT", "LTIM", "LTTS", "LUPIN", "M&M", "M&MFIN", "MANAPPURAM", "MARICO", "MARUTI", "MCDOWELL-N", "MCX", "METROPOLIS", "MFSL", "MGL", "MOTHERSON", "MPHASIS", "MRF", "MUTHOOTFIN", "NATIONALUM", "NAUKRI", "NAVINFLUOR", "NESTLEIND", "NMDC", "NTPC", "OBEROIRLTY", "OFSS", "ONGC", "PAGEIND", "PEL", "PETRONET", "PFC", "PIDILITIND", "PIIND", "PNB", "POLYCAB", "POWERGRID", "PVRINOX", "RAMCOCEM", "RBLBANK", "RECLTD", "RELIANCE", "SAIL", "SBICARD", "SBILIFE", "SBIN", "SHREECEM", "SHRIRAMFIN", "SIEMENS", "SRF", "SUNPHARMA", "SUNTV", "SYNGENE", "TATACHEM", "TATACOMM", "TATACONSUM", "TATAMOTORS", "TATAPOWER", "TATASTEEL", "TCS", "TECHM", "TITAN", "TORNTPHARM", "TRENT", "TVSMOTOR", "UBL", "ULTRACEMCO", "UPL", "VEDL", "VOLTAS", "WIPRO", "ZEEL", "ZYDUSLIFE"]
    try:
        url = "https://archives.nseindia.com/content/fo/fo_mktlots.csv"
        df = pd.read_csv(url, timeout=5)
        cols = [c.strip() for c in df.columns]
        df.columns = cols
        if 'SYMBOL' in df.columns: return [str(x).strip().upper() for x in df['SYMBOL'].tolist()]
    except: pass
    return static_fno

def get_all_nse_tickers():
    try:
        url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        df = pd.read_csv(io.StringIO(response.text))
        return [f"{str(s).strip()}.NS" for s in df['Symbol'].tolist()]
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

            # Generate targets
            if close_p >= ema_20:
                t1, t2, t3 = round(close_p*1.005, 1), round(close_p*1.010, 1), round(close_p*1.015, 1)
                bias = "🟢 BULL"
                opt_type = "CE"
            else:
                t1, t2, t3 = round(close_p*0.995, 1), round(close_p*0.990, 1), round(close_p*0.985, 1)
                bias = "🔴 BEAR"
                opt_type = "PE"
                
            sl = round(close_p*0.995, 1) if bias == "🟢 BULL" else round(close_p*1.005, 1)

            # Calculate for CURRENT WEEK (Approx 3 DTE)
            c_call, c_put, _ = black_scholes(close_p, atm_strike, 3/365.0, 0.07, vol)
            c_pt1_call, c_pt1_put, _ = black_scholes(t1, atm_strike, 3/365.0, 0.07, vol)
            c_pt2_call, c_pt2_put, _ = black_scholes(t2, atm_strike, 3/365.0, 0.07, vol)
            c_pt3_call, c_pt3_put, _ = black_scholes(t3, atm_strike, 3/365.0, 0.07, vol)
            
            c_prem = c_call if opt_type == "CE" else c_put
            c_pt1 = c_pt1_call if opt_type == "CE" else c_pt1_put
            c_pt2 = c_pt2_call if opt_type == "CE" else c_pt2_put
            c_pt3 = c_pt3_call if opt_type == "CE" else c_pt3_put

            ideas.append({'Index': f"{name} (Curr Wk)", 'Spot': round(close_p, 2), 'Bias': bias, 'Opt': f"{atm_strike} {opt_type} [CW]", 'Prem': c_prem, 'PT1': round(c_pt1,1), 'PT2': round(c_pt2,1), 'PT3': round(c_pt3,1), 'SL': sl, 'T1': t1, 'T2': t2, 'T3': t3})

            # Calculate for NEXT WEEK (Approx 10 DTE)
            n_call, n_put, _ = black_scholes(close_p, atm_strike, 10/365.0, 0.07, vol)
            n_pt1_call, n_pt1_put, _ = black_scholes(t1, atm_strike, 10/365.0, 0.07, vol)
            n_pt2_call, n_pt2_put, _ = black_scholes(t2, atm_strike, 10/365.0, 0.07, vol)
            n_pt3_call, n_pt3_put, _ = black_scholes(t3, atm_strike, 10/365.0, 0.07, vol)
            
            n_prem = n_call if opt_type == "CE" else n_put
            n_pt1 = n_pt1_call if opt_type == "CE" else n_pt1_put
            n_pt2 = n_pt2_call if opt_type == "CE" else n_pt2_put
            n_pt3 = n_pt3_call if opt_type == "CE" else n_pt3_put

            ideas.append({'Index': f"{name} (Next Wk)", 'Spot': round(close_p, 2), 'Bias': bias, 'Opt': f"{atm_strike} {opt_type} [NW]", 'Prem': n_prem, 'PT1': round(n_pt1,1), 'PT2': round(n_pt2,1), 'PT3': round(n_pt3,1), 'SL': sl, 'T1': t1, 'T2': t2, 'T3': t3})
            
        except: continue
    return pd.DataFrame(ideas)

def generate_tabular_markdown(df_results, df_index, title, filename, include_index=False):
    md = f"# {title}\n\n"
    if include_index and not df_index.empty:
        md += "## 🏛️ Index Options (Curr & Next Week)\n"
        md += "| Index | Bias | Spot | Option | Prem | Prem Tgts (1/2/3) | SL | Spot Tgts (1/2/3) |\n"
        md += "|---|---|---|---|---|---|---|---|\n"
        for _, r in df_index.iterrows():
            md += f"| **{r['Index']}** | {r['Bias']} | ₹{r['Spot']} | **{r['Opt']}** | ₹{r['Prem']} | ₹{r['PT1']}/₹{r['PT2']}/₹{r['PT3']} | ₹{r['SL']} | ₹{r['T1']}/₹{r['T2']}/₹{r['T3']} |\n"
        md += "\n---\n\n"

    md += "## 📊 Quant Stock Setups (5 Targets)\n"
    if not df_results.empty:
        md += "| Stock | Entry | SL | Tgts (1/2/3/4/5) | Opt (CE) | Prem | Prem Tgts (1/2/3) |\n"
        md += "|---|---|---|---|---|---|---|\n"
        for _, r in df_results.iterrows():
            opt_str = r['Opt'] if r['Opt'] != 'N/A (Cash)' else '-'
            prem_str = f"₹{r['Prem']}" if r['Prem'] != '-' else '-'
            pt_str = f"₹{r['PT1']}/₹{r['PT2']}/₹{r['PT3']}" if r['Prem'] != '-' else '-'
            tgts_str = f"₹{r['EqT1']}/₹{r['EqT2']}/₹{r['EqT3']}/₹{r['EqT4']}/₹{r['EqT5']}"
            md += f"| **{r['Stock']}** | ₹{r['Entry']} | ₹{r['EqSL']} | {tgts_str} | {opt_str} | {prem_str} | {pt_str} |\n"
    else:
        md += "> *No highly profitable momentum setups met the strict criteria for this session.*\n"
    with open(filename, "w", encoding="utf-8") as f: f.write(md)

def generate_telegram_cards(df_results, df_index, title, filename, include_index=False):
    txt = f"*{title}*\n\n"
    if include_index and not df_index.empty:
        txt += "🏛️ *Index Options (Curr & Next Wk)*\n"
        for _, r in df_index.iterrows():
            txt += f"📌 *{r['Index']}* ({r['Bias']})\n"
            txt += f"• Spot: ₹{r['Spot']} | SL: ₹{r['SL']}\n"
            txt += f"• Spot Tgts: ₹{r['T1']} | ₹{r['T2']} | ₹{r['T3']}\n"
            txt += f"• Option: *{r['Opt']}* (Entry: ₹{r['Prem']})\n"
            txt += f"• Prem Tgts: ₹{r['PT1']} | ₹{r['PT2']} | ₹{r['PT3']}\n\n"
        txt += "➖➖➖➖➖➖➖➖➖➖\n\n"

    txt += "📊 *Quant Stock Setups (5 Targets)*\n\n"
    if not df_results.empty:
        for _, r in df_results.iterrows():
            txt += f"🟢 *{r['Stock']}* (RSI: {r['RSI']})\n"
            txt += f"• Entry: ₹{r['Entry']} | SL: ₹{r['EqSL']}\n"
            txt += f"• Eq Tgts: ₹{r['EqT1']} | ₹{r['EqT2']} | ₹{r['EqT3']} | ₹{r['EqT4']} | ₹{r['EqT5']}\n"
            if str(r['Opt']) != 'N/A (Cash)':
                txt += f"• Option: *{r['Opt']}* (Entry: ₹{r['Prem']})\n"
                txt += f"• Prem Tgts: ₹{r['PT1']} | ₹{r['PT2']} | ₹{r['PT3']}\n"
            txt += "\n"
    else:
        txt += "No highly profitable setups met criteria.\n"
    with open(filename, "w", encoding="utf-8") as f: f.write(txt)

def run():
    sess_title, sess_type = get_session_info()
    df_index = get_index_options_ideas()
    fno_list = get_fno_symbols()
    tickers = get_all_nse_tickers()
    
    data = yf.download(tickers, period="3mo", interval="1d", progress=False, threads=True)
    if data.empty: return
    
    closes, highs, lows, volumes = data['Close'], data['High'], data['Low'], data['Volume']
    ema_50_all = closes.ewm(span=50).mean()
    vol_50d_avg_all = volumes.rolling(50).mean()
    
    delta = closes.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rsi_all = 100 - (100 / (1 + (gain / loss)))

    exp1 = closes.ewm(span=12, adjust=False).mean()
    exp2 = closes.ewm(span=26, adjust=False).mean()
    macd_all = exp1 - exp2
    macd_signal_all = macd_all.ewm(span=9, adjust=False).mean()
    
    hl = highs - lows
    hc = (highs - closes.shift(1)).abs()
    lc = (lows - closes.shift(1)).abs()
    tr = pd.DataFrame(np.maximum(hl.values, np.maximum(hc.values, lc.values)), index=hl.index, columns=hl.columns)
    atr_all = tr.ewm(alpha=1/14).mean()

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

    valid_setups = []

    for ticker in closes.columns:
        try:
            close_p = float(last_close[ticker])
            high_p = float(last_high[ticker])
            low_p = float(last_low[ticker])
            vol_today = float(last_vol[ticker])
            
            if pd.isna(close_p) or close_p <= 0 or high_p == low_p or vol_today < 1000: continue
            
            vol_50_avg = float(last_vol_50[ticker])
            if pd.isna(vol_50_avg) or vol_50_avg <= 0: continue
            
            rsi_val = float(last_rsi[ticker])
            if pd.isna(rsi_val) or rsi_val > 72.0: continue
            
            macd_val = float(last_macd[ticker])
            macd_sig = float(last_macd_signal[ticker])
            if macd_val < macd_sig: continue
            
            ema_50 = float(last_ema_50[ticker])
            passes_ema = close_p >= ema_50
            atr = float(last_atr[ticker])

            pos = round(((close_p - low_p) / (high_p - low_p)) * 100, 1)
            if pos < 55.0: continue 

            vol_vs = round(vol_today / vol_50_avg, 2)

            if sess_type == "Intraday": hor = "Intraday" if vol_vs >= 1.3 else "Swing"
            else: hor = "BTST" if vol_vs >= 1.2 else "Swing"

            base_score = (2 if 55 <= rsi_val <= 68 else 0) + (2 if vol_vs>=2 else 0)
            
            t1 = round(close_p + 1.5 * atr, 1)
            t2 = round(close_p + 3.0 * atr, 1)
            t3 = round(close_p + 4.5 * atr, 1)
            t4 = round(close_p + 6.0 * atr, 1)
            t5 = round(close_p + 7.5 * atr, 1)

            symbol = ticker.replace(".NS", "")
            if symbol in fno_list:
                df_h, df_l, df_c = highs[ticker].dropna(), lows[ticker].dropna(), closes[ticker].dropna()
                opt, prem, pt1, pt2, pt3 = generate_quant_option(close_p, t1, t2, t3, df_h, df_l, df_c)
            else:
                opt, prem, pt1, pt2, pt3 = "N/A (Cash)", "-", "-", "-", "-"
            
            record = {'Stock': symbol, 'Horizon': hor, 'Entry': round(close_p, 2), 'RSI': round(rsi_val,1), 'EqSL': round(close_p-1.5*atr,1), 'EqT1': t1, 'EqT2': t2, 'EqT3': t3, 'EqT4': t4, 'EqT5': t5, 'Opt': opt, 'Prem': prem, 'PT1': pt1, 'PT2': pt2, 'PT3': pt3, 'Score': base_score}

            if passes_ema and base_score >= 2:
                valid_setups.append(record)
        except: continue

    df_all = pd.DataFrame(valid_setups).drop_duplicates(subset=['Stock']).sort_values(by=['Score', 'RSI'], ascending=[False, False]) if valid_setups else pd.DataFrame()

    df_intra = df_all[df_all['Horizon'] == 'Intraday'].head(20) if not df_all.empty else pd.DataFrame()
    df_btst = df_all[df_all['Horizon'] == 'BTST'].head(20) if not df_all.empty else pd.DataFrame()
    df_swing = df_all[df_all['Horizon'] == 'Swing'].head(20) if not df_all.empty else pd.DataFrame()

    generate_tabular_markdown(df_intra, df_index, f"⚡ Intraday & Index Report — {sess_title}", "intraday_report.md", include_index=True)
    generate_tabular_markdown(df_btst, pd.DataFrame(), f"🌙 BTST Carry-Forward Report — {sess_title}", "btst_report.md", include_index=False)
    generate_tabular_markdown(df_swing, pd.DataFrame(), f"📈 Swing Trade Report — {sess_title}", "swing_report.md", include_index=False)

    generate_telegram_cards(df_intra, df_index, f"⚡ Intraday & Index Report — {sess_title}", "intraday_tg.txt", include_index=True)
    generate_telegram_cards(df_btst, pd.DataFrame(), f"🌙 BTST Carry-Forward Report — {sess_title}", "btst_tg.txt", include_index=False)
    generate_telegram_cards(df_swing, pd.DataFrame(), f"📈 Swing Trade Report — {sess_title}", "swing_tg.txt", include_index=False)

if __name__ == "__main__": run()
