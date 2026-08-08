import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import os
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="ISTS Pro Dashboard", page_icon="📈", layout="wide")
st_autorefresh(interval=60000, limit=None, key="live_chart_refresh") # Auto-refresh UI every 60 seconds

@st.cache_data(ttl=60)
def load_report(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content: return content
    return f"⚠️ **Report file pending generation:** `{filepath}`\nRun the GitHub Actions scanner to generate."

@st.cache_data(ttl=60)
def load_csv(filepath):
    if os.path.exists(filepath): return pd.read_csv(filepath)
    return pd.DataFrame()

st.sidebar.title("ISTS Pro Terminal")
page = st.sidebar.radio("Navigation", ["Dashboard", "Scan Market", "Budget Scanner (< ₹500)"])

if page == "Dashboard":
    st.title("Institutional Quant Trading System (ISTS Pro)")
    st.markdown("Live Market Top-Down MTF Momentum & Options Engine")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Market Status", "MTF ALIGNED", "NSE Live Feed")
    col2.metric("Scan Universe", "1200+ Equities", "Liquidity Protected")
    col3.metric("Math Engine", "Retest / Pre-Breakout", "10-Point Grader")
    col4.metric("Strategy", "Scaled ATR Vectors", "Scalp/Swing/Pre")

elif page == "Scan Market":
    st.title("🚀 Master Quant Scanner")
    st.markdown("Displays Live 1200+ Universe Scans executed securely via GitHub Engine.")

    # Load pre-computed CSV Data instantly
    df_all_setups = load_csv("all_setups.csv")
    df_index_setups = load_csv("index_setups.csv")

    st.markdown("---")
    st.subheader("📊 Full Market Scan by Horizon")
    tab1, tab2, tab3, tab4 = st.tabs(["💥 Soon to Breakout (2-3 Days)", "⚡ Intraday", "🌙 BTST (Best 10-15)", "📈 Swing (Retest)"])
    
    with tab1: st.markdown(load_report("prebreakout_report.md"), unsafe_allow_html=True)
    with tab2: st.markdown(load_report("intraday_report.md"), unsafe_allow_html=True)
    with tab3: st.markdown(load_report("btst_report.md"), unsafe_allow_html=True)
    with tab4: st.markdown(load_report("swing_report.md"), unsafe_allow_html=True)

    # --- NATIVE PLOTLY CHART INTEGRATION ---
    st.markdown("---")
    st.subheader("🔍 Native Real-Time Chart Analysis")
    
    df_all_merged = pd.concat([df_index_setups, df_all_setups]) if not df_all_setups.empty else df_index_setups
    
    if not df_all_merged.empty and 'Stock' in df_all_merged.columns:
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1: selected_stock = st.selectbox("Select asset to load native chart:", df_all_merged['Stock'].tolist())
        with c2: selected_tf = st.selectbox("Timeframe:", ["5m", "15m", "30m", "1h", "1d"], index=1)
        with c3:
            st.write("")
            st.write("")
            if st.button("🔄 Reload Chart", use_container_width=True): st.cache_data.clear()

        stock_row = df_all_merged[df_all_merged['Stock'] == selected_stock].iloc[0]
        raw_sym = str(stock_row['RawStock']).strip()
        
        yf_sym = "^NSEI" if raw_sym == "NIFTY" else ("^NSEBANK" if raw_sym == "BANKNIFTY" else f"{raw_sym}.NS")
        tv_link_sym = f"NSE:{raw_sym}"
        fetch_period = "3mo" if selected_tf == "1d" else "5d"
        
        with st.spinner(f"Fetching live {selected_tf} candlestick data..."):
            chart_data = yf.Ticker(yf_sym).history(period=fetch_period, interval=selected_tf)
            if not chart_data.empty:
                fig = go.Figure(data=[go.Candlestick(
                    x=chart_data.index, open=chart_data['Open'], high=chart_data['High'], low=chart_data['Low'], close=chart_data['Close'],
                    increasing_line_color='#00ff00', decreasing_line_color='#ff0000'
                )])
                range_breaks = [dict(bounds=["sat", "mon"])]
                if selected_tf != "1d": range_breaks.append(dict(bounds=[15.5, 9.25], pattern="hour")) 
                fig.update_xaxes(rangebreaks=range_breaks)
                fig.update_layout(title=f"{selected_stock} - Native {selected_tf} Chart", yaxis_title="Price (₹)", template="plotly_dark", height=550, margin=dict(l=10, r=10, t=40, b=10), xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Live chart data temporarily unavailable.")

        st.markdown("### ⚡ Execute Broker Trade")
        b1, b2, b3 = st.columns(3)
        with b1: st.link_button("🟠 Trade on Dhan", "https://web.dhan.co/", use_container_width=True)
        with b2: st.link_button("🔵 Trade on Angel One", "https://trade.angelone.in/", use_container_width=True)
        with b3: st.link_button("📈 Open Full Chart on TV", f"https://in.tradingview.com/chart/?symbol={tv_link_sym}", use_container_width=True)

        st.markdown("---")
        st.subheader(f"🧮 Position Size & Risk Calculator: {selected_stock}")
        c1, c2, c3 = st.columns(3)
        capital = c1.number_input("Account Capital (₹)", min_value=10000, value=500000, step=25000)
        risk_pct = c2.number_input("Risk Limit per Trade (%)", min_value=0.25, max_value=5.0, value=1.0, step=0.25)
        entry_p = float(stock_row['Entry'])
        sl_p = c3.number_input("Stop Loss Price (₹)", min_value=1.0, value=float(stock_row['EqSL']), step=1.0)
        
        risk_per_share = abs(entry_p - sl_p)
        if risk_per_share > 0:
            max_risk = (capital * risk_pct) / 100.0
            qty = int(max_risk / risk_per_share)
            if "NIFTY" in raw_sym:
                lot_size = 25 if "BANK" not in raw_sym else 15
                qty = max(lot_size, (qty // lot_size) * lot_size)
                st.info(f"💡 Index detected. Adjusted to nearest lot size ({lot_size} qty).")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Quantity to Trade", f"{qty} units")
            m2.metric("Total Investment", f"₹{(qty * entry_p):,.2f}")
            m3.metric("Max Capital at Risk", f"₹{max_risk:,.2f}")
            m4.metric("Target 3 Profit", f"₹{(qty * abs(float(stock_row['EqT3']) - entry_p)):,.2f}")

elif page == "Budget Scanner (< ₹500)":
    st.title("💡 Sub-₹500 Budget Quant Scanner")
    budget_limit = st.number_input("Max Stock Price (₹)", min_value=50, max_value=1000, value=500, step=50)

    df_all_setups = load_csv("all_setups.csv")
    if not df_all_setups.empty:
        budget_res = df_all_setups[df_all_setups['Entry'] <= budget_limit].copy()
        if not budget_res.empty:
            budget_res.insert(0, '#', range(1, len(budget_res) + 1)) 
            st.success(f"Found {len(budget_res)} quant setups under ₹{budget_limit}!")
            
            st.subheader(f"🏆 Top Budget Quant Setups Under ₹{budget_limit}")
            b_cols = ['#', 'Stock', 'Horizon', 'Score', 'Entry', 'EqSL', 'EqT1', 'EqT2', 'EqT3', 'Opt', 'Prem']
            st.dataframe(budget_res[b_cols], use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("🔍 Budget Position & Share Quantity Calculator")
            selected_stock = st.selectbox("Select stock to evaluate:", budget_res['Stock'].tolist())
            stock_row = budget_res[budget_res['Stock'] == selected_stock].iloc[0]

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Stock:** `{selected_stock}`")
                st.markdown(f"**Entry Price:** ₹{stock_row['Entry']}")
                st.markdown(f"**Score / 10:** 🔥 {stock_row['Score']}")
                st.markdown(f"**Option Recommendation:** `{stock_row['Opt']}` at ₹{stock_row['Prem']}")
            with col2:
                trade_capital = st.number_input("Allocated Capital (₹)", min_value=5000, value=50000, step=5000)
                shares_qty = int(trade_capital // float(stock_row['Entry']))
                st.metric("Affordable Shares", f"{shares_qty} shares")
                st.metric("Total Investment Required", f"₹{round(shares_qty * float(stock_row['Entry']), 2):,.2f}")
        else:
            st.warning(f"No setups found under ₹{budget_limit} today.")
    else:
        st.warning("Run the GitHub Scanner first to populate the database.")
