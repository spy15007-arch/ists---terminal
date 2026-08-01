import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import datetime
import io

st.set_page_config(page_title="ISTS Pro Dashboard", page_icon="📈", layout="wide")

if 'watchlist' not in st.session_state:
    st.session_state['watchlist'] = ['RELIANCE', 'SBIN', 'HAL', 'BEL', 'FEDERALBNK']

if 'atr_sl_mult' not in st.session_state: st.session_state['atr_sl_mult'] = 1.5
if 'atr_t1_mult' not in st.session_state: st.session_state['atr_t1_mult'] = 1.5
if 'atr_t2_mult' not in st.session_state: st.session_state['atr_t2_mult'] = 3.0
if 'atr_t3_mult' not in st.session_state: st.session_state['atr_t3_mult'] = 4.5

st.sidebar.title("ISTS Pro Terminal")
st.sidebar.caption("Multi-Horizon Institutional Trading Engine")

page = st.sidebar.radio(
    "Navigation", 
    ["Dashboard", "Strict ISTS Scan", "Aggressive Momentum Scan", "Budget Scanner (< ₹500)", "Watchlist", "Settings"]
)

st.sidebar.markdown("---")
bot_token = st.sidebar.text_input("Bot Token", type="password")
chat_id = st.sidebar.text_input("Chat ID", value="1338671581")

@st.cache_data(ttl=14400)
def get_nifty500_tickers():
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        df = pd.read_csv(io.StringIO(response.text))
        return [f"{symbol}.NS" for symbol in df['Symbol'].tolist()]
    except Exception:
        fallback = ['TVSMOTOR', 'COFORGE', 'HAL', 'BEL', 'DIXON', 'TRENT', 'MCX', 'PERSISTENT', 'RELIANCE', 'SBIN', 'DIVISLAB', 'FEDERALBNK']
        return [f"{s}.NS" for s in fallback]

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
                    'Index': name, 'Spot Price (₹)': round(close_p, 2), 'Trend Bias': bias,
                    'Recommended Option': contract, 'Spot SL (₹)': sl,
                    'Spot Target 1 (₹)': t1, 'Spot Target 2 (₹)': t2, 'Spot Target 3 (₹)': t3
                })
        except Exception:
            continue
    return pd.DataFrame(ideas)

def generate_option_idea(symbol, price):
    step = 100 if price > 5000 else (50 if price > 2000 else (20 if price > 1000 else (10 if price > 500 else 5)))
    atm_strike = int(round(price / step) * step)
    return f"BUY {symbol} {atm_strike} CE", round(price * 0.985, 1), round(price * 1.02, 1), round(price * 1.04, 1), round(price * 1.06, 1)

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

    sl_m = st.session_state['atr_sl_mult']
    t1_m = st.session_state['atr_t1_mult']
    t2_m = st.session_state['atr_t2_mult']
    t3_m = st.session_state['atr_t3_mult']

    for ticker in tickers:
        symbol = ticker.replace(".NS", "")
        try:
            df = data[ticker].dropna() if len(tickers) > 1 else data.dropna()
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
            low_50d = float(df['Low'].rolling(50).min().iloc[-1])
            base_range_pct = round(((high_50d - low_50d) / low_50d) * 100, 1) if low_50d > 0 else 20.0
            resistance_clearance = round(((high_50d - close_p) / close_p) * 100, 1) if high_50d > close_p else 0.0

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
                score = 2
                if close_p > ema_20: score += 2
                if vol_vs_50d >= 1.3: score += 2
                elif vol_vs_50d >= 1.1: score += 1
                if close_pos >= 70: score += 2
                elif close_pos >= 50: score += 1
                if resistance_clearance <= 3.0: score += 2

            score = min(10, score)
            composite = round((close_pos * 0.25) + (min(vol_vs_50d * 15, 30)) + (max(0, 25 - base_range_pct * 0.5)) + (min(max(0, rs_edge_pct), 20)), 1)

            if close_pos >= 75 and vol_vs_50d >= 1.2:
                horizon = "🌙 BTST (15:15 IST)"
            elif vol_vs_50d >= 1.3 or close_pos >= 70:
                horizon = "⚡ Intraday Momentum"
            else:
                horizon = "📈 Swing (1-2 Weeks)"

            high_low = df['High'] - df['Low']
            high_close = np.abs(df['High'] - df['Close'].shift())
            low_close = np.abs(df['Low'] - df['Close'].shift())
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = float(tr.ewm(alpha=1/14, adjust=False).mean().iloc[-1])

            opt_contract, opt_sl, opt_t1, opt_t2, opt_t3 = generate_option_idea(symbol, close_p)

            results.append({
                'Stock': symbol, 'Entry Price': round(close_p, 2), 'Horizon': horizon,
                'Score /10': score, 'Composite /100': composite,
                'Equity SL': round(close_p - (sl_m * atr), 1),
                'Target 1': round(close_p + (t1_m * atr), 1),
                'Target 2': round(close_p + (t2_m * atr), 1),
                'Target 3': round(close_p + (t3_m * atr), 1),
                'Option Contract': opt_contract, 
                'Opt Spot SL': opt_sl, 
                'Opt Spot T1': opt_t1, 
                'Opt Spot T2': opt_t2, 
                'Opt Spot T3': opt_t3, 
                'Data': df
            })
        except Exception: continue

    df_results = pd.DataFrame(results)
    if not df_results.empty:
        df_results = df_results.sort_values(by=['Score /10', 'Composite /100'], ascending=[False, False]).head(25)
        df_results['Rank'] = range(1, len(df_results) + 1)
    return df_results

if page == "Dashboard":
    st.title("Institutional Swing Trading System (ISTS Pro)")
    st.markdown("Live Market Top-Down Momentum & Multi-Target Trading Terminal")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Market Status", "OPEN", "NSE Live Feed")
    col2.metric("Morning Scan", "09:15-09:45 IST", "Intraday & Swing Focus")
    col3.metric("Pre-Close Scan", "15:15 IST", "BTST Entry Focus")
    col4.metric("Multi-Target Engine", "3 Targets + SL", "Equity & Options")

elif page in ["Strict ISTS Scan", "Aggressive Momentum Scan"]:
    mode_key = "strict" if page == "Strict ISTS Scan" else "aggressive"
    st.title(f"🚀 {page}")
    
    if st.button(f"Run {page}", type="primary"):
        with st.spinner("Scanning Nifty 500 & Index trends..."):
            df_idx = get_index_options_ideas()
            res = run_scan(mode=mode_key)
            st.session_state['index_res'] = df_idx
            st.session_state[f'{mode_key}_res'] = res
            st.success("Scan complete!")

    if 'index_res' in st.session_state and not st.session_state['index_res'].empty:
        st.subheader("🏛️ Live Index Options (Nifty 50 & Bank Nifty) — Call & Put Strategies")
        st.dataframe(st.session_state['index_res'], use_container_width=True, hide_index=True)
        st.markdown("---")

    if f'{mode_key}_res' in st.session_state and not st.session_state[f'{mode_key}_res'].empty:
        df = st.session_state[f'{mode_key}_res']
        tab1, tab2, tab3, tab4 = st.tabs(["⚡ Intraday Setups (09:15 IST)", "🌙 BTST Setups (15:15 IST)", "📈 Swing Setups (1-2 Weeks)", "🏆 All Setups"])

        col_list = ['Rank', 'Stock', 'Entry Price', 'Score /10', 'Equity SL', 'Target 1', 'Target 2', 'Target 3', 'Option Contract', 'Opt Spot SL', 'Opt Spot T1', 'Opt Spot T2', 'Opt Spot T3']

        with tab1:
            st.subheader("⚡ Morning Intraday Setups (3 Targets + SL)")
            st.dataframe(df[df['Horizon'].str.contains("Intraday")][col_list], use_container_width=True, hide_index=True)

        with tab2:
            st.subheader("🌙 Pre-Close BTST Setups (3 Targets + SL)")
            st.dataframe(df[df['Horizon'].str.contains("BTST")][col_list], use_container_width=True, hide_index=True)

        with tab3:
            st.subheader("📈 Swing Trading Setups (3 Targets + SL)")
            st.dataframe(df[df['Horizon'].str.contains("Swing")][col_list], use_container_width=True, hide_index=True)

        with tab4:
            st.subheader("🏆 Complete Categorized Leaderboard")
            st.dataframe(df[['Rank', 'Stock', 'Horizon', 'Entry Price', 'Score /10', 'Equity SL', 'Target 1', 'Target 2', 'Target 3', 'Option Contract', 'Opt Spot SL', 'Opt Spot T1', 'Opt Spot T2', 'Opt Spot T3']], use_container_width=True, hide_index=True)

elif page == "Budget Scanner (< ₹500)":
    st.title("💡 Sub-₹500 Momentum & Budget Scanner")
    budget_limit = st.number_input("Max Stock Price (₹)", min_value=50, max_value=1000, value=500, step=50)

    if st.button("Run Budget Market Scan", type="primary"):
        with st.spinner("Scanning budget universe..."):
            df_idx = get_index_options_ideas()
            full_res = run_scan(mode="strict")
            st.session_state['index_res'] = df_idx
            if not full_res.empty:
                st.session_state['b_res'] = full_res[full_res['Entry Price'] <= budget_limit].copy()

    if 'index_res' in st.session_state and not st.session_state['index_res'].empty:
        st.subheader("🏛️ Live Index Options (Nifty 50 & Bank Nifty)")
        st.dataframe(st.session_state['index_res'], use_container_width=True, hide_index=True)
        st.markdown("---")

    if 'b_res' in st.session_state and not st.session_state['b_res'].empty:
        df_b = st.session_state['b_res']
        col_list = ['Rank', 'Stock', 'Horizon', 'Entry Price', 'Score /10', 'Equity SL', 'Target 1', 'Target 2', 'Target 3', 'Option Contract', 'Opt Spot SL', 'Opt Spot T1', 'Opt Spot T2', 'Opt Spot T3']
        st.subheader("💡 Budget Equity & Call Option Multi-Target Plan")
        st.dataframe(df_b[col_list], use_container_width=True, hide_index=True)

elif page == "Watchlist":
    st.title("📌 Custom Watchlist Tracker")
    new_stock = st.text_input("Enter NSE Symbol:").strip().upper()
    if st.button("➕ Add") and new_stock:
        if new_stock not in st.session_state['watchlist']:
            st.session_state['watchlist'].append(new_stock)
            st.rerun()
    st.write(st.session_state['watchlist'])

elif page == "Settings":
    st.title("⚙️ Parameters")
    st.session_state['atr_sl_mult'] = st.number_input("SL Multiplier", value=float(st.session_state['atr_sl_mult']))
