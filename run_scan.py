import yfinance as yf
import pandas as pd
import numpy as np
import requests
import io

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
                low_50d = float(df['Low'].rolling(50).min().iloc[-1])
                base_range_pct = round(((high_50d - low_50d) / low_50d) * 100, 1) if low_50d > 0 else 20.0
                resistance_clearance = round(((high_50d - close_p) / close_p) * 100, 1) if high_50d > close_p else 0.0

                score = 0
                if close_pos >= 80: score += 2
                elif close_pos >= 65: score += 1
                if vol_vs_50d >= 2.0: score += 2
                elif vol_vs_50d >= 1.3: score += 1
                if base_range_pct <= 15: score += 2
                elif base_range_pct <= 25: score += 1
                if rs_edge_pct >= 15: score += 2
                elif rs_edge_pct >= 5: score += 1
                if resistance_clearance == 0: score += 2
                elif resistance_clearance <= 2.0: score += 1

                composite = round((close_pos * 0.25) + (min(vol_vs_50d * 15, 30)) + (max(0, 25 - base_range_pct * 0.5)) + (min(max(0, rs_edge_pct), 20)), 1)

                high_low = df['High'] - df['Low']
                high_close = np.abs(df['High'] - df['Close'].shift())
                low_close = np.abs(df['Low'] - df['Close'].shift())
                tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                atr = float(tr.ewm(alpha=1/14, adjust=False).mean().iloc[-1])

                step = 100 if close_p > 5000 else (50 if close_p > 2000 else (20 if close_p > 1000 else (10 if close_p > 500 else 5)))
                atm_strike = int(round(close_p / step) * step)

                results.append({
                    'Stock': symbol, 'Entry': round(close_p, 2), 'Score': score, 'Composite': composite,
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

    md = "# 📊 ISTS Pro — Strict Pre-Breakout Multi-Target Report\n\n"
    if results:
        df_res = pd.DataFrame(results).sort_values(by=['Score', 'Composite'], ascending=[False, False]).head(25)
        df_res['Rank'] = range(1, len(df_res) + 1)

        md += "## 📈 Equity Multi-Target Plan\n\n"
        md += "| Rank | Stock | Entry (₹) | Score | Equity SL (₹) | Target 1 (₹) | Target 2 (₹) | Target 3 (₹) |\n"
        md += "| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n"
        for _, r in df_res.iterrows():
            badge = f"🔥 {r['Score']}/10" if r['Score'] >= 5 else f"{r['Score']}/10"
            md += f"| {r['Rank']} | **{r['Stock']}** | ₹{r['Entry']} | {badge} | ₹{r['EqSL']} | ₹{r['EqT1']} | ₹{r['EqT2']} | ₹{r['EqT3']} |\n"

        md += "\n---\n\n## 🎯 Call Options Spot Multi-Target Plan\n\n"
        md += "| Stock | Entry (₹) | Option Strategy | Spot SL (₹) | Spot Target 1 | Spot Target 2 | Spot Target 3 |\n"
        md += "| :--- | :---: | :--- | :---: | :---: | :---: | :---: |\n"
        for _, r in df_res.iterrows():
            md += f"| **{r['Stock']}** | ₹{r['Entry']} | **{r['Option']}** | ₹{r['OptSL']} | ₹{r['OptT1']} | ₹{r['OptT2']} | ₹{r['OptT3']} |\n"
    else:
        md += "_No stocks met all strict breakout criteria in this session._\n"

    with open("breakoutsummary.md", "w", encoding="utf-8") as f:
        f.write(md)

if __name__ == "__main__":
    run()
