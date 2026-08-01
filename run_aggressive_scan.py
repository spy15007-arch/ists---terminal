import yfinance as yf
import pandas as pd
import numpy as np
import requests
import io
import datetime

def get_session_info():
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    ist_now = utc_now + datetime.timedelta(hours=5, minutes=30)
    hour = ist_now.hour
    if hour < 12:
        return "🌅 MORNING AGGRESSIVE SCAN (09:15-09:45 IST)", "Intraday"
    else:
        return "🌙 PRE-CLOSE AGGRESSIVE SCAN (15:15 IST)", "BTST"

def get_index_options_ideas():
    ideas = []
    indices = [('NIFTY 50', '^NSEI', 50), ('BANK NIFTY', '^NSEBANK', 100)]
    for name, symbol, step in indices:
        try:
            df = yf.download(symbol, period="1mo", interval="1d", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if not df.empty:
                close_p = float(df['Close'].iloc[-1])
                ema_20 = float(df['Close'].ewm(span=20, adjust=False).mean().iloc[-1])
                atm_strike = int(round(close_p / step) * step)

                if close_p >= ema_20:
                    bias = "🟢 BULLISH (Above EMA20)"
                    contract = f"BUY {name.replace(' ', '')} {atm_strike} CE"
                    sl = round(close_p * 0.995, 1)
                    t1 = round(close_p * 1.005, 1)
                    t2 = round(close_p * 1.010, 1)
                    t3 = round(close_p * 1.015, 1)
                else:
                    bias = "🔴 BEARISH (Below EMA20)"
                    contract = f"BUY {name.replace(' ', '')} {atm_strike} PE"
                    sl = round(close_p * 1.005, 1)
                    t1 = round(close_p * 0.995, 1)
                    t2 = round(close_p * 0.990, 1)
                    t3 = round(close_p * 0.985, 1)

                ideas.append({
                    'Index': name, 'Spot Price': round(close_p, 2), 'Trend Bias': bias,
                    'Recommended Option': contract, 'Spot SL': sl,
                    'Spot Target 1': t1, 'Spot Target 2': t2, 'Spot Target 3': t3
                })
        except Exception:
            continue
    return pd.DataFrame(ideas)

def get_nifty500_tickers():
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        df = pd.read_csv(io.StringIO(response.text))
        if 'Symbol' in df.columns:
            return [f"{symbol}.NS" for symbol in df['Symbol'].tolist()]
    except Exception:
        pass
    fallback = ['TVSMOTOR', 'COFORGE', 'HAL', 'BEL', 'DIXON', 'TRENT', 'MCX', 'PERSISTENT', 'RELIANCE', 'SBIN', 'DIVISLAB', 'FEDERALBNK']
    return [f"{s}.NS" for s in fallback]

def run():
    session_title, session_type = get_session_info()
    df_index = get_index_options_ideas()
    tickers = get_nifty500_tickers()
    results = []

    try:
        nifty = yf.download('^NSEI', period="6m", interval="1d", progress=False)['Close']
        if isinstance(nifty, pd.DataFrame): nifty = nifty.iloc[:, 0]
        nifty = nifty.dropna()
        nifty_3m = ((nifty.iloc[-1] / nifty.iloc[-63]) - 1) * 100 if len(nifty) >= 63 else 0.0
    except Exception:
        nifty_3m = 0.0

    try:
        data = yf.download(tickers, period="1y", interval="1d", group_by='ticker', progress=False)
    except Exception:
        data = pd.DataFrame()

    if not data.empty:
        for ticker in tickers:
            symbol = ticker.replace(".NS", "")
            try:
                if ticker not in data.columns.levels[0] if isinstance(data.columns, pd.MultiIndex) else ticker not in data: continue
                df = data[ticker].dropna() if isinstance(data.columns, pd.MultiIndex) else data.dropna()
                if len(df) < 200: continue

                close_p = float(df['Close'].iloc[-1])
                high_p = float(df['High'].iloc[-1])
                low_p = float(df['Low'].iloc[-1])
                vol_today = float(df['Volume'].iloc[-1])

                ema_20 = float(df['Close'].ewm(span=20, adjust=False).mean().iloc[-1])
                ema_50 = float(df['Close'].ewm(span=50, adjust=False).mean().iloc[-1])
                ema_200 = float(df['Close'].ewm(span=200, adjust=False).mean().iloc[-1])

                if not (close_p > ema_50 and ema_50 > ema_200): continue

                stock_3m_return = ((close_p / float(df['Close'].iloc[-63])) - 1) * 100
                rs_edge_pct = round(stock_3m_return - nifty_3m, 1)
                if rs_edge_pct < 0: continue

                close_pos = round(((close_p - low_p) / (high_p - low_p)) * 100, 1) if high_p != low_p else 50.0
                vol_50d_avg = float(df['Volume'].rolling(50).mean().iloc[-1])
                vol_vs_50d = round(vol_today / vol_50d_avg, 2) if vol_50d_avg > 0 else 1.0

                high_50d = float(df['High'].rolling(50).max().iloc[-1])
                resistance_clearance = round(((high_50d - close_p) / close_p) * 100, 1) if high_50d > close_p else 0.0

                score = 2
                if close_p > ema_20: score += 2
                if vol_vs_50d >= 1.3: score += 2
                elif vol_vs_50d >= 1.1: score += 1
                if close_pos >= 70: score += 2
                elif close_pos >= 50: score += 1
                if resistance_clearance <= 3.0: score += 2

                score = min(10, score)
                composite = round((close_pos * 0.25) + (min(vol_vs_50d * 15, 30)) + (min(max(0, rs_edge_pct), 20)), 1)

                if session_type == "Intraday":
                    if vol_vs_50d >= 1.3 or close_pos >= 70:
                        horizon = "⚡ Intraday Momentum"
                    else:
                        horizon = "📈 Swing (1-2 Weeks)"
                else: # Pre-Close
                    if close_pos >= 75 and vol_vs_50d >= 1.2:
                        horizon = "🌙 BTST Entry (15:15 IST)"
                    else:
                        horizon = "📈 Swing (1-2 Weeks)"

                high_low = df['High'] - df['Low']
                high_close = np.abs(df['High'] - df['Close'].shift())
                low_close = np.abs(df['Low'] - df['Close'].shift())
                tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                atr = float(tr.ewm(alpha=1/14, adjust=False).mean().iloc[-1])

                step = 100 if close_p > 5000 else (50 if close_p > 2000 else (20 if close_p > 1000 else (10 if close_p > 500 else 5)))
                atm_strike = int(round(close_p / step) * step)

                results.append({
                    'Stock': symbol, 'Horizon': horizon, 'Entry': round(close_p, 2), 'Score': score, 'Composite': composite,
                    'EqSL': round(close_p - (1.5 * atr), 1),
                    'EqT1': round(close_p + (1.5 * atr), 1),
                    'EqT2': round(close_p + (3.0 * atr), 1),
                    'EqT3': round(close_p + (4.5 * atr), 1),
                    'Option': f"BUY {symbol} {atm_strike} CE",
                    'OptSL': round(close_p * 0.985, 1),
                    'OptT1': round(close_p * 1.02, 1),
                    'OptT2': round(close_p * 1.04, 1),
                    'OptT3': round(close_p * 1.06, 1)
                })
            except Exception:
                continue

    md = f"# ⚡ ISTS Pro — {session_title}\n\n"

    if not df_index.empty:
        md += "## 🏛️ Live Index Options (Nifty 50 & Bank Nifty) — Call & Put Strategies\n\n"
        md += "| Index | Spot Price (₹) | Trend Bias | Recommended Option | Spot SL (₹) | Spot Target 1 | Spot Target 2 | Spot Target 3 |\n"
        md += "| :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: |\n"
        for _, r in df_index.iterrows():
            md += f"| **{r['Index']}** | ₹{r['Spot Price']} | {r['Trend Bias']} | **{r['Recommended Option']}** | ₹{r['Spot SL']} | ₹{r['Spot Target 1']} | ₹{r['Spot Target 2']} | ₹{r['Spot Target 3']} |\n"
        md += "\n---\n\n"

    if results:
        df_res = pd.DataFrame(results).sort_values(by=['Score', 'Composite'], ascending=[False, False]).head(25)
        df_res['Rank'] = range(1, len(df_res) + 1)

        md += "## 🏆 Aggressive Multi-Horizon Equity & Option Leaderboard\n\n"
        md += "| Rank | Stock | Horizon | Entry (₹) | Score | Equity SL | Target 1 | Target 2 | Target 3 | Call Option Strategy | Spot SL | Spot Target 1 | Spot Target 2 | Spot Target 3 |\n"
        md += "| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :---: | :---: | :---: | :---: |\n"
        for _, r in df_res.iterrows():
            md += f"| {r['Rank']} | **{r['Stock']}** | {r['Horizon']} | ₹{r['Entry']} | 🔥 {r['Score']}/10 | ₹{r['EqSL']} | ₹{r['EqT1']} | ₹{r['EqT2']} | ₹{r['EqT3']} | **{r['Option']}** | ₹{r['OptSL']} | ₹{r['OptT1']} | ₹{r['OptT2']} | ₹{r['OptT3']} |\n"
    else:
        md += "_No aggressive momentum setups found in this session._\n"

    with open("aggressivesummary.md", "w", encoding="utf-8") as f:
        f.write(md)

if __name__ == "__main__":
    run()
