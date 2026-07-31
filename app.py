import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import threading
import io

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="ISTS Pro Dashboard",
    page_icon="📈",
    layout="wide"
)

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("ISTS Pro Terminal")
st.sidebar.caption("Institutional Swing & BTST Trading System")

page = st.sidebar.radio(
    "Navigation", 
    ["Dashboard", "Strict ISTS Scan", "Aggressive Momentum Scan", "Budget Scanner (< ₹500)", "Watchlist", "Settings"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("📲 Telegram Alert Setup")
bot_token = st.sidebar.text_input("Bot Token", type="password")
chat_id = st.sidebar.text_input("Chat ID", value="1338671581")
enable_alerts = st.sidebar.checkbox("Enable Automated Alerts", value=True)

# --- TELEGRAM ALERT ENGINE ---
def send_telegram_alert_async(symbol, price, score, composite, opt_contract, token, c_id, mode="Strict"):
    if not token or not c_id: return
    header = f"🚨 *ISTS PRO {mode.upper()} BREAKOUT ALERT* 🚨"
    message = (
        f"{header}\n\n"
        f"📌 *Stock:* `{symbol}`\n"
        f"💰 *Price:* ₹{price}\n"
        f"⭐ *Score:* *{score}/10*\n"
        f"📊 *Composite:* *{composite}/100*\n"
        f"🎯 *Option:* `{opt_contract}`\n\n"
        f"🎯 Review chart on ISTS Pro Terminal."
    )
    url = f"https://api.telegram.org/bot{token.strip()}/sendMessage"
    payload = {"chat_id": c_id.strip(), "text": message, "parse_mode": "Markdown"}
    threading.Thread(target=requests.post, args=(url,), kwargs={'json': payload, 'timeout': 5}, daemon=True).start()

# --- HELPER 1: DYNAMIC NIFTY 500 FETCH ENGINE ---
@st.cache_data(ttl=14400)
def get_nifty500_tickers():
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        df = pd.read_csv(io.StringIO(response.text))
        return [f"{symbol}.NS" for symbol in df['Symbol'].tolist()]
    except Exception:
        fallback = [
            'TVSMOTOR', 'COFORGE', 'HAL', 'BEL', 'DIXON', 'TRENT', 'MCX', 'PERSISTENT',
            'BHARTIARTL', 'RELIANCE', 'SBIN', 'ICICIBANK', 'HDFCBANK', 'TATAMOTORS',
            'INFY', 'TCS', 'LT', 'MARUTI', 'AXISBANK', 'M&M', 'SUNPHARMA', 'TITAN',
            'KALYANKJIL', 'SAREGAMA', 'JYOTICNC', 'FEDERALBNK', 'IEX', 'BHARTIHEXA',
            'LALPATHLAB', 'DIVISLAB', 'PARADEEP', 'PCBL', 'FSL', 'SONATSOFTW', 'RADICO'
        ]
        return [f"{s}.NS" for s in fallback]

# --- HELPER 2: INDEX OPTIONS STRATEGY ENGINE ---
def get_index_options_ideas():
    ideas = []
    indices = [
        ('NIFTY 50', '^NSEI', 50),
        ('BANK NIFTY', '^NSEBANK', 100)
    ]
    for name, symbol, step in indices:
        try:
            df = yf.download(symbol, period="1mo", interval="1d", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if not df.empty:
                close_p = df['Close'].iloc[-1]
                ema_20 = df['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
                atm_strike = int(round(close_p / step) * step)
                
                if close_p >= ema_20:
                    bias = "🟢 BULLISH (Above EMA20)"
                    contract = f"BUY {name.replace(' ', '')} {atm_strike} CE"
                    target = f"₹{round(close_p * 1.01, 1)}"
                    sl = f"₹{round(close_p * 0.995, 1)}"
                else:
                    bias = "🔴 BEARISH (Below EMA20)"
                    contract = f"BUY {name.replace(' ', '')} {atm_strike} PE"
                    target = f"₹{round(close_p * 0.99, 1)}"
                    sl = f"₹{round(close_p * 1.005, 1)}"
                
                ideas.append({
                    'Index': name,
                    'Spot Price': round(close_p, 2),
                    'Trend Bias': bias,
                    'Recommended Option': contract,
                    'Spot Target': target,
                    'Spot Stop Loss': sl
                })
        except Exception:
            continue
    return pd.DataFrame(ideas)

# --- HELPER 3: STOCK OPTIONS CALCULATOR ---
def generate_option_idea(symbol, price):
    step = 100 if price > 5000 else (50 if price > 2000 else (20 if price > 1000 else (10 if price > 500 else 5)))
    atm_strike = int(round(price / step) * step)
    return f"BUY {symbol} {atm_strike} CE"

# --- HELPER 4: MARKDOWN REPORT GENERATOR ---
def generate_breakout_markdown(df_results, df_index, mode_label="ISTS Pro"):
    md_content = f"# 📊 {mode_label} — Live Market & Options Report\n\n"
    
    if not df_index.empty:
        md_content += "## 🏛️ Live Index Options Recommendations\n\n"
        md_content += "| Index | Spot Price (₹) | Trend Bias | Recommended Option | Spot Target | Spot Stop Loss |\n"
        md_content += "| :--- | :---: | :---: | :--- | :---: | :---: |\n"
        for _, r in df_index.iterrows():
            md_content += f"| **{r['Index']}** | ₹{r['Spot Price']} | {r['Trend Bias']} | **{r['Recommended Option']}** | {r['Spot Target']} | {r['Spot Stop Loss']} |\n"
        md_content += "\n---\n\n"

    md_content += "## 🏆 Top 25 Momentum & Options Leaderboard\n\n"
    md_content += "| Rank | Stock | Price (₹) | Score | Equity SL (₹) | Equity Target (₹) | Call Option Strategy | Action |\n"
    md_content += "| :---: | :--- | :---: | :---: | :---: | :---: | :--- | :---: |\n"
    
    for _, r in df_results.iterrows():
        sl = round(r['Price'] - (1.5 * r['ATR']), 1)
        target = round(r['Price'] + (3.0 * r['ATR']), 1)
        badge = f"🔥 {r['Score /10']}/10" if r['Score /10'] >= 5 else f"{r['Score /10']}/10"
        action = "BUY NOW (BTST)" if r['Score /10'] >= 5 else "BUY (Breakout)"
        
        md_content += (
            f"| {r['Rank']} | **{r['Stock']}** | ₹{r['Price']} | {badge} | "
            f"₹{sl} | ₹{target} | **{r['Option Contract']}** | **{action}** |\n"
        )

    return md_content

# --- SCANNER ENGINE (SUPPORTS STRICT AND AGGRESSIVE MODES) ---
@st.cache_data(ttl=1800)
def get_nifty_benchmark_return():
    try:
        nifty = yf.download('^NSEI', period="6m", interval="1d", progress=False)['Close']
        if isinstance(nifty, pd.DataFrame): nifty = nifty.iloc[:, 0]
        return ((nifty.iloc[-1] / nifty.iloc[-63]) - 1) * 100
    except Exception:
        return 0.0

def run_scan(mode="strict"):
    tickers = get_nifty500_tickers()
    results = []
    nifty_3m = get_nifty_benchmark_return()

    data = yf.download(tickers, period="1y", interval="1d", group_by='ticker', progress=False)

    for ticker in tickers:
        symbol = ticker.replace(".NS", "")
        try:
            df = data[ticker].dropna() if len(tickers) > 1 else data.dropna()
            if len(df) < 200: continue

            close_p = df['Close'].iloc[-1]
            high_p = df['High'].iloc[-1]
            low_p = df['Low'].iloc[-1]
            vol_today = df['Volume'].iloc[-1]

            ema_20 = df['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
            ema_50 = df['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
            ema_200 = df['Close'].ewm(span=200, adjust=False).mean().iloc[-1]

            if not (close_p > ema_50 and ema_50 > ema_200): continue

            stock_3m_return = ((close_p / df['Close'].iloc[-63]) - 1) * 100
            rs_edge_pct = round(stock_3m_return - nifty_3m, 1)
            if rs_edge_pct < 0: continue

            close_pos = round(((close_p - low_p) / (high_p - low_p)) * 100, 1) if high_p != low_p else 50.0
            vol_50d_avg = df['Volume'].rolling(50).mean().iloc[-1]
            vol_vs_50d = round(vol_today / vol_50d_avg, 2) if vol_50d_avg > 0 else 1.0

            high_50d = df['High'].rolling(50).max().iloc[-1]
            low_50d = df['Low'].rolling(50).min().iloc[-1]
            base_range_pct = round(((high_50d - low_50d) / low_50d) * 100, 1)
            resistance_clearance = round(((high_50d - close_p) / close_p) * 100, 1) if high_50d > close_p else 0.0

            # SCORING ENGINE DIVERGENCE
            if mode == "strict":
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
            else:
                # AGGRESSIVE MODE (Generates 7-10 scores consistently)
                score = 2
                if close_p > ema_20: score += 2
                if vol_vs_50d >= 1.3: score += 2
                elif vol_vs_50d >= 1.1: score += 1
                if close_pos >= 70: score += 2
                elif close_pos >= 50: score += 1
                if resistance_clearance <= 3.0: score += 2

            score = min(10, score)

            composite = round(
                (close_pos * 0.25) + 
                (min(vol_vs_50d * 15, 30)) + 
                (max(0, 25 - base_range_pct * 0.5)) + 
                (min(max(0, rs_edge_pct), 20)), 
                1
            )

            df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
            df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
            df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()

            high_low = df['High'] - df['Low']
            high_close = np.abs(df['High'] - df['Close'].shift())
            low_close = np.abs(df['Low'] - df['Close'].shift())
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = tr.ewm(alpha=1/14, adjust=False).mean().iloc[-1]

            opt_contract = generate_option_idea(symbol, close_p)

            if enable_alerts and score >= 4:
                is_budget_stock = close_p <= 500
                send_telegram_alert_async(
                    symbol, round(close_p, 2), score, composite, 
                    opt_contract, bot_token, chat_id, mode=mode
                )

            results.append({
                'Stock': symbol,
                'Price': round(close_p, 2),
                'Score /10': score,
                'Composite /100': composite,
                'Close Position %': close_pos,
                'Vol vs 50d Avg': vol_vs_50d,
                'Base Range %': base_range_pct,
                'RS Edge %': rs_edge_pct,
                'Resistance Clearance %': resistance_clearance,
                'Option Contract': opt_contract,
                'ATR': round(atr, 2),
                'Data': df
            })
        except Exception:
            continue

    df_results = pd.DataFrame(results)
    if not df_results.empty:
        df_results = df_results.sort_values(by=['Score /10', 'Composite /100'], ascending=[False, False]).head(25)
        df_results['Rank'] = range(1, len(df_results) + 1)
    return df_results

# --- VIEW 1: DASHBOARD ---
if page == "Dashboard":
    st.title("Institutional Swing Trading System (ISTS Pro)")
    st.markdown("Live Market Top-Down Momentum & Pre-Breakout Terminal")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Market Status", "OPEN", "NSE Live Feed")
    col2.metric("Scan Universe", "Top 500 NSE Stocks", "Dynamic")
    col3.metric("Alert Engine", "ACTIVE", "Telegram Bot")
    col4.metric("Strategy", "BTST / Swing / Options", "Dual Scoring Engine")

# --- VIEW 2: STRICT ISTS SCAN ---
elif page == "Strict ISTS Scan":
    st.title("🛡️ Strict ISTS Pro Scanner")
    st.caption("Institutional grade. High scores (8-10/10) trigger only during massive volume breakouts.")

    if st.button("Run Strict Market Scan", type="primary"):
        with st.spinner("Scanning Nifty 500 under strict rules..."):
            df_index = get_index_options_ideas()
            df_res = run_scan(mode="strict")
            st.session_state['strict_index'] = df_index
            st.session_state['strict_res'] = df_res
            st.success("Strict scan finished!")

    if 'strict_index' in st.session_state and not st.session_state['strict_index'].empty:
        st.subheader("🏛️ Live Index Options Trade Recommendations")
        st.dataframe(st.session_state['strict_index'], use_container_width=True, hide_index=True)
        st.markdown("---")

    if 'strict_res' in st.session_state and not st.session_state['strict_res'].empty:
        df_results = st.session_state['strict_res']
        st.subheader("🏆 Top 25 Strict Momentum & Options Leaderboard")
        
        display_df = df_results.copy()
        display_df['Equity SL (₹)'] = (display_df['Price'] - (1.5 * display_df['ATR'])).round(1)
        display_df['Equity Target (₹)'] = (display_df['Price'] + (3.0 * display_df['ATR'])).round(1)
        display_df['Suggested Action'] = display_df['Score /10'].apply(lambda s: "🔥 BUY NOW (BTST)" if s >= 5 else "BUY (Breakout)")

        st.dataframe(
            display_df[['Rank', 'Stock', 'Price', 'Score /10', 'Equity SL (₹)', 'Equity Target (₹)', 'Option Contract', 'Suggested Action']], 
            use_container_width=True, 
            hide_index=True
        )

# --- VIEW 3: AGGRESSIVE MOMENTUM SCAN ---
elif page == "Aggressive Momentum Scan":
    st.title("⚡ Aggressive Momentum Scanner")
    st.caption("High sensitivity. Designed to produce 7/10 to 10/10 readiness scores every trading session.")

    if st.button("Run Aggressive Market Scan", type="primary"):
        with st.spinner("Scanning Nifty 500 under aggressive sensitivity..."):
            df_index = get_index_options_ideas()
            df_res = run_scan(mode="aggressive")
            st.session_state['agg_index'] = df_index
            st.session_state['agg_res'] = df_res
            st.success("Aggressive scan finished!")

    if 'agg_index' in st.session_state and not st.session_state['agg_index'].empty:
        st.subheader("🏛️ Live Index Options Trade Recommendations")
        st.dataframe(st.session_state['agg_index'], use_container_width=True, hide_index=True)
        st.markdown("---")

    if 'agg_res' in st.session_state and not st.session_state['agg_res'].empty:
        df_results = st.session_state['agg_res']
        st.subheader("🏆 Top 25 Aggressive Momentum Leaderboard (High Scores)")
        
        display_df = df_results.copy()
        display_df['Equity SL (₹)'] = (display_df['Price'] - (1.5 * display_df['ATR'])).round(1)
        display_df['Equity Target (₹)'] = (display_df['Price'] + (3.0 * display_df['ATR'])).round(1)
        display_df['Suggested Action'] = display_df['Score /10'].apply(lambda s: "🔥 BUY NOW (BTST)" if s >= 7 else "BUY (Swing)")

        st.dataframe(
            display_df[['Rank', 'Stock', 'Price', 'Score /10', 'Equity SL (₹)', 'Equity Target (₹)', 'Option Contract', 'Suggested Action']], 
            use_container_width=True, 
            hide_index=True
        )

# --- VIEW 4: BUDGET SCANNER (< ₹500) ---
elif page == "Budget Scanner (< ₹500)":
    st.title("💡 Sub-₹500 Momentum & Budget Scanner")
    st.markdown("Scans liquid Nifty 500 stocks specifically priced under ₹500 in Stage-2 uptrends.")

    c1, c2 = st.columns([2, 1])
    budget_limit = c1.number_input("Max Stock Price (₹)", min_value=50, max_value=1000, value=500, step=50)
    min_score = c2.slider("Min Readiness Score", min_value=1, max_value=10, value=3)

    if st.button("Run Budget Market Scan", type="primary"):
        with st.spinner(f"Scanning Nifty 500 for stocks under ₹{budget_limit}..."):
            full_res = run_scan(mode="strict")
            if not full_res.empty:
                budget_res = full_res[
                    (full_res['Price'] <= budget_limit) & 
                    (full_res['Score /10'] >= min_score)
                ].copy()
                
                if not budget_res.empty:
                    budget_res['Rank'] = range(1, len(budget_res) + 1)
                    st.session_state['budget_results'] = budget_res
                    st.success(f"Found {len(budget_res)} momentum setups under ₹{budget_limit}!")

    if 'budget_results' in st.session_state and not st.session_state['budget_results'].empty:
        df_budget = st.session_state['budget_results']
        st.subheader(f"🏆 Top Budget Equity & Option Setups Under ₹{budget_limit}")
        st.dataframe(
            df_budget[['Rank', 'Stock', 'Price', 'Score /10', 'Composite /100', 'Close Position %', 'Vol vs 50d Avg', 'Option Contract']], 
            use_container_width=True, 
            hide_index=True
        )

else:
    st.title(f"{page} Module")
    st.info(f"The {page} module is active.")
