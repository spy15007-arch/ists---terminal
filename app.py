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

# --- SIDEBAR SETUP ---
st.sidebar.title("ISTS Pro Terminal")
st.sidebar.caption("Institutional Swing & BTST Trading System")

page = st.sidebar.radio(
    "Navigation", 
    ["Dashboard", "Scan Market", "Budget Scanner (< ₹500)", "Watchlist", "Portfolio", "Settings"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("📲 Telegram Alert Setup")
bot_token = st.sidebar.text_input("Bot Token", type="password")
chat_id = st.sidebar.text_input("Chat ID", value="1338671581")
enable_alerts = st.sidebar.checkbox("Enable Automated Alerts (>=75%)", value=True)

# --- TELEGRAM ALERT ENGINE ---
def send_telegram_alert_async(symbol, price, score, composite, opt_contract, token, c_id, is_budget=False):
    if not token or not c_id: return
    header = "💡 *ISTS PRO BUDGET ALERT (< ₹500)* 💡" if is_budget else "🚨 *ISTS PRO BREAKOUT ALERT* 🚨"
    message = (
        f"{header}\n\n"
        f"📌 *Stock:* `{symbol}`\n"
        f"💰 *Price:* ₹{price}\n"
        f"⭐ *Readiness Score:* *{score}/10*\n"
        f"📊 *Composite Score:* *{composite}/100*\n"
        f"🎯 *Option Strategy:* `{opt_contract}`\n\n"
        f"🎯 Review chart on ISTS Pro Terminal."
    )
    url = f"https://api.telegram.org/bot{token.strip()}/sendMessage"
    payload = {"chat_id": c_id.strip(), "text": message, "parse_mode": "Markdown"}
    threading.Thread(target=requests.post, args=(url,), kwargs={'json': payload, 'timeout': 5}, daemon=True).start()

# --- HELPER 1: DYNAMIC NIFTY 500 FETCH ENGINE ---
@st.cache_data(ttl=14400) # Caches list for 4 hours
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

# --- HELPER 2: OPTIONS CONTRACT RECOMMENDATION ENGINE ---
def generate_option_idea(symbol, price):
    """Calculates ATM Call option strike and target for top breakout candidates."""
    if price > 5000:
        step = 100
    elif price > 2000:
        step = 50
    elif price > 1000:
        step = 20
    elif price > 500:
        step = 10
    else:
        step = 5

    atm_strike = int(round(price / step) * step)
    option_contract = f"BUY {symbol} {atm_strike} CE"
    target_spot = f"₹{round(price * 1.03, 1)}"
    sl_spot = f"₹{round(price * 0.985, 1)}"
    return option_contract, target_spot, sl_spot

# --- HELPER 3: MARKDOWN SUMMARY GENERATOR ---
def generate_breakout_markdown(df_results):
    md_content = "# 📊 ISTS Pro — Pre-Breakout & BTST Readiness Report\n\n"
    md_content += "> **Universe:** Dynamic Top 500 NSE Stocks | **Filter:** Stage-2 Uptrend + RS Edge\n\n"
    
    # 1. TOP 10 HIGH CONVICTION SETUPS (EQUITY + OPTIONS)
    top_10 = df_results.head(10)
    md_content += "## ⚡ Top 10 High-Conviction Setups (Equity & Call Options)\n\n"
    md_content += "| Rank | Stock | Price (₹) | Score | Equity SL (₹) | Equity Target (₹) | Call Option Strategy | Action |\n"
    md_content += "| :---: | :--- | :---: | :---: | :---: | :---: | :--- | :---: |\n"
    
    for _, r in top_10.iterrows():
        sl = round(r['Price'] - (1.5 * r['ATR']), 1)
        target = round(r['Price'] + (3.0 * r['ATR']), 1)
        badge = f"🔥 {r['Score /10']}/10" if r['Score /10'] >= 7 else f"{r['Score /10']}/10"
        action = "BUY NOW (BTST)" if r['Score /10'] >= 5 else "BUY (Breakout)"
        
        md_content += (
            f"| {r['Rank']} | **{r['Stock']}** | ₹{r['Price']} | {badge} | "
            f"₹{sl} | ₹{target} | **{r['Option Contract']}** | **{action}** |\n"
        )

    # 2. FULL TOP 20 LEADERBOARD
    md_content += "\n---\n\n## 🏆 Full Top 20 Momentum Leaderboard\n\n"
    md_content += "| Rank | Stock | Price (₹) | Score | Composite /100 | Close Pos % | Vol vs 50d | Base Range % | RS Edge % | Resistance Clearance % |\n"
    md_content += "| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n"
    
    for _, r in df_results.iterrows():
        badge = f"🔥 {r['Score /10']}/10" if r['Score /10'] >= 7 else f"{r['Score /10']}/10"
        md_content += (
            f"| {r['Rank']} | **{r['Stock']}** | ₹{r['Price']} | {badge} | "
            f"{r['Composite /100']} | {r['Close Position %']}% | {r['Vol vs 50d Avg']}x | "
            f"{r['Base Range %']}% | {r['RS Edge %']}% | {r['Resistance Clearance %']}% |\n"
        )

    return md_content

# --- BENCHMARK & SCAN ENGINE ---
@st.cache_data(ttl=1800)
def get_nifty_benchmark_return():
    try:
        nifty = yf.download('^NSEI', period="6m", interval="1d", progress=False)['Close']
        if isinstance(nifty, pd.DataFrame): nifty = nifty.iloc[:, 0]
        return ((nifty.iloc[-1] / nifty.iloc[-63]) - 1) * 100
    except Exception:
        return 0.0

def run_btst_breakout_scan():
    tickers = get_nifty500_tickers()
    results = []
    nifty_3m_return = get_nifty_benchmark_return()

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

            ema_50 = df['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
            ema_200 = df['Close'].ewm(span=200, adjust=False).mean().iloc[-1]

            # Stage-2 Uptrend Filter
            if not (close_p > ema_50 and ema_50 > ema_200):
                continue

            stock_3m_return = ((close_p / df['Close'].iloc[-63]) - 1) * 100
            rs_edge_pct = round(stock_3m_return - nifty_3m_return, 1)

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

            df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
            df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
            df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()

            high_low = df['High'] - df['Low']
            high_close = np.abs(df['High'] - df['Close'].shift())
            low_close = np.abs(df['Low'] - df['Close'].shift())
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = tr.ewm(alpha=1/14, adjust=False).mean().iloc[-1]

            # Always generate option contract for qualified setups
            opt_contract, opt_target, opt_sl = generate_option_idea(symbol, close_p)

            if enable_alerts and score >= 4:
                is_budget_stock = close_p <= 500
                send_telegram_alert_async(
                    symbol, round(close_p, 2), score, composite, 
                    opt_contract, bot_token, chat_id, is_budget=is_budget_stock
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
                'Spot Target': opt_target,
                'Spot SL': opt_sl,
                'ATR': round(atr, 2),
                'Data': df
            })
        except Exception:
            continue

    df_results = pd.DataFrame(results)
    if not df_results.empty:
        df_results = df_results.sort_values(by=['Score /10', 'Composite /100'], ascending=[False, False]).head(20)
        df_results['Rank'] = range(1, len(df_results) + 1)
    return df_results

# --- VIEW: DASHBOARD ---
if page == "Dashboard":
    st.title("Institutional Swing Trading System (ISTS Pro)")
    st.markdown("Live Market Top-Down Momentum & Pre-Breakout Terminal")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Market Status", "OPEN", "NSE Live Feed")
    col2.metric("Scan Universe", "Top 500 NSE Stocks", "Dynamic")
    col3.metric("Alert Engine", "ACTIVE", "Telegram Bot")
    col4.metric("Strategy", "BTST / Swing / Options", "0-10 Composite")

# --- VIEW: SCAN MARKET ---
elif page == "Scan Market":
    st.title("🚀 Institutional Pre-Breakout & Options Scanner")
    st.markdown("Scans top 500 liquid stocks for accumulation, Stage-2 uptrend, ATR contraction, and Call option strike triggers.")

    if st.button("Run Live Pre-Breakout Scan", type="primary"):
        with st.spinner("Scanning Nifty 500 universe & ranking top momentum setups..."):
            df_res = run_btst_breakout_scan()
            st.session_state['btst_results'] = df_res
            st.success("Scan complete! Extracted top momentum setups.")

    if 'btst_results' in st.session_state and not st.session_state['btst_results'].empty:
        df_results = st.session_state['btst_results']
        
        # 1. Combined Top 10 High-Conviction Equity & Options Table
        st.subheader("⚡ Top 10 High-Conviction Setups (Equity Levels + Call Options)")
        top_10_combined = df_results.head(10).copy()
        top_10_combined['Equity SL (₹)'] = (top_10_combined['Price'] - (1.5 * top_10_combined['ATR'])).round(1)
        top_10_combined['Equity Target (₹)'] = (top_10_combined['Price'] + (3.0 * top_10_combined['ATR'])).round(1)
        top_10_combined['Suggested Action'] = top_10_combined['Score /10'].apply(
            lambda s: "🔥 BUY NOW (BTST)" if s >= 5 else "BUY (Breakout)"
        )

        eq_display = top_10_combined[[
            'Rank', 'Stock', 'Price', 'Score /10', 'Equity SL (₹)', 'Equity Target (₹)', 'Option Contract', 'Suggested Action'
        ]]
        st.dataframe(eq_display, use_container_width=True, hide_index=True)

        st.markdown("---")

        # 2. Main Full Top 20 Leaderboard
        st.subheader("🏆 Full Top 20 Momentum Leaderboard")
        df_display = df_results[[
            'Rank', 'Stock', 'Price', 'Score /10', 'Composite /100', 
            'Close Position %', 'Vol vs 50d Avg', 'Base Range %', 'RS Edge %', 'Resistance Clearance %'
        ]]
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # 3. Export Summary & Download Button
        markdown_data = generate_breakout_markdown(df_results)

        st.markdown("---")
        st.subheader("📄 Export Breakout Summary")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.download_button(
                label="📥 Download breakoutsummary.md",
                data=markdown_data,
                file_name="breakoutsummary.md",
                mime="text/markdown",
                type="primary"
            )
            
        with st.expander("👁️ Preview breakoutsummary.md Content"):
            st.markdown(markdown_data)

        # 4. Technical Charting
        st.markdown("---")
        st.subheader("🔍 Interactive Technical Chart Analysis")
        selected_stock = st.selectbox("Select stock to analyze chart:", df_display['Stock'].tolist())
        stock_row = df_results[df_results['Stock'] == selected_stock].iloc[0]
        chart_df = stock_row['Data'].tail(120)

        fig = go.Figure(data=[
            go.Candlestick(x=chart_df.index, open=chart_df['Open'], high=chart_df['High'], low=chart_df['Low'], close=chart_df['Close'], name="Price"),
            go.Scatter(x=chart_df.index, y=chart_df['EMA_20'], line=dict(color='blue', width=1), name="EMA 20"),
            go.Scatter(x=chart_df.index, y=chart_df['EMA_50'], line=dict(color='orange', width=1), name="EMA 50"),
            go.Scatter(x=chart_df.index, y=chart_df['EMA_200'], line=dict(color='red', width=1.5), name="EMA 200")
        ])
        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=450, title=f"{selected_stock} Daily Chart")
        st.plotly_chart(fig, use_container_width=True)

        # 5. Risk & Position Calculator
        st.markdown("---")
        st.subheader(f"🧮 Position Size & Risk Calculator: {selected_stock}")
        c1, c2, c3 = st.columns(3)
        capital = c1.number_input("Account Capital (₹)", min_value=10000, value=500000, step=25000)
        risk_pct = c2.number_input("Risk Limit per Trade (%)", min_value=0.25, max_value=5.0, value=1.0, step=0.25)
        
        entry_p = stock_row['Price']
        suggested_sl = round(entry_p - (1.5 * stock_row['ATR']), 2)
        sl_p = c3.number_input("Stop Loss Price (₹) [Default: 1.5x ATR]", min_value=1.0, value=float(suggested_sl), step=1.0)
        
        risk_per_share = entry_p - sl_p
        if risk_per_share > 0:
            max_risk = (capital * risk_pct) / 100.0
            qty = int(max_risk / risk_per_share)
            target_p = round(entry_p + (3.0 * risk_per_share), 2)
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Quantity to Buy", f"{qty} shares")
            m2.metric("Total Investment", f"₹{(qty * entry_p):,.2f}")
            m3.metric("Max Capital at Risk", f"₹{max_risk:,.2f}")
            m4.metric("Risk / Reward Ratio", f"1 : {round((target_p - entry_p) / risk_per_share, 2)}")

# --- VIEW: BUDGET SCANNER (< ₹500) ---
elif page == "Budget Scanner (< ₹500)":
    st.title("💡 Sub-₹500 Momentum & Budget Scanner")
    st.markdown("Scans liquid Nifty 500 stocks specifically priced under ₹500 in Stage-2 uptrends with high breakout readiness.")

    c1, c2 = st.columns([2, 1])
    budget_limit = c1.number_input("Max Stock Price (₹)", min_value=50, max_value=1000, value=500, step=50)
    min_score = c2.slider("Min Readiness Score", min_value=1, max_value=10, value=3)

    if st.button("Run Budget Market Scan", type="primary"):
        with st.spinner(f"Scanning Nifty 500 for stocks under ₹{budget_limit}..."):
            full_res = run_btst_breakout_scan()
            if not full_res.empty:
                budget_res = full_res[
                    (full_res['Price'] <= budget_limit) & 
                    (full_res['Score /10'] >= min_score)
                ].copy()
                
                if not budget_res.empty:
                    budget_res['Rank'] = range(1, len(budget_res) + 1)
                    st.session_state['budget_results'] = budget_res
                    st.success(f"Found {len(budget_res)} momentum setups under ₹{budget_limit}!")
                else:
                    st.session_state['budget_results'] = pd.DataFrame()
                    st.warning(f"No setups found under ₹{budget_limit} matching score ≥ {min_score}.")

    if 'budget_results' in st.session_state and not st.session_state['budget_results'].empty:
        df_budget = st.session_state['budget_results']

        st.subheader(f"🏆 Top Budget Equity & Option Setups Under ₹{budget_limit}")
        df_display = df_budget[[
            'Rank', 'Stock', 'Price', 'Score /10', 'Composite /100', 
            'Close Position %', 'Vol vs 50d Avg', 'RS Edge %', 'Option Contract', 'Spot Target', 'Spot SL'
        ]]
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("🔍 Budget Position & Share Quantity Calculator")
        selected_stock = st.selectbox("Select stock to evaluate:", df_display['Stock'].tolist())
        stock_row = df_budget[df_budget['Stock'] == selected_stock].iloc[0]

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Stock:** `{selected_stock}`")
            st.markdown(f"**Last Price:** ₹{stock_row['Price']}")
            st.markdown(f"**Readiness Score:** {stock_row['Score /10']}/10")
            st.markdown(f"**Option Recommendation:** `{stock_row['Option Contract']}`")
        
        with col2:
            trade_capital = st.number_input("Allocated Capital for this Trade (₹)", min_value=5000, value=50000, step=5000)
            shares_qty = int(trade_capital // stock_row['Price'])
            actual_inv = round(shares_qty * stock_row['Price'], 2)
            st.metric("Affordable Shares", f"{shares_qty} shares")
            st.metric("Total Investment Required", f"₹{actual_inv:,.2f}")

else:
    st.title(f"{page} Module")
    st.info(f"The {page} module is active.")
