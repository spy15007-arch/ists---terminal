import yfinance as yf
import pandas as pd
import numpy as np

# Nifty 50 / FnO Core Scanner Universe
NIFTY_UNIVERSE = [
    'BHARTIARTL', 'RELIANCE', 'SBIN', 'ICICIBANK', 'HDFCBANK', 'TATAMOTORS',
    'TVSMOTOR', 'COFORGE', 'INFY', 'TCS', 'HAL', 'BEL', 'LT', 'MARUTI'
]

def run():
    results = []
    
    # 1. Benchmark Return (Nifty 50 3-Month Return)
    try:
        nifty = yf.download('^NSEI', period="6m", interval="1d", progress=False)['Close']
        if isinstance(nifty, pd.DataFrame): 
            nifty = nifty.iloc[:, 0]
        nifty_3m = ((nifty.iloc[-1] / nifty.iloc[-63]) - 1) * 100
    except Exception:
        nifty_3m = 0.0

    # 2. Iterate and Evaluate Each Stock
    for symbol in NIFTY_UNIVERSE:
        try:
            data = yf.download(f"{symbol}.NS", period="1y", interval="1d", progress=False)
            if len(data) < 70: 
                continue
            if isinstance(data.columns, pd.MultiIndex): 
                data.columns = data.columns.get_level_values(0)

            close_p = data['Close'].iloc[-1]
            high_p = data['High'].iloc[-1]
            low_p = data['Low'].iloc[-1]
            vol_today = data['Volume'].iloc[-1]

            # Technical Metrics
            close_pos = round(((close_p - low_p) / (high_p - low_p)) * 100, 1) if high_p != low_p else 50.0
            vol_50d_avg = data['Volume'].rolling(50).mean().iloc[-1]
            vol_vs_50d = round(vol_today / vol_50d_avg, 2) if vol_50d_avg > 0 else 1.0

            high_50d = data['High'].rolling(50).max().iloc[-1]
            low_50d = data['Low'].rolling(50).min().iloc[-1]
            base_range_pct = round(((high_50d - low_50d) / low_50d) * 100, 1)

            stock_3m_return = ((close_p / data['Close'].iloc[-63]) - 1) * 100
            rs_edge_pct = round(stock_3m_return - nifty_3m, 1)
            resistance_clearance = round(((high_50d - close_p) / close_p) * 100, 1) if high_50d > close_p else 0.0

            # 0 - 10 Readiness Score Calculation
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

            results.append({
                'Stock': symbol, 
                'Price': round(close_p, 2), 
                'Score': score,
                'Composite': composite, 
                'ClosePos': close_pos, 
                'Vol50d': vol_vs_50d,
                'BaseRange': base_range_pct, 
                'RSEdge': rs_edge_pct, 
                'ResClear': resistance_clearance
            })
        except Exception:
            continue

    # 3. Sort & Build Markdown Output
    df = pd.DataFrame(results).sort_values(by=['Score', 'Composite'], ascending=[False, False])
    df['Rank'] = range(1, len(df) + 1)

    md = "# 📊 ISTS Pro - Pre-Breakout & BTST Readiness Report\n\n"
    md += "## 🏆 Stock Leaderboard (Ranked Best to Weakest)\n\n"
    md += "| Rank | Stock | Price (₹) | Readiness Score | Composite /100 | Close Pos % | Vol vs 50d | Base Range % | RS Edge % | Resistance Clearance % |\n"
    md += "| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n"
    
    for _, r in df.iterrows():
        score_badge = f"🔥 {r['Score']}/10" if r['Score'] >= 8 else f"{r['Score']}/10"
        md += (
            f"| {r['Rank']} | **{r['Stock']}** | ₹{r['Price']} | {score_badge} | "
            f"{r['Composite']} | {r['ClosePos']}% | {r['Vol50d']}x | "
            f"{r['BaseRange']}% | {r['RSEdge']}% | {r['ResClear']}% |\n"
        )

    # 4. Write breakoutsummary.md
    with open("breakoutsummary.md", "w", encoding="utf-8") as f:
        f.write(md)

if __name__ == "__main__":
    run()
