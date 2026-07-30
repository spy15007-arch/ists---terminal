import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import threading

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="ISTS Pro - BTST & Breakout Terminal",
    page_icon="📈",
    layout="wide"
)

# --- NIFTY 500 SAMPLE UNIVERSE ---
NIFTY_500_SAMPLE = [
    'LALPATHLAB', 'DIVISLAB', 'PARADEEP', 'PCBL', 'FSL', 'TVSMOTOR', 'SONATSOFTW', 
    'M&MFIN', 'RADICO', 'MEDANTA', 'SWIGGY', 'SAGILITY', 'MANAPPURAM', 'ASIANPAINT', 
    'CIPLA', 'WELCORP', 'AFFLE', 'RKFORGE', 'LLOYDSME', 'HEG', 'COFORGE', 'REDINGTON', 
    'PIDILITIND', 'SUNPHARMA', 'SAILIFE', 'ENDURANCE', 'LAURUSLABS', '360ONE', 
    'KALYANKJIL', 'SAREGAMA', 'JYOTICNC', 'FEDERALBNK', 'IEX', 'BHARTIHEXA', 'IIFL', 
    'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'SBIN', 'BHARTIARTL', 'MARUTI'
]

# --- SIDEBAR SETUP ---
st.sidebar.title("ISTS Pro Terminal")
st.sidebar.caption("Institutional BTST & Breakout Engine")

page = st.sidebar.radio("Navigation", ["Scan Market", "Watchlist", "Settings"])

st.sidebar.markdown("---")
st.sidebar.subheader("📲 Telegram Alert Setup")
bot_token = st.sidebar.text_input("Bot Token", type="password")
chat_id = st.sidebar.text_input("Chat ID", value="1338671581")
enable_alerts = st.sidebar.checkbox("Enable Alerts (Score >= 8)", value=True)

# --- TELEGRAM NOTIFIER ---
def send_telegram_alert_async(symbol, price, score, composite, token, c_id):
    if not token or not c_id: return
    message = (
        f"🚨 *BTST BREAKOUT ALERT* 🚨\n\n"
        f"📌 *Stock:* `{symbol}`\n"
        f"💰 *Price:* ₹{price}\n"
        f"⭐ *Readiness Score:* *{score}/10*\n"
        f"📊 *Composite Score:* *{composite}/100*\n\n"
        f"🎯 Review chart on ISTS Pro Terminal."
    )
    url = f"https://api.telegram.org/bot{token.strip()}/sendMessage"
    payload = {"chat_id": c_id.strip(), "text": message, "parse_mode": "Markdown"}
    threading.Thread(target=requests.post, args=(url,), kwargs={'json': payload, 'timeout': 5}, daemon=True).start()

# --- COMPOSITE BREAKOUT CALCULATION ENGINE ---
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

            close_p = data['Close'].iloc[-1]
            high_p = data['High'].iloc[-1]
            low_p = data['Low'].iloc[-1]
            vol_today = data['Volume'].iloc[-1]

            # Metrics
            close_pos = round(((close_p - low_p) / (high_p - low_p)) * 100, 1) if high_p != low_p else 50.0
            vol_50d_avg = data['Volume'].rolling(50).mean().iloc[-1]
            vol_vs_50d = round(vol_today / vol_50d_avg, 2) if vol_50d_avg > 0 else 1.0

            high_50d = data['High'].rolling(50).max().iloc[-1]
            low_50d = data['Low'].rolling(50).min().iloc[-1]
            base_range_pct = round(((high_50d - low_50d) / low_50d) * 100, 1)

            stock_3m_return = ((close_p / data['Close'].iloc[-63]) - 1) * 100
            rs_edge_pct = round(stock_3m_return - nifty_3m_return, 1)

            resistance_clearance = round(((high_50d - close_p) / close_p) * 100, 1) if high_50d > close_p else 0.0

            # 0 - 10 Score System
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

            # Composite Tiebreaker /100
            composite = round(
                (close_pos * 0.25) + 
                (min(vol_vs_50d * 15, 30)) + 
                (max(0, 25 - base_range_pct * 0.5)) + 
                (min(max(0, rs_edge_pct), 20)), 
                1
            )

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
                'Data': data
            })
        except:
            continue

    # Sort by Score /10 primary, Composite /100 secondary
    df_results = pd.DataFrame(results)
    if not df_results.empty:
        df_results = df_results.sort_values(by=['Score /10', 'Composite /100'], ascending=[False, False])
        df_results['Rank'] = range(1, len(df_results) + 1)
    return df_results

# --- MAIN SCANNER VIEW ---
if page == "Scan Market":
    st.title("🎯 BTST Breakout-Readiness Scanner")
    st.markdown("Multi-factor scoring based on Close Position, Vol Surge, Base Tightness, RS Edge, and Overhead Resistance Clearance.")

    if st.button("Run BTST Breakout Scan (500 Stocks)", type="primary"):
        with st.spinner("Scanning universe & computing composite readiness scores..."):
            df_res = run_btst_breakout_scan(NIFTY_500_SAMPLE)
            st.session_state['btst_results'] = df_res
            st.success(f"Scan complete! {len(df_res[df_res['Score /10'] >= 6])} stocks scored 6+/10.")

    if 'btst_results' in st.session_state and not st.session_state['btst_results'].empty:
        df_display = st.session_state['btst_results'][[
            'Rank', 'Stock', 'Price', 'Score /10', 'Composite /100', 
            'Close Position %', 'Vol vs 50d Avg', 'Base Range %', 'RS Edge %', 'Resistance Clearance %'
        ]]

        st.dataframe(df_display, use_container_width=True, hide_index=True)

        st.caption("• **Close Position %**: Higher = closed near day's high (100 = day's high).")
        st.caption("• **Vol vs 50d Avg**: >1.3–2x indicates institutional buying volume.")
        st.caption("• **Base Range %**: Lower = tighter prior consolidation base.")
        st.caption("• **RS Edge %**: Stock 3-month return minus Nifty 3-month return.")
        st.caption("• **Resistance Clearance %**: 0 = making new 50-day high.")

        st.markdown("---")
        selected_stock = st.selectbox("Select stock to inspect chart:", df_display['Stock'].tolist())
        stock_row = st.session_state['btst_results'][st.session_state['btst_results']['Stock'] == selected_stock].iloc[0]
        chart_df = stock_row['Data'].tail(120)

        fig = go.Figure(data=[
            go.Candlestick(x=chart_df.index, open=chart_df['Open'], high=chart_df['High'], low=chart_df['Low'], close=chart_df['Close'], name="Price")
        ])
        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=450, title=f"{selected_stock} Daily Chart")
        st.plotly_chart(fig, use_container_width=True)
