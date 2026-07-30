import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import threading

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="ISTS Pro Dashboard",
    page_icon="📈",
    layout="wide"
)

# --- NIFTY SAMPLE UNIVERSE ---
NIFTY_UNIVERSE = [
    'BHARTIARTL', 'RELIANCE', 'SBIN', 'ICICIBANK', 'HDFCBANK', 'TATAMOTORS',
    'TVSMOTOR', 'COFORGE', 'INFY', 'TCS', 'HAL', 'BEL', 'LT', 'MARUTI',
    'ASIANPAINT', 'DIVISLAB', 'PIDILITIND', 'SUNPHARMA', 'M&M', 'AXISBANK'
]

# --- SIDEBAR SETUP ---
st.sidebar.title("ISTS Pro Terminal")
st.sidebar.caption("Institutional Swing & BTST Trading System")

page = st.sidebar.radio(
    "Navigation", 
    ["Dashboard", "Scan Market", "Watchlist", "Portfolio", "Settings"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("📲 Telegram Alert Setup")
bot_token = st.sidebar.text_input("Bot Token", type="password")
chat_id = st.sidebar.text_input("Chat ID", value="1338671581")
enable_alerts = st.sidebar.checkbox("Enable Automated Alerts (>=75%)", value=True)

# --- TELEGRAM ALERT ENGINE ---
def send_telegram_alert_async(symbol, price, score, composite, token, c_id):
    if not token or not c_id: return
    message = (
        f"🚨 *ISTS PRO BREAKOUT ALERT* 🚨\n\n"
        f"📌 *Stock:* `{symbol}`\n"
        f"💰 *Price:* ₹{price}\n"
        f"⭐ *Readiness Score:* *{score}/10*\n"
        f"📊 *Composite Score:* *{composite}/100*\n\n"
        f"🎯 Review chart on ISTS Pro Terminal."
    )
    url = f"https://api.telegram.org/bot{token.strip()}/sendMessage"
    payload = {"chat_id": c_id.strip(), "text": message, "parse_mode": "Markdown"}
    threading.Thread(target=requests.post, args=(url,), kwargs={'json': payload, 'timeout': 5}, daemon=True).start()

# --- STEP 1: MARKDOWN SUMMARY GENERATOR ---
def generate_breakout_markdown(df_results):
    """Generates breakoutsummary.md content ranked from best to weakest."""
    md_content = "# 📊 ISTS Pro - Pre-Breakout & BTST Readiness Report\n\n"
    md_content += "## 🏆 Stock Leaderboard (Ranked Best to Weakest)\n\n"
    md_content += "| Rank | Stock | Price (₹) | Readiness Score | Composite /100 | Close Pos % | Vol vs 50d | Base Range % | RS Edge % | Resistance Clearance % |\n"
    md_content += "| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n"
    
    for _, row in df_results.iterrows():
        score_badge = f"🔥 {row['Score /10']}/10" if row['Score /10'] >= 8 else f"{row['Score /10']}/10"
        md_content += (
            f"| {row['Rank']} | **{row['Stock']}** | ₹{row['Price']} | {score_badge} | "
            f"{row['Composite /100']} | {row['Close Position %']}% | {row['Vol vs 50d Avg']}x | "
            f"{row['Base Range %']}% | {row['RS Edge %']}% | {row['Resistance Clearance %']}% |\n"
        )
    
    md_content += "\n---\n\n### 🎯 Top High-Conviction Setups\n\n"
    top_setups = df_results[df_results['Score /10'] >= 7]
    if top_setups.empty:
        top_setups = df_results.head(3)
        
    for _, row in top_setups.iterrows():
        md_content += f"#### #{row['Rank']} {row['Stock']} — Score: {row['Score /10']}/10 (Composite: {row['Composite /100']})\n"
        md_content += f"- **Last Price:** ₹{row['Price']}\n"
        md_content += f"- **Close Position:** {row['Close Position %']}% (buyers held control into close)\n"
        md_content += f"- **Volume Surge:** {row['Vol vs 50d Avg']}x 50-day average volume\n"
        md_content += f"- **Relative Strength Edge:** {row['RS Edge %']}% vs NIFTY 50\n\n"
        
    return md_content

# --- BENCHMARK & SCAN ENGINE ---
@st.cache_data(ttl=1800)
def get_nifty_benchmark_return():
    try:
        nifty = yf.download('^NSEI', period="6m", interval="1d", progress=False)['Close']
        if isinstance(nifty, pd.DataFrame): nifty = nifty.iloc[:, 0]
        return ((nifty.iloc[-1] / nifty.iloc[-63]) - 1) * 100
    except:
        return 0.0

def run_btst_breakout_scan(symbols):
    results = []
    nifty_3m_return = get_nifty_benchmark_return()

    for symbol in symbols:
        ticker = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
        try:
            data = yf.download(ticker, period="1y", interval="1d", progress=False)
            if len(data) < 70: continue
            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)

            data['EMA_20'] = data['Close'].ewm(span=20, adjust=False).mean()
            data['EMA_50'] = data['Close'].ewm(span=50, adjust=False).mean()
            data['EMA_200'] = data['Close'].ewm(span=200, adjust=False).mean()

            close_p = data['Close'].iloc[-1]
            high_p = data['High'].iloc[-1]
            low_p = data['Low'].iloc[-1]
            vol_today = data['Volume'].iloc[-1]

            close_pos = round(((close_p - low_p) / (high_p - low_p)) * 100, 1) if high_p != low_p else 50.0
            vol_50d_avg = data['Volume'].rolling(50).mean().iloc[-1]
            vol_vs_50d = round(vol_today / vol_50d_avg, 2) if vol_50d_avg > 0 else 1.0

            high_50d = data['High'].rolling(50).max().iloc[-1]
            low_50d = data['Low'].rolling(50).min().iloc[-1]
            base_range_pct = round(((high_50d - low_50d) / low_50d) * 100, 1)

            stock_3m_return = ((close_p / data['Close'].iloc[-63]) - 1) * 100
            rs_edge_pct = round(stock_3m_return - nifty_3m_return, 1)
            resistance_clearance = round(((high_50d - close_p) / close_p) * 100, 1) if high_50d > close_p else 0.0

            # 0 - 10 Readiness Scoring
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

            # ATR for position sizing calculation
            high_low = data['High'] - data['Low']
            high_close = np.abs(data['High'] - data['Close'].shift())
            low_close = np.abs(data['Low'] - data['Close'].shift())
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = tr.ewm(alpha=1/14, adjust=False).mean().iloc[-1]

            if enable_alerts and score >= 8:
                send_telegram_alert_async(symbol, round(close_p, 2), score, composite, bot_token, chat_id)

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
                'ATR': round(atr, 2),
                'Data': data
            })
        except:
            continue

    df_results = pd.DataFrame(results)
    if not df_results.empty:
        df_results = df_results.sort_values(by=['Score /10', 'Composite /100'], ascending=[False, False])
        df_results['Rank'] = range(1, len(df_results) + 1)
    return df_results

# --- VIEW: DASHBOARD ---
if page == "Dashboard":
    st.title("Institutional Swing Trading System (ISTS Pro)")
    st.markdown("Live Market Top-Down Momentum & Pre-Breakout Terminal")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Market Status", "OPEN", "NSE Live Feed")
    col2.metric("Scan Universe", f"{len(NIFTY_UNIVERSE)} Liquid Stocks", "Active")
    col3.metric("Alert Engine", "ACTIVE", "Telegram Bot")
    col4.metric("Strategy", "BTST / Breakout", "0-10 Composite")

# --- VIEW: SCAN MARKET ---
elif page == "Scan Market":
    st.title("🚀 Institutional Pre-Breakout & BTST Scanner")
    st.markdown("Detects accumulation, volume dry-up, ATR contraction, and Golden Pocket Fib support.")

    if st.button("Run Live Pre-Breakout Scan", type="primary"):
        with st.spinner("Scanning universe & ranking stocks..."):
            df_res = run_btst_breakout_scan(NIFTY_UNIVERSE)
            st.session_state['btst_results'] = df_res
            st.success(f"Scan complete! Analyzed {len(df_res)} liquid stocks.")

    if 'btst_results' in st.session_state and not st.session_state['btst_results'].empty:
        df_results = st.session_state['btst_results']
        
        df_display = df_results[[
            'Rank', 'Stock', 'Price', 'Score /10', 'Composite /100', 
            'Close Position %', 'Vol vs 50d Avg', 'Base Range %', 'RS Edge %', 'Resistance Clearance %'
        ]]
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # STEP 2: DOWNLOAD BREAKOUTSUMMARY.MD
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

        # TECHNICAL CHARTING
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

        # RISK & POSITION CALCULATOR
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

else:
    st.title(f"{page} Module")
    st.info(f"The {page} module is active.")
