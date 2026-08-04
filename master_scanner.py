import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import math
import calendar
from scipy.stats import norm
import warnings
warnings.filterwarnings('ignore')

# --- FIREWALL-PROOF F&O UNIVERSE ---
STATIC_FNO = ["AARTIIND", "ABB", "ABBOTINDIA", "ABCAPITAL", "ABFRL", "ACC", "ADANIENT", "ADANIPORTS", "ALKEM", "AMBUJACEM", "APOLLOHOSP", "APOLLOTYRE", "ASHOKLEY", "ASIANPAINT", "ASTRAL", "ATUL", "AUBANK", "AUROPHARMA", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BALKRISIND", "BALRAMCHIN", "BANDHANBNK", "BANKBARODA", "BATAINDIA", "BEL", "BERGEPAINT", "BHARATFORG", "BHARTIARTL", "BHEL", "BIOCON", "BOSCHLTD", "BPCL", "BRITANNIA", "CANBK", "CANFINHOME", "CHAMBLFERT", "CHOLAFIN", "CIPLA", "COALINDIA", "COFORGE", "COLPAL", "CONCOR", "COROMANDEL", "CROMPTON", "CUB", "CUMMINSIND", "DABUR", "DALBHARAT", "DEEPAKNTR", "DIVISLAB", "DIXON", "DLF", "DRREDDY", "EICHERMOT", "ESCORTS", "EXIDEIND", "FEDERALBNK", "GAIL", "GLENMARK", "GMRINFRA", "GNFC", "GODREJCP", "GODREJPROP", "GRANULES", "GRASIM", "GUJGASLTD", "HAL", "HAVELLS", "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDCOPPER", "HINDPETRO", "HINDUNILVR", "ICICIBANK", "ICICIGI", "ICICIPRULI", "IDEA", "IDFCFIRSTB", "IEX", "IGL", "INDHOTEL", "INDIACEM", "INDIAMART", "INDIGO", "INDUSINDBK", "INFY", "IOC", "IPCALAB", "IRCTC", "ITC", "JINDALSTEL", "JSWSTEEL", "JUBLFOOD", "KOTAKBANK", "LALPATHLAB", "LAURUSLABS", "LICHSGFIN", "LT", "LTIM", "LTTS", "LUPIN", "M&M", "M&MFIN", "MANAPPURAM", "MARICO", "MARUTI", "MCDOWELL-N", "MCX", "METROPOLIS", "MFSL", "MGL", "MOTHERSON", "MPHASIS", "MRF", "MUTHOOTFIN", "NATIONALUM", "NAUKRI", "NAVINFLUOR", "NESTLEIND", "NMDC", "NTPC", "OBEROIRLTY", "OFSS", "ONGC", "PAGEIND", "PEL", "PETRONET", "PFC", "PIDILITIND", "PIIND", "PNB", "POLYCAB", "POWERGRID", "PVRINOX", "RAMCOCEM", "RBLBANK", "RECLTD", "RELIANCE", "SAIL", "SBICARD", "SBILIFE", "SBIN", "SHREECEM", "SHRIRAMFIN", "SIEMENS", "SRF", "SUNPHARMA", "SUNTV", "SYNGENE", "TATACHEM", "TATACOMM", "TATACONSUM", "TATAMOTORS", "TATAPOWER", "TATASTEEL", "TCS", "TECHM", "TITAN", "TORNTPHARM", "TRENT", "TVSMOTOR", "UBL", "ULTRACEMCO", "UPL", "VEDL", "VOLTAS", "WIPRO", "ZEEL", "ZYDUSLIFE"]

def get_session_info():
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    hour = now_ist.hour
    if hour < 12:
        return now_ist.strftime("%d %b %Y | %I:%M %p (Morning Intraday)"), "Intraday"
    else:
        return now_ist.strftime("%d %b %Y | %I:%M %p (Afternoon BTST)"), "BTST"

def get_expiry_dte(symbol_type):
    """Dynamic Expiry Calendar for Indian Markets"""
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    today = now.date()
    
    if symbol_type == "NIFTY":
        days_ahead = 3 - now.weekday() # Next Thursday
        if days_ahead < 0 or (days_ahead == 0 and now.hour >= 15): days_ahead += 7
        return max(1, days_ahead), "Current Wk"
        
    elif symbol_type == "BANKNIFTY":
        days_ahead = 2 - now.weekday() # Next Wednesday
        if days_ahead < 0 or (days_ahead == 0 and now.hour >= 15): days_ahead += 7
        return max(1, days_ahead), "Current Wk"
        
    else:
        c = calendar.Calendar(firstweekday=calendar.MONDAY)
        monthcal = c.monthdatescalendar(today.year, today.month)
        last_thursday = [d for week in monthcal for d in week if d.weekday() == 3 and d.month == today.month][-1]
        
        if today > last_thursday or (today == last_thursday and now.hour >= 15):
            next_month = today.month + 1 if today.month < 12 else 1
            next_year = today.year if today.month < 12 else today.year + 1
            monthcal = c.monthdatescalendar(next_year, next_month)
            last_thursday = [d for week in monthcal for d in week if d.weekday() == 3 and d.month == next_month][-1]
        
        dte = (last_thursday - today).days
        return max(1, dte), "Monthly"

def black_scholes(S, K, T, r, sigma):
    if T <= 0 or sigma == 0: return max(0, S - K), max(0, K - S), 1.0 if S > K else 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    call_prem = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    return round(call_prem, 2)

def generate_quant_option(price, t1, t2, t3, df_h, df_l, df_c, dte, label):
    step = 100 if price > 5000 else (50 if price > 2000 else (20 if price > 1000 else (10 if price > 500 else 5)))
    atm = int(round(price / step) * step)
    try:
        vol = math.sqrt((1.0 / (4.0 * math.log(2.0))) * ((np.log(df_h/df_l)**2).tail(10).mean())) * math.sqrt(252)
        if math.isnan(vol) or vol == 0: vol = np.log(df_c/df_c.shift(1)).tail(10).std() * math.sqrt(252)
        if math.isnan(vol) or vol == 0: vol = 0.2
    except: vol = 0.2
    
    c_prem = black_scholes(price, atm, dte/365.0, 0.07, vol)
    pt1 = black_scholes(t1, atm, dte/365.0, 0.07, vol)
    pt2 = black_scholes(t2, atm, dte/365.0, 0.07, vol)
    pt3 = black_scholes(t3, atm, dte/365.0, 0.07, vol)
    
    return f"{atm} CE [{label}]", c_prem, round(pt1, 1), round(pt2, 1), round(pt3, 1)

def get_index_options_ideas():
    indices = {'NIFTY 50': '^NSEI', 'BANK NIFTY': '^NSEBANK'}
    results = []
    
    for name, ticker in indices.items():
        try:
            data = yf.download(ticker, period="1mo", interval="1d", progress=False)
            if data.empty: continue
            
            close_p = float(data['Close'].iloc[-1])
            
            hl = data['High'] - data['Low']
            hc = (data['High'] - data['Close'].shift(1)).abs()
            lc = (data['Low'] - data['Close'].shift(1)).abs()
            tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
            atr = float(tr.ewm(alpha=1/14).mean().iloc[-1])
            
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rsi_val = float((100 - (100 / (1 + (gain / loss)))).iloc[-1])
            
            t1 = round(close_p + 1.5 * atr, 1)
            t2 = round(close_p + 3.0 * atr, 1)
            t3 = round(close_p + 4.5 * atr, 1)
            t4 = round(close_p + 6.0 * atr, 1)
            t5 = round(close_p + 7.5 * atr, 1)
            
            # Dynamic Calendar calculation for Index Options
            sym_type = "NIFTY" if name == 'NIFTY 50' else "BANKNIFTY"
            dte, label = get_expiry_dte(sym_type)
            
            opt, prem, pt1, pt2, pt3 = generate_quant_option(close_p, t1, t2, t3, data['High'], data['Low'], data['Close'], dte, label)
            
            results.append({
                'Stock': name, 'Horizon': 'Intraday', 'Entry': round(close_p, 2),
                'RSI': round(rsi_val, 1), 'EqSL': round(close_p - 1.5 * atr, 1),
                'EqT1': t1, 'EqT2': t2, 'EqT3': t3, 'EqT4': t4, 'EqT5': t5,
                'Opt': opt, 'Prem': prem, 'PT1': pt1, 'PT2': pt2, 'PT3': pt3, 'Score': 10
            })
        except: pass
        
    return pd.DataFrame(results)

def generate_tabular_markdown(df_stocks, df_index, title, filename, include_index=False):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write("> **System:** Quant Breakout Strategy | **Targets:** 5x ATR Vector & Black-Scholes Premiums\n\n")
        
        if include_index and not df_index.empty:
            f.write("## 👑 Index Options (High Conviction Intraday)\n\n")
            f.write("| Index | Price | Base Score | Eq SL | Eq T1/T2/T3/T4/T5 | Option | Prem | Prem T1/T2/T3 |\n")
            f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
            for _, r in df_index.iterrows():
                eq_tgts = f"{r['EqT1']}/{r['EqT2']}/{r['EqT3']}/{r['EqT4']}/{r['EqT5']}"
                prem_tgts = f"{r['PT1']}/{r['PT2']}/{r['PT3']}"
                f.write(f"| **{r['Stock']}** | ₹{r['Entry']} | 🔥 {r['Score']}/10 | ₹{r['EqSL']} | {eq_tgts} | **{r['Opt']}** | ₹{r['Prem']} | {prem_tgts} |\n")
            f.write("\n---\n\n")

        f.write("## 📊 F&O High-Momentum Scans\n\n")
        if df_stocks.empty:
            f.write("*No setups met the strict mathematical criteria in this session.*\n")
            return

        f.write("| Stock | Price | Base Score | Eq SL | Eq T1/T2/T3/T4/T5 | Option | Prem | Prem T1/T2/T3 |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        
        for _, r in df_stocks.iterrows():
            badge = f"🔥 {r['Score']}/10" if r['Score'] >= 4 else f"{r['Score']}/10"
            eq_tgts = f"{r['EqT1']}/{r['EqT2']}/{r['EqT3']}/{r['EqT4']}/{r['EqT5']}"
            prem_tgts = f"{r['PT1']}/{r['PT2']}/{r['PT3']}" if r['Prem'] != "-" else "-/-/-"
            f.write(f"| **{r['Stock']}** | ₹{r['Entry']} | {badge} | ₹{r['EqSL']} | {eq_tgts} | **{r['Opt']}** | ₹{r['Prem']} | {prem_tgts} |\n")

def generate_telegram_cards(df_stocks, df_index, title, filename, include_index=False):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"🚨 {title} 🚨\n\n")
        if include_index and not df_index.empty:
            f.write("👑 INDEX ALERTS\n")
            for _, r in df_index.iterrows():
                f.write(f"• {r['Stock']} @ ₹{r['Entry']}\n  {r['Opt']} @ ₹{r['Prem']}\n  Tgts: {r['PT1']}/{r['PT2']}/{r['PT3']}\n\n")
        
        f.write("📊 TOP QUANT SETUPS\n")
        for _, r in df_stocks.head(7).iterrows():
            f.write(f"• {r['Stock']} @ ₹{r['Entry']}\n  Eq Tgts: {r['EqT1']}/{r['EqT2']}/{r['EqT3']}\n")
            if str(r['Opt']) != "N/A (Cash)": f.write(f"  {r['Opt']} @ ₹{r['Prem']}\n")
            f.write("\n")

def run():
    print("🚀 Starting Automated Master Quant Scanner...")
    sess_title, sess_type = get_session_info()
    
    if sess_type == "Intraday":
        df_index = get_index_options_ideas()
    else:
        df_index = pd.DataFrame() 
    
    tickers = [f"{s}.NS" for s in STATIC_FNO]
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
    
    # Calculate accurate DTE for all stock options once
    stock_dte, stock_label = get_expiry_dte("STOCK")

    for ticker in closes.columns:
        try:
            close_p = float(last_close[ticker])
            high_p = float(last_high[ticker])
            low_p = float(last_low[ticker])
            vol_today = float(last_vol[ticker])
            
            if pd.isna(close_p) or close_p <= 0 or vol_today < 1000: continue
            
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

            base_score = (2 if 55 <= rsi_val <= 68 else 0) + (2 if vol_vs >= 1.5 else 0)
            
            t1 = round(close_p + 1.5 * atr, 1)
            t2 = round(close_p + 3.0 * atr, 1)
            t3 = round(close_p + 4.5 * atr, 1)
            t4 = round(close_p + 6.0 * atr, 1)
            t5 = round(close_p + 7.5 * atr, 1)

            symbol = ticker.replace(".NS", "")
            df_h, df_l, df_c = highs[ticker].dropna(), lows[ticker].dropna(), closes[ticker].dropna()
            
            # Pass actual stock DTE
            opt, prem, pt1, pt2, pt3 = generate_quant_option(close_p, t1, t2, t3, df_h, df_l, df_c, stock_dte, stock_label)
            
            record = {
                'Stock': symbol, 'Horizon': hor, 'Entry': round(close_p, 2), 
                'RSI': round(rsi_val,1), 'EqSL': round(close_p-1.5*atr,1), 
                'EqT1': t1, 'EqT2': t2, 'EqT3': t3, 'EqT4': t4, 'EqT5': t5, 
                'Opt': opt, 'Prem': prem, 'PT1': pt1, 'PT2': pt2, 'PT3': pt3, 
                'Score': base_score
            }

            if passes_ema and base_score >= 2: valid_setups.append(record)
        except: continue

    df_all = pd.DataFrame(valid_setups).drop_duplicates(subset=['Stock']).sort_values(by=['Score', 'RSI'], ascending=[False, False]) if valid_setups else pd.DataFrame()
    df_intra = df_all[df_all['Horizon'] == 'Intraday'].head(20) if not df_all.empty else pd.DataFrame()
    df_btst = df_all[df_all['Horizon'] == 'BTST'].head(20) if not df_all.empty else pd.DataFrame()
    df_swing = df_all[df_all['Horizon'] == 'Swing'].head(20) if not df_all.empty else pd.DataFrame()

    if sess_type == "Intraday":
        generate_tabular_markdown(df_intra, df_index, f"⚡ Intraday Report — {sess_title}", "intraday_report.md", include_index=True)
        generate_tabular_markdown(df_swing, pd.DataFrame(), f"📈 Swing Trade Report — {sess_title}", "swing_report.md", include_index=False)
        open("btst_report.md", "w").close() 
    else:
        generate_tabular_markdown(df_btst, pd.DataFrame(), f"🌙 BTST Carry-Forward Report — {sess_title}", "btst_report.md", include_index=False)
        generate_tabular_markdown(df_swing, pd.DataFrame(), f"📈 Swing Trade Report — {sess_title}", "swing_report.md", include_index=False)
        open("intraday_report.md", "w").close() 

    if sess_type == "Intraday":
        generate_telegram_cards(df_intra, df_index, f"⚡ Intraday Report — {sess_title}", "intraday_tg.txt", include_index=True)
        generate_telegram_cards(df_swing, pd.DataFrame(), f"📈 Swing Trade Report — {sess_title}", "swing_tg.txt", include_index=False)
        open("btst_tg.txt", "w").close()
    else:
        generate_telegram_cards(df_btst, pd.DataFrame(), f"🌙 BTST Carry-Forward Report — {sess_title}", "btst_tg.txt", include_index=False)
        generate_telegram_cards(df_swing, pd.DataFrame(), f"📈 Swing Trade Report — {sess_title}", "swing_tg.txt", include_index=False)
        open("intraday_tg.txt", "w").close()

if __name__ == "__main__":
    run()
