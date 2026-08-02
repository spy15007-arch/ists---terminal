import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import datetime
import io
import math
import os
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
st.sidebar.caption("High Conviction Trading Engine")

page = st.sidebar.radio(
    "Navigation", 
    ["Dashboard", "Strict ISTS Scan", "Aggressive Momentum Scan", "Budget Scanner (< ₹500)", 
     "MCX Commodities", "🧪 Backtesting Engine", "📓 Trade Journal", "Watchlist", "Settings"]
)
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

def calculate_lorentzian_distance(current_rsi, current_vol_vs, ideal_rsi=70.0, ideal_vol=2.0):
    dist_rsi = math.log(1 + abs(current_rsi - ideal_rsi))
    dist_vol = math.log(1 + abs(current_vol_vs - ideal_vol))
    return round(dist_rsi + dist_vol, 2)

def black_scholes_call(S, K, T, r, sigma):
    if T <= 0 or sigma == 0: return max(0, S - K), 1.0 if S > K else 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    return round(price, 2), round(norm.cdf(d1), 2)

def generate_quant_option(symbol, price, df, dte=15):
    step = 100 if price > 5000 else (50 if price > 2000 else (20 if price > 1000 else (10 if price > 500 else 5)))
    atm_strike = int(round(price / step) * step)
    hl_log_sq = (np.log(df['High'] / df['Low']) ** 2).tail(10)
    vol = math.sqrt((1.0 / (4.0 * math.log(2.0))) * hl_log_sq.mean()) * math.sqrt(252)
    if math.isnan(vol) or vol == 0:
        df['Log_Ret'] = np.log(df['Close'] / df['Close'].shift(1))
        vol = df['Log_Ret'].tail(10).std() * math.sqrt(252)
    prem, delta = black_scholes_call(price, atm_strike, dte/365.0, 0.07, vol)
    return f"{atm_strike} CE", prem, delta, round(price*0.985, 1), round(price*1.02, 1), round(price*1.04, 1), round(price*1.06, 1)

@st.cache_data(ttl=14400)
def get_nifty500_tickers():
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        df = pd.read_csv(io.StringIO(response.text))
        return [f"{s}.NS" for s in df['Symbol'].tolist()]
    except: return ['RELIANCE.NS', 'SBIN.NS', 'HAL.NS', 'BEL.NS', 'DIXON.NS']

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
            ema_50 = float(df['Close'].ewm(span=50).mean().iloc[-1])
            if mode == "strict" and close_p < ema_50: continue

            df['RSI'] = calculate_rsi(df['Close'])
            rsi_val = float(df['RSI'].iloc[-1])
            close_pos = round(((close_p - low_p) / (high_p - low_p)) * 100, 1) if high_p != low_p else 50.0
            vol_50d_avg = float(df['Volume'].rolling(50).mean().iloc[-1])
            vol_vs_50d = round(vol_today / vol_50d_avg, 2) if vol_50d_avg > 0 else 1.0

            signal = "🚀 STRONG BULL" if (rsi_val > 60 and vol_vs_50d > 1.5) else ("📈 BULLISH" if rsi_val > 50 else "NEUTRAL")
            
            # Base Score
            score = min(10, (2 if close_pos >= 80 else (1 if close_pos >= 65 else 0)) + 
                        (2 if vol_vs_50d >= 2.0 else (1 if vol_vs_50d >= 1.3 else 0)) + 
                        (2 if rsi_val >= 60 else (1 if rsi_val >= 50 else 0)) + 
                        (2 if mode == "aggressive" else 0))
            
            # Lorentzian Filter
            lorentzian_score = calculate_lorentzian_distance(rsi_val, vol_vs_50d)
            if lorentzian_score > 1.5: score -= 1
            elif lorentzian_score < 0.5: score += 1
            
            if score < 4: continue
            
            horizon = "🌙 BTST" if (close_pos >= 75 and vol_vs_50d >= 1.2) else ("⚡ Intraday" if vol_vs_50d >= 1.3 else "📈 Swing")

            high_low, high_close, low_close = df['High'] - df['Low'], np.abs(df['High'] - df['Close'].shift()), np.abs(df['Low'] - df['Close'].shift())
            atr = float(pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).ewm(alpha=1/14).mean().iloc[-1])
            sl_price = round(close_p - (sl_m * atr), 1)
            qty = int(risk_amt / (close_p - sl_price)) if close_p > sl_price else 0

            opt_str, est_prem, delta, opt_sl, opt_t1, opt_t2, opt_t3 = generate_quant_option(symbol, close_p, df)
            broker_link = f"https://in.tradingview.com/chart/?symbol=NSE:{symbol}"

            results.append({
                'Stock': symbol, 'Horizon': horizon, 'Entry': round(close_p, 2), 'Signal': signal, 'Score': score, 'RSI': round(rsi_val, 1),
                'Qty': qty, 'EqSL': sl_price, 'EqT1': round(close_p + (t1_m * atr), 1), 'EqT2': round(close_p + (t2_m * atr), 1), 'EqT3': round(close_p + (t3_m * atr), 1),
                'Option': opt_str, 'EstPrem': est_prem, 'Delta': delta, 'OptSL': opt_sl, 'OptT1': opt_t1, 'OptT2': opt_t2, 'OptT3': opt_t3,
                'Execute': broker_link
            })
        except: continue
    
    return pd.DataFrame(results).sort_values(by=['Score', 'RSI'], ascending=[False, False]).head(20) if results else pd.DataFrame()

def render_dataframe(df_input, horizon_filter=None):
    if df_input is None or df_input.empty: return
    dff = df_input[df_input['Horizon'].str.contains(horizon_filter, case=False, na=False)].copy() if horizon_filter else df_input.copy()
    if dff.empty: 
        st.info(f"No {horizon_filter if horizon_filter else ''} setups currently.")
        return
    dff['S.No'] = range(1, len(dff) + 1)
    
    st.dataframe(
        dff[['S.No', 'Stock', 'Horizon', 'Signal', 'Score', 'RSI', 'Entry', 'Qty', 'EqSL', 'EqT1', 'EqT2', 'EqT3', 'Option', 'EstPrem', 'Execute']],
        use_container_width=True, hide_index=True,
        column_config={"Execute": st.column_config.LinkColumn("Execute (Chart)", display_text="Open ⚡")}
    )

# --- BACKTESTING ENGINE ---
def run_backtest(symbol, strategy="Strict"):
    df = yf.download(f"{symbol}.NS", period="2y", interval="1d", progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    if len(df) < 100: return None, None
    
    df['EMA20'] = df['Close'].ewm(span=20).mean()
    df['EMA50'] = df['Close'].ewm(span=50).mean()
    df['RSI'] = calculate_rsi(df['Close'])
    
    hl, hc, lc = df['High']-df['Low'], np.abs(df['High']-df['Close'].shift()), np.abs(df['Low']-df['Close'].shift())
    df['ATR'] = pd.concat([hl, hc, lc], axis=1).max(axis=1).ewm(alpha=1/14).mean()
    df['Vol_50'] = df['Volume'].rolling(50).mean()
    
    trades = []
    in_trade = False
    entry_price, sl_price, target_price = 0, 0, 0
    
    for i in range(50, len(df)):
        c, h, l = df['Close'].iloc[i], df['High'].iloc[i], df['Low'].iloc[i]
        
        if not in_trade:
            cond_strict = c > df['EMA50'].iloc[i] and df['RSI'].iloc[i] > 60 and df['Volume'].iloc[i] > (1.3 * df['Vol_50'].iloc[i])
            cond_agg = df['RSI'].iloc[i] > 55 and df['Volume'].iloc[i] > (1.1 * df['Vol_50'].iloc[i]) and c > df['EMA20'].iloc[i]
            
            if (strategy == "Strict" and cond_strict) or (strategy == "Aggressive" and cond_agg):
                in_trade = True
                entry_price = c
                sl_price = entry_price - (st.session_state['atr_sl_mult'] * df['ATR'].iloc[i])
                target_price = entry_price + (st.session_state['atr_t2_mult'] * df['ATR'].iloc[i])
        else:
            if l <= sl_price:
                trades.append((df.index[i], entry_price, sl_price, "LOSS", sl_price - entry_price))
                in_trade = False
            elif h >= target_price:
                trades.append((df.index[i], entry_price, target_price, "WIN", target_price - entry_price))
                in_trade = False
                
    return df, pd.DataFrame(trades, columns=['Date', 'Entry', 'Exit', 'Result', 'PnL'])

# --- VIEWS ---
if page == "Dashboard":
    st.title("ISTS Pro Quant Terminal")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Risk Capital", f"₹{st.session_state['capital']:,.0f}")
    c2.metric("Risk/Trade", f"{st.session_state['risk_pct']}%")
    c3.metric("Top Stocks Cap", "Top 20 Sure Shot")
    c4.metric("Algorithm", "Lorentzian + RSI")

elif page in ["Strict ISTS Scan", "Aggressive Momentum Scan", "Budget Scanner (< ₹500)"]:
    mode = "aggressive" if "Aggressive" in page else "strict"
    st.title(f"🚀 {page}")
    if st.button("Run High Conviction Engine", type="primary"):
        with st.spinner("Extracting Top 20 Setups via Lorentzian Classification..."):
            st.session_state['idx_res'] = get_index_options_ideas()
            res = run_scan(mode)
            if "Budget" in page and not res.empty: res = res[res['Entry'] <= 500].copy()
            st.session_state['scan_res'] = res
            st.success("Extraction Complete!")

    if 'idx_res' in st.session_state and not st.session_state['idx_res'].empty:
        st.subheader("🏛️ Live Index Options (Nifty 50 & Bank Nifty CEs/PEs)")
        df_idx = st.session_state['idx_res'].copy()
        df_idx.insert(0, 'S.No', range(1, len(df_idx) + 1))
        st.dataframe(df_idx, use_container_width=True, hide_index=True)

    if 'scan_res' in st.session_state and not st.session_state['scan_res'].empty:
        df = st.session_state['scan_res']
        t1, t2, t3, t4 = st.tabs(["⚡ Intraday", "🌙 BTST", "📈 Swing", "🏆 Top 20 All Setups"])
        with t1: render_dataframe(df, "Intraday")
        with t2: render_dataframe(df, "BTST")
        with t3: render_dataframe(df, "Swing")
        with t4: render_dataframe(df)

elif page == "MCX Commodities":
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
                    res.append({'Commodity': name, 'Spot (USD)': round(close,2), 'Bias': bias, 'RSI': round(float(df['RSI'].iloc[-1]),1), 'SL': round(close-(1.5*atr*mult),2), 'T1': round(close+(1.5*atr*mult),2), 'T2': round(close+(3.0*atr*mult),2)})
                except: continue
            
            df_mcx = pd.DataFrame(res)
            if not df_mcx.empty:
                df_mcx.insert(0, 'S.No', range(1, len(df_mcx) + 1))
                st.dataframe(df_mcx, use_container_width=True, hide_index=True)

elif page == "🧪 Backtesting Engine":
    st.title("🧪 Live Strategy Backtester")
    col1, col2 = st.columns(2)
    test_sym = col1.text_input("Enter NSE Stock (e.g., RELIANCE):", value="RELIANCE").upper().strip()
    test_strat = col2.selectbox("Strategy Type:", ["Strict", "Aggressive"])
    
    if st.button("Run Backtest", type="primary"):
        with st.spinner(f"Running 2-Year Backtest on {test_sym}..."):
            price_data, trade_data = run_backtest(test_sym, test_strat)
            if trade_data is not None and not trade_data.empty:
                win_rate = (len(trade_data[trade_data['Result'] == 'WIN']) / len(trade_data)) * 100
                total_pnl = trade_data['PnL'].sum()
                trade_data['Cumulative PnL'] = trade_data['PnL'].cumsum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Trades", len(trade_data))
                c2.metric("Win Rate", f"{win_rate:.1f}%")
                c3.metric("Net Points PnL", f"₹{total_pnl:.2f}")
                
                fig = go.Figure(go.Scatter(x=trade_data['Date'], y=trade_data['Cumulative PnL'], fill='tozeroy', line=dict(color='green' if total_pnl > 0 else 'red')))
                fig.update_layout(title=f"Equity Curve: {test_sym}", template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
                
                trade_data.insert(0, 'S.No', range(1, len(trade_data) + 1))
                st.dataframe(trade_data, use_container_width=True, hide_index=True)
            else: st.warning("No trades triggered.")

elif page == "📓 Trade Journal":
    st.title("📓 Live Trade Journal")
    journal_file = "journal.csv"
    if not os.path.exists(journal_file):
        pd.DataFrame(columns=["S.No", "Date", "Stock", "Status", "Entry Price", "Exit Price", "Net PnL"]).to_csv(journal_file, index=False)
        
    df_j = pd.read_csv(journal_file)
    edited_df = st.data_editor(df_j, num_rows="dynamic", column_config={"Status": st.column_config.SelectboxColumn("Status", options=["OPEN", "WIN", "LOSS"])}, use_container_width=True)
    
    if st.button("💾 Save Journal"):
        edited_df['S.No'] = range(1, len(edited_df) + 1)
        edited_df.to_csv(journal_file, index=False)
        st.success("Saved!")
        st.rerun()

elif page == "Watchlist":
    st.title("📌 Custom Watchlist")
    n = st.text_input("NSE Symbol:").strip().upper()
    if st.button("Add") and n and n not in st.session_state['watchlist']: st.session_state['watchlist'].append(n); st.rerun()
    st.write(st.session_state['watchlist'])

elif page == "Settings":
    st.title("⚙️ Parameters")
    st.session_state['capital'] = st.number_input("Capital (₹)", value=st.session_state['capital'])
    st.session_state['risk_pct'] = st.number_input("Risk %", value=st.session_state['risk_pct'])
