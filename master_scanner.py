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

# --- FIREWALL-PROOF F&O UNIVERSE ---
STATIC_FNO = ["AARTIIND", "ABB", "ABBOTINDIA", "ABCAPITAL", "ABFRL", "ACC", "ADANIENT", "ADANIPORTS", "ALKEM", "AMBUJACEM", "APOLLOHOSP", "APOLLOTYRE", "ASHOKLEY", "ASIANPAINT", "ASTRAL", "ATUL", "AUBANK", "AUROPHARMA", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BALKRISIND", "BALRAMCHIN", "BANDHANBNK", "BANKBARODA", "BATAINDIA", "BEL", "BERGEPAINT", "BHARATFORG", "BHARTIARTL", "BHEL", "BIOCON", "BOSCHLTD", "BPCL", "BRITANNIA", "CANBK", "CANFINHOME", "CHAMBLFERT", "CHOLAFIN", "CIPLA", "COALINDIA", "COFORGE", "COLPAL", "CONCOR", "COROMANDEL", "CROMPTON", "CUB", "CUMMINSIND", "DABUR", "DALBHARAT", "DEEPAKNTR", "DIVISLAB", "DIXON", "DLF", "DRREDDY", "EICHERMOT", "ESCORTS", "EXIDEIND", "FEDERALBNK", "GAIL", "GLENMARK", "GMRINFRA", "GNFC", "GODREJCP", "GODREJPROP", "GRANULES", "GRASIM", "GUJGASLTD", "HAL", "HAVELLS", "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDCOPPER", "HINDPETRO", "HINDUNILVR", "ICICIBANK", "ICICIGI", "ICICIPRULI", "IDEA", "IDFCFIRSTB", "IEX", "IGL", "INDHOTEL", "INDIACEM", "INDIAMART", "INDIGO", "INDUSINDBK", "INFY", "IOC", "IPCALAB", "IRCTC", "ITC", "JINDALSTEL", "JSWSTEEL", "JUBLFOOD", "KOTAKBANK", "LALPATHLAB", "LAURUSLABS", "LICHSGFIN", "LT", "LTIM", "LTTS", "LUPIN", "M&M", "M&MFIN", "MANAPPURAM", "MARICO", "MARUTI", "MCDOWELL-N", "MCX", "METROPOLIS", "MFSL", "MGL", "MOTHERSON", "MPHASIS", "MRF", "MUTHOOTFIN", "NATIONALUM", "NAUKRI", "NAVINFLUOR", "NESTLEIND", "NMDC", "NTPC", "OBEROIRLTY", "OFSS", "ONGC", "PAGEIND", "PEL", "PETRONET", "PFC", "PIDILITIND", "PIIND", "PNB", "POLYCAB", "POWERGRID", "PVRINOX", "RAMCOCEM", "RBLBANK", "RECLTD", "RELIANCE", "SAIL", "SBICARD", "SBILIFE", "SBIN", "SHREECEM", "SHRIRAMFIN", "SIEMENS", "SRF", "SUNPHARMA", "SUNTV", "SYNGENE", "TATACHEM", "TATACOMM", "TATACONSUM", "TATAMOTORS", "TATAPOWER", "TATASTEEL", "TCS", "TECHM", "TITAN", "TORNTPHARM", "TRENT", "TVSMOTOR", "UBL", "ULTRACEMCO", "UPL", "VEDL", "VOLTAS", "WIPRO", "ZEEL", "ZYDUSLIFE"]

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
    """Ensures the stock is in a structural uptrend with Higher Highs and Higher Lows."""
    if len(df_h) < 20: return True
    h_half1 = df_h.iloc[-20:-10].max()
    h_half2 = df_h.iloc[-10:].max()
    l_half1 = df_l.iloc[-20:-10].min()
    l_half2 = df_l.iloc[-10:].min()
    return (h_half2 >= h_half1) and (l_half2 >= l_half1)

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
            hc = (df_h - df_c.shift(1)).abs()
            lc = (df_l - df_c.shift(1)).abs()
            tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
            atr = float(tr.ewm(alpha=1/14).mean().iloc[-1])
            
            delta = df_c.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rsi_val = float((100 - (100 / (1 + (gain / loss)))).iloc[-1])
            
            if close_p > ema_50:
                direction = "Bullish (Call)"
                t1, t2, t3, t4, t5 = [round(close_p + m * atr, 1) for m in (0.4, 0.8, 1.2, 1.6, 2.0)]
                eq_sl = round(close_p - 0.8 * atr, 1)
            else:
                direction = "Bearish (Put)"
                t1, t2, t3, t4, t5 = [round(close_p - m * atr, 1) for m in (0.4, 0.8, 1.2, 1.6, 2.0)]
                eq_sl = round(close_p + 0.8 * atr, 1)
            
            opt, prem, pt1, pt2, pt3 = generate_quant_option(close_p, t1, t2, t3, df_h, df_l, df_c, direction.split(" ")[0])
            
            results.append({
                'Stock': f"{name} {direction}", 'Horizon': 'Intraday', 'Entry': round(close_p, 2),
                'RSI': round(rsi_val, 1), 'EqSL': eq_sl,
                'EqT1': t1, 'EqT2': t2, 'EqT3': t3, 'EqT4': t4, 'EqT5': t5,
                'Opt': opt, 'Prem': prem, 'PT1': pt1, 'PT2': pt2, 'PT3': pt3, 'Score': 10, 'Tag': 'Index Scalp'
            })
        except Exception as e: pass
        
    return pd.DataFrame(results)

def generate_tabular_markdown(df_stocks, df_index, title, filename, include_index=False):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write("> **System:** MTF Quant Breakout, Squeeze Detection & HH/HL Structure | **Targets:** ATR Vector & Black-Scholes\n\n")
        
        if df_stocks.empty and df_index.empty:
            f.write("*Market conditions did not trigger any structural quantitative setups for this timeframe.*\n")
            return

        if include_index and not df_index.empty:
            f.write("## 👑 Index Options (Intraday Scalps)\n\n")
            f.write("| # | Index Direction | Price | Score | Eq SL | Eq T1/T2/T3/T4/T5 | Option | Prem | Prem T1/T2/T3 |\n")
            f.write("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
            for idx, r in df_index.reset_index().iterrows():
                eq_tgts = f"{r['EqT1']}/{r['EqT2']}/{r['EqT3']}/{r['EqT4']}/{r['EqT5']}"
                prem_tgts = f"{r['PT1']}/{r['PT2']}/{r['PT3']}"
                f.write(f"| {idx+1} | **{r['Stock']}** | ₹{r['Entry']} | 🔥 {r['Score']}/10 | ₹{r['EqSL']} | {eq_tgts} | **{r['Opt']}** | ₹{r['Prem']} | {prem_tgts} |\n")
            f.write("\n---\n\n")

        if not df_stocks.empty:
            f.write("## 📊 F&O High-Momentum & Structural Squeeze Scans (Long-Only)\n\n")
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
        msg += "👑 *INDEX ALERTS*\n"
        for _, r in df_index.iterrows():
            msg += f"• {r['Stock']} @ ₹{r['Entry']}\n  {r['Opt']} @ ₹{r['Prem']}\n  Opt Targets: {r['PT1']}/{r['PT2']}/{r['PT3']}\n\n"
    
    if not df_stocks.empty:
        msg += "📊 *TOP QUANT & STRUCTURAL SETUPS (Long-Only)*\n"
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
        msg += "No high-conviction structural long setups triggered for this scan."
        
    return msg

def run():
    print("🚀 Starting Automated Master Quant Scanner (Structural HH/HL & Live Price Edition)...")
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
    
    tickers = [f"{s}.NS" for s in STATIC_FNO]
    data = yf.download(tickers, period="6mo", interval="1d", progress=False, threads=True)
    
    if data.empty: return
    
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

    last_high = highs.iloc[-1]
    last_low = lows.iloc[-1]
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

            # Squeeze & Structural Trend checks
            recent_vol_avg = float(volumes[ticker].tail(3).mean())
            recent_range_avg = float((highs[ticker].tail(3) - lows[ticker].tail(3)).mean())
            is_squeeze = (recent_vol_avg < vol_50_avg * 0.85) and (recent_range_avg < atr * 0.85)
            is_structural_uptrend = check_structure_hh_hl(highs[ticker], lows[ticker])

            if vol_vs >= 1.5:
                hor, m1, m2, m3, m4, m5, sl_m = "Intraday", 0.4, 0.8, 1.2, 1.6, 2.0, 0.8
            elif is_squeeze or vol_vs >= 1.2:
                hor, m1, m2, m3, m4, m5, sl_m = "BTST", 0.8, 1.6, 2.4, 3.2, 4.0, 1.0
            else:
                hor, m1, m2, m3, m4, m5, sl_m = "Swing", 1.5, 3.0, 4.5, 6.0, 7.5, 1.5

            # Core conditions + structural HH/HL filter requirement
            if close_p > d_ema and close_p > w_ema and macd_val > macd_sig and (55 <= rsi_val <= 75) and is_structural_uptrend:
                direction = "Bullish"
                t1, t2, t3, t4, t5 = [round(close_p + m * atr, 1) for m in (m1, m2, m3, m4, m5)]
                eq_sl = round(close_p - sl_m * atr, 1)
                
                if is_squeeze:
                    base_score = 5  
                    tag = "🔥 Squeeze Blast (1-3d)"
                else:
                    base_score = 2 + (2 if vol_vs >= 1.5 else 0)
                    tag = "Momentum Breakout"
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
