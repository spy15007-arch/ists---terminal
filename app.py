import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import datetime
import io
import math
from scipy.stats import norm

st.set_page_config(page_title="ISTS Pro Quant Terminal", page_icon="📈", layout="wide")

# --- SESSION DEFAULTS ---
if 'watchlist' not in st.session_state: st.session_state['watchlist'] = ['RELIANCE', 'SBIN', 'HAL', 'BEL', 'FEDERALBNK']
if 'atr_sl_mult' not in st.session_state: st.session_state['atr_sl_mult'] = 1.5
if 'atr_t1_mult' not in st.session_state: st.session_state['atr_t1_mult'] = 1.5
if 'atr_t2_mult' not in st.session_state: st.session_state['atr_t2_mult'] = 3.0
if 'atr_t3_mult' not in st.session_state: st.session_state['atr_t3_mult'] = 4.5
if 'capital' not in st.session_state: st.session_state['capital'] = 100000.0
if 'risk_pct' not in st.session_state: st.session_state['risk_pct'] = 2.0

st.sidebar.title("ISTS Pro Quant")
st.sidebar.caption("Institutional Trading Engine")

page = st.sidebar.radio("Navigation", ["Dashboard", "Strict ISTS Scan", "Aggressive Momentum Scan", "Budget Scanner (< ₹500)", "MCX Commodities (Crude/NG)", "Watchlist", "Settings"])
st.sidebar.markdown("---")
bot_token = st.sidebar.text_input("Telegram Bot Token", type="password")
chat_id = st.sidebar.text_input("Telegram Chat ID", value="1338671581")

# --- QUANT MATH ENGINES ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def black_scholes_call(S, K, T, r, sigma):
    if T <= 0 or sigma == 0: return max(0, S - K), 1.0 if S > K else 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    return round(price, 2), round(norm.cdf(d1), 2)

def generate_quant_option(symbol, price, df, dte=15):
    step = 100 if price > 5000 else (50 if price > 2000 else (20 if price > 1000 else (10 if price > 500 else 5)))
    atm_strike = int(round(price / step) * step)
    
    # 10-Day Parkinson Volatility
    hl_log_sq = (np.log(df['High'] / df['Low']) ** 2).tail(10)
    vol = math.sqrt((1.0 / (4.0 * math.log(2.0))) * hl_log_sq.mean()) * math.sqrt(252)
    if math.isnan(vol) or vol == 0:
        df['Log_Ret'] = np.log(df['Close'] / df['Close'].shift(1))
        vol = df['Log_Ret'].tail(10).std() * math.sqrt(252)
        
    prem, delta = black_scholes_call(price, atm_strike, dte/365.0, 0.07, vol)
    return f"{atm_strike} CE", prem, delta, round(price*0.985, 1), round(price*1.02, 1), round(price*1.04, 1), round(price*1.06, 1)

def get_index_options_ideas():
    ideas = []
    for name, symbol, step in [('NIFTY 50', '^NSEI', 50), ('BANK NIFTY', '^NSEBANK', 100)]:
        try:
            df = yf.download(symbol, period="1mo", interval="1d", progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if df.empty: continue
            
            close_p = float(df['Close'].iloc[-1])
            ema_20 = float(df['Close'].ewm(span=20).mean().iloc[-1])
            atm_strike = int(round(close_p / step) * step)
            
            hl_log_sq = (np.log(df['High'] / df['Low']) ** 2).tail(10)
            vol = math.sqrt((1.0 / (4.0 * math.log(2.0))) * hl_log_sq.mean()) * math.sqrt(252)
            if math.isnan(vol) or vol == 0:
                df['Log_Ret'] = np.log(df['Close'] / df['Close'].shift(1))
                vol = df['Log_Ret'].tail(10).std() * math.sqrt(252)

            if close_p >= ema_20:
                bias, contract = "🟢 BULLISH", f"BUY {atm_strike} CE"
                prem, delta = black_scholes_call(close_p, atm_strike, 7/365.0, 0.07, vol)
                sl, t1, t2, t3 = round(close_p*0.995, 1), round(close_p*1.005, 1), round(close_p*1.010, 1), round(close_p*1.015, 1)
            else:
                bias, contract = "🔴 BEARISH", f"BUY {atm_strike} PE"
                prem, delta = black_scholes_call(atm_strike, close_p, 7/365.0, 0.07, vol)
                sl, t1, t2, t3 = round(close_p*1.005, 1), round(close_p*0.995, 1), round(close_p*0.990, 1), round(close_p*0.985, 1)

            ideas.append({'Index': name, 'Spot': round(close_p, 2), 'Bias': bias, 'Option': contract, 'EstPrem': prem, 'Delta': delta, 'SpotSL': sl, 'SpotT1': t1, 'SpotT2': t2, 'SpotT3': t3})
        except: continue
    return pd.DataFrame(ideas)

@st.cache_data(ttl=14400)
def get_nifty500_tickers():
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        df = pd.read_csv(io.StringIO(response.text))
        return [f"{s}.NS" for s in df['Symbol'].tolist()]
    except: return ['RELIANCE.NS', 'SBIN.NS', 'HAL.NS', 'BEL.NS', 'DIXON.NS']

def run_scan(mode="strict"):
    tickers = get_nifty500_tickers()
    results = []
    data = yf.download(tickers, period="6mo", interval="1d", group_by='ticker', progress=False)

    sl_m, t1_m, t2_m, t3_m = st.session_state['atr_sl_mult'], st.session_state['atr_t1_mult'], st.session_state['atr_t2_mult'], st.session_state['atr_t3_mult']
    risk_amt = st.session_state['capital'] * (st.session_state['risk_pct'] / 100.0)

    for ticker in tickers:
        symbol = ticker.replace(".NS", "")
        try:
            df = data[ticker].dropna() if len(tickers) > 1 else data.dropna()
            if len(df) < 60: continue

            close_p = float(df['Close'].iloc[-1])
            high_p, low_p, vol_today = float(df['High'].iloc[-1]), float(df['Low'].iloc[-1]), float(df['Volume'].iloc[-1])
            ema_20, ema_50 = float(df['Close'].ewm(span=20).mean().iloc[-1]), float(df['Close'].ewm(span=50).mean().iloc[-1])
            
            if mode == "strict" and close_p < ema_50: continue

            df['RSI'] = calculate_rsi(df['Close'])
            rsi_val = float(df['RSI'].iloc[-1])
            close_pos = round(((close_p - low_p) / (high_p - low_p)) * 100, 1) if high_p != low_p else 50.0
            vol_50d_avg = float(df['Volume'].rolling(50).mean().iloc[-1])
            vol_vs_50d = round(vol_today / vol_50d_avg, 2) if vol_50d_avg > 0 else 1.0

            signal = "🚀 STRONG BULL" if (rsi_val > 60 and vol_vs_50d > 1.5) else ("📈 BULLISH" if rsi_val > 50 else "NEUTRAL")
            score = min(10, (2 if close_pos >= 80 else (1 if close_pos >= 65 else 0)) + (2 if vol_vs_50d >= 2.0 else (1 if vol_vs_50d >= 1.3 else 0)) + (2 if rsi_val >= 60 else (1 if rsi_val >= 50 else 0)) + (2 if mode == "aggressive" else 0))
            
            horizon = "🌙 BTST" if (close_pos >= 75 and vol_vs_50d >= 1.2) else ("⚡ Intraday" if vol_vs_50d >= 1.3 else "📈 Swing")

            high_low, high_close, low_close = df['High'] - df['Low'], np.abs(df['High'] - df['Close'].shift()), np.abs(df['Low'] - df['Close'].shift())
            atr = float(pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).ewm(alpha=1/14).mean().iloc[-1])
            
            sl_price = round(close_p - (sl_m * atr), 1)
            qty = int(risk_amt / (close_p - sl_price)) if close_p > sl_price else 0

            opt_str, est_prem, delta, opt_sl, opt_t1, opt_t2, opt_t3 = generate_quant_option(symbol, close_p, df)

            results.append({
                'Stock': symbol, 'Horizon': horizon, 'Entry': round(close_p, 2), 'Signal': signal, 'Score': score, 'RSI': round(rsi_val, 1),
                'Qty': qty, 'EqSL': sl_price, 'EqT1': round(close_p + (t1_m * atr), 1), 'EqT2': round(close_p + (t2_m * atr), 1), 'EqT3': round(close_p + (t3_m * atr), 1),
                'Option': opt_str, 'EstPrem': est_prem, 'Delta': delta, 'OptSL': opt_sl, 'OptT1': opt_t1, 'OptT2': opt_t2, 'OptT3': opt_t3
            })
        except: continue
    return pd.DataFrame(results).sort_values(by=['Score', 'RSI'], ascending=[False, False]) if results else pd.DataFrame()

def get_tab_display_df(df, filter_text=None):
    if df is None or df.empty: return pd.DataFrame()
    dff = df[df['Horizon'].str.contains(filter_text, case=False, na=False)].copy() if filter_text else df.copy()
    if dff.empty: return pd.DataFrame()
    dff['Rank'] = range(1, len(dff) + 1)
    return dff[[c for c in ['Rank', 'Stock', 'Horizon', 'Signal', 'Entry', 'Qty', 'Score', 'RSI', 'EqSL', 'EqT1', 'EqT2', 'EqT3', 'Option', 'EstPrem', 'Delta', 'OptSL', 'OptT1', 'OptT2', 'OptT3'] if c in dff.columns]]

# --- VIEWS ---
if page == "Dashboard":
    st.title("ISTS Pro Quant Terminal")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Risk Capital", f"₹{st.session_state['capital']:,.0f}")
    c2.metric("Risk/Trade", f"{st.session_state['risk_pct']}%")
    c3.metric("Option Engine", "10-D Parkinson HV")
    c4.metric("Algorithm", "RSI Momentum")

elif page in ["Strict ISTS Scan", "Aggressive Momentum Scan", "Budget Scanner (< ₹500)"]:
    mode = "aggressive" if "Aggressive" in page else "strict"
    st.title(f"🚀 {page}")
    if st.button("Run Quant Engine", type="primary"):
        with st.spinner("Calculating Volatility & Greeks..."):
            st.session_state['idx_res'] = get_index_options_ideas()
            res = run_scan(mode)
            if "Budget" in page and not res.empty: res = res[res['Entry'] <= 500].copy()
            st.session_state['scan_res'] = res
            st.success("Complete!")

    if 'idx_res' in st.session_state and not st.session_state['idx_res'].empty:
        st.subheader("🏛️ Index Options (Black-Scholes Parkinson)")
        st.dataframe(st.session_state['idx_res'], use_container_width=True, hide_index=True)

    if 'scan_res' in st.session_state and not st.session_state['scan_res'].empty:
        df = st.session_state['scan_res']
        t1, t2, t3, t4 = st.tabs(["⚡ Intraday", "🌙 BTST", "📈 Swing", "🏆 All"])
        with t1: st.dataframe(get_tab_display_df(df, "Intraday"), use_container_width=True, hide_index=True)
        with t2: st.dataframe(get_tab_display_df(df, "BTST"), use_container_width=True, hide_index=True)
        with t3: st.dataframe(get_tab_display_df(df, "Swing"), use_container_width=True, hide_index=True)
        with t4: st.dataframe(get_tab_display_df(df), use_container_width=True, hide_index=True)

elif page == "MCX Commodities (Crude/NG)":
    st.title("🛢️ MCX Quant Commodities")
    if st.button("Scan Commodities", type="primary"):
        with st.spinner("Pricing NYMEX proxies..."):
            res = []
            for name, sym in {'Crude Oil': 'CL=F', 'Natural Gas': 'NG=F', 'Gold': 'GC=F', 'Silver': 'SI=F'}.items():
                try:
                    df = yf.download(sym, period="1mo", interval="1d", progress=False)
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                    close = float(df['Close'].iloc[-1])
                    df['RSI'] = calculate_rsi(df['Close'])
                    ema20 = float(df['Close'].ewm(span=20).mean().iloc[-1])
                    bias = "🟢 BULLISH" if close > ema20 else "🔴 BEARISH"
                    hl, hc, lc = df['High']-df['Low'], np.abs(df['High']-df['Close'].shift()), np.abs(df['Low']-df['Close'].shift())
                    atr = float(pd.concat([hl, hc, lc], axis=1).max(axis=1).ewm(alpha=1/14).mean().iloc[-1])
                    mult = 1 if close > ema20 else -1
                    res.append({'Commodity': name, 'Spot (USD)': round(close,2), 'Bias': bias, 'RSI': round(float(df['RSI'].iloc[-1]),1), 'ATR': round(atr,2), 'SL': round(close - (1.5*atr*mult), 2), 'T1': round(close + (1.5*atr*mult), 2), 'T2': round(close + (3.0*atr*mult), 2)})
                except: continue
            st.dataframe(pd.DataFrame(res), use_container_width=True, hide_index=True)

elif page == "Watchlist":
    st.title("📌 Watchlist")
    n = st.text_input("NSE Symbol:").strip().upper()
    if st.button("Add") and n and n not in st.session_state['watchlist']: st.session_state['watchlist'].append(n); st.rerun()
    st.write(st.session_state['watchlist'])

elif page == "Settings":
    st.title("⚙️ Parameters")
    st.session_state['capital'] = st.number_input("Capital (₹)", value=st.session_state['capital'])
    st.session_state['risk_pct'] = st.number_input("Risk %", value=st.session_state['risk_pct'])
