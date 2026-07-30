import yfinance as yf
import pandas as pd
import numpy as np
import requests

# 1. FETCH DYNAMIC NIFTY 500 TICKER UNIVERSE
def get_nifty500_tickers():
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        df = pd.read_csv(pd.compat.StringIO(response.text))
        return [f"{symbol}.NS" for symbol in df['Symbol'].tolist()]
    except Exception:
        fallback_symbols = [
            'EXIDEIND', 'RBLBANK', 'ACMESOLAR', 'NYKAA', 'FEDERALBNK', 'IEX',
            'PARADEEP', 'PCBL', 'FSL', 'RADICO', 'SAREGAMA', 'BHARTIHEXA'
        ]
        return [f"{s}.NS" for s in fallback_symbols]

# 2. OPTIONS CONTRACT RECOMMENDATION ENGINE
def generate_option_idea(symbol, price, score):
    if score < 7:
        return "N/A", "-", "-"
    
    if price > 5000: step = 100
    elif price > 2000: step = 50
    elif price > 1000: step = 20
    elif price > 500: step = 10
    else: step = 5

    atm_strike = int(round(price / step) * step)
    return f"BUY {symbol} {atm_strike} CE", f"₹{round(price * 1.03, 1)}", f"₹{round(price * 0.985, 1)}"

def run():
    tickers = get_nifty500_tickers()
    results = []

    try:
        nifty = yf.download('^NSEI', period="6m", interval="1d", progress=False)['Close']
        if isinstance(nifty, pd.DataFrame): nifty = nifty.iloc[:, 0]
        nifty_3m = ((nifty.iloc[-1] / nifty.iloc[-63]) - 1) * 100
    except Exception:
        nifty_3m = 0.0

    data = yf.download(tickers, period="1y", interval="1d", group_by='ticker', progress=False)

    for ticker in tickers:
        symbol = ticker.replace(".NS", "")
        try:
            df = data[ticker].dropna() if len(tickers) > 1 else data.dropna()
            if len(df) < 200: continue

            close_p = df['Close'].iloc[-1]

            # --- STRICT BUDGET FILTER: PRICE MUST BE <= ₹500 ---
            if close_p > 500:
                continue

            high_p = df['High'].iloc[-1]
            low_p = df['Low'].iloc[-1]
            vol_today = df['Volume'].iloc[-1]

            ema_50 = df['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
            ema_200 = df['Close'].ewm(span=200, adjust=False).mean().iloc[-1]

            # Stage-2 Uptrend filter
            if not (close_p > ema_50 and ema_50 > ema_200):
                continue

            stock_3m_return = ((close_p / df['Close'].iloc[-63]) - 1) * 100
            rs_edge_pct = round(stock_3m_return - nifty_3m, 1)

            if rs_edge_pct < 0:
                continue

            close_pos = round(((close_p - low_p) / (high_p - low_p)) * 100, 1) if high_p != low_p else 50.0
            vol_50d_avg = df['Volume'].rolling(50).mean().iloc[-1]
            vol_vs_50d = round(vol_today / vol_50d_avg, 2) if vol_50d_avg > 0 else 1.0

            high_50d = df['High'].rolling(50).max().iloc[-1]
            low_50d = df['Low'].rolling(50).min().iloc[-1]
            base_range_pct = round(((high_50d - low_50d) / low_50d) * 100, 1)
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

            composite = round(
                (close_pos * 0.25) + 
                (min(vol_vs_50d * 15, 30)) + 
                (max(0, 25 - base_range_pct * 0.5)) + 
                (min(max(0, rs_edge_pct), 20)), 
                1
            )

            opt_contract, opt_target, opt_sl = generate_option_idea(symbol, close_p, score)

            results.append({
                'Stock': symbol, 
                'Price': round(close_p, 2), 
                'Score': score,
                'Composite': composite, 
                'ClosePos': close_pos, 
                'Vol50d': vol_vs_50d,
                'BaseRange': base_range_pct, 
                'RSEdge': rs_edge_pct, 
                'ResClear': resistance_clearance,
                'OptionContract': opt_contract,
                'OptTarget': opt_target,
                'OptSL': opt_sl
            })
        except Exception:
            continue

    df_res = pd.DataFrame(results).sort_values(by=['Score', 'Composite'], ascending=[False, False]).head(20)
    df_res['Rank'] = range(1, len(df_res) + 1) if not df_res.empty else []

    # Build budgetsummary.md
    md = "# 💡 ISTS Pro — Budget Momentum Report (Under ₹500)\n\n"
    md += f"> **Universe:** Top 500 NSE Stocks | **Filter:** Price ≤ ₹500 + Stage-2 Uptrend + RS Edge\n\n"
    md += "## 🏆 Top Budget Setups Leaderboard (Ranked Best to Weakest)\n\n"
    md += "| Rank | Stock | Price (₹) | Readiness Score | Composite /100 | Close Pos % | Vol vs 50d | Base Range % | RS Edge % | Resistance Clearance % |\n"
    md += "| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n"

    for _, r in df_res.iterrows():
        badge = f"🔥 {r['Score']}/10" if r['Score'] >= 8 else f"{r['Score']}/10"
        md += (
            f"| {r['Rank']} | **{r['Stock']}** | ₹{r['Price']} | {badge} | "
            f"{r['Composite']} | {r['ClosePos']}% | {r['Vol50d']}x | "
            f"{r['BaseRange']}% | {r['RSEdge']}% | {r['ResClear']}% |\n"
        )

    options_df = df_res[df_res['Score'] >= 7]
    if not options_df.empty:
        md += "\n---\n\n## 🎯 Budget Call Options Setups (Under ₹500)\n\n"
        md += "| Stock | Spot Price (₹) | Score | Option Strategy | Spot Target | Spot Stop Loss |\n"
        md += "| :--- | :---: | :---: | :--- | :---: | :---: |\n"
        for _, r in options_df.iterrows():
            md += f"| **{r['Stock']}** | ₹{r['Price']} | 🔥 {r['Score']}/10 | **{r['OptionContract']}** | {r['OptTarget']} | {r['OptSL']} |\n"

    with open("budgetsummary.md", "w", encoding="utf-8") as f:
        f.write(md)

if __name__ == "__main__":
    run()
