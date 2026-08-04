import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import datetime
import calendar
import math
from scipy.stats import norm

st.set_page_config(page_title="ISTS Pro Dashboard", page_icon="📈", layout="wide")

STATIC_FNO = ["AARTIIND", "ABB", "ABBOTINDIA", "ABCAPITAL", "ABFRL", "ACC", "ADANIENT", "ADANIPORTS", "ALKEM", "AMBUJACEM", "APOLLOHOSP", "APOLLOTYRE", "ASHOKLEY", "ASIANPAINT", "ASTRAL", "ATUL", "AUBANK", "AUROPHARMA", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BALKRISIND", "BALRAMCHIN", "BANDHANBNK", "BANKBARODA", "BATAINDIA", "BEL", "BERGEPAINT", "BHARATFORG", "BHARTIARTL", "BHEL", "BIOCON", "BOSCHLTD", "BPCL", "BRITANNIA", "CANBK", "CANFINHOME", "CHAMBLFERT", "CHOLAFIN", "CIPLA", "COALINDIA", "COFORGE", "COLPAL", "CONCOR", "COROMANDEL", "CROMPTON", "CUB", "CUMMINSIND", "DABUR", "DALBHARAT", "DEEPAKNTR", "DIVISLAB", "DIXON", "DLF", "DRREDDY", "EICHERMOT", "ESCORTS", "EXIDEIND", "FEDERALBNK", "GAIL", "GLENMARK", "GMRINFRA", "GNFC", "GODREJCP", "GODREJPROP", "GRANULES", "GRASIM", "GUJGASLTD", "HAL", "HAVELLS", "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDCOPPER", "HINDPETRO", "HINDUNILVR", "ICICIBANK", "ICICIGI", "ICICIPRULI", "IDEA", "IDFCFIRSTB", "IEX", "IGL", "INDHOTEL", "INDIACEM", "INDIAMART", "INDIGO", "INDUSINDBK", "INFY", "IOC", "IPCALAB", "IRCTC", "ITC", "JINDALSTEL", "JSWSTEEL", "JUBLFOOD", "KOTAKBANK", "LALPATHLAB", "LAURUSLABS", "LICHSGFIN", "LT", "LTIM", "LTTS", "LUPIN", "M&M", "M&MFIN", "MANAPPURAM", "MARICO", "MARUTI", "MCDOWELL-N", "MCX", "METROPOLIS", "MFSL", "MGL", "MOTHERSON", "MPHASIS", "MRF", "MUTHOOTFIN", "NATIONALUM", "NAUKRI", "NAVINFLUOR", "NESTLEIND", "NMDC", "NTPC", "OBEROIRLTY", "OFSS", "ONGC", "PAGEIND", "PEL", "PETRONET", "PFC", "PIDILITIND", "PIIND", "PNB", "POLYCAB", "POWERGRID", "PVRINOX", "RAMCOCEM", "RBLBANK", "RECLTD", "RELIANCE", "SAIL", "SBICARD", "SBILIFE", "SBIN", "SHREECEM", "SHRIRAMFIN", "SIEMENS", "SRF", "SUNPHARMA", "SUNTV", "SYNGENE", "TATACHEM", "TATACOMM", "TATACONSUM", "TATAMOTORS", "TATAPOWER", "TATASTEEL", "TCS", "TECHM", "TITAN", "TORNTPHARM", "TRENT", "TVSMOTOR", "UBL", "ULTRACEMCO", "UPL", "VEDL", "VOLTAS", "WIPRO", "ZEEL", "ZYDUSLIFE"]

st.sidebar.title("ISTS Pro Terminal")
st.sidebar.caption("Institutional Quant Trading System")
page = st.sidebar.radio("Navigation", ["Dashboard", "Scan Market", "Budget Scanner (< ₹500)"])

def get_session_info():
    hour = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)).hour
    return "Intraday" if hour < 12 else "BTST"

def get_expiry_dte():
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    today = now.date()
    c = calendar.Calendar(firstweekday=calendar.MONDAY)
    monthcal = c.monthdatescalendar(today.year, today.month)
    last_thursday = [d for week in monthcal for d in week if d.weekday() == 3 and d.month == today.month][-1]
    
    if today > last_thursday or (today == last_thursday and now.hour >= 15):
        next_month = today.month + 1 if today.month < 12 else 1
        next_year = today.year if today.month < 12 else today.year + 1
        monthcal = c.monthdatescalendar(next_year, next_month)
        last_thursday = [d for week in monthcal for d in week if d.weekday() == 3 and d.month == next_month][-1]
    
    dte = (last_thursday - today).days
    return max(1, dte), "Monthly"

def black_scholes(S, K, T, r, sigma):
    if T <= 0 or sigma == 0: return max(0, S - K), max(0, K - S), 1.0 if S > K else 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    call_prem = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    return round(call_prem, 2)

def generate_quant_option(price, t1, t2, t3, df_h, df_l, df_c, dte, label):
    step = 100 if price > 5000 else (50 if price > 2000 else (20 if price > 1000 else (10 if price > 500 else 5)))
    atm = int(round(price / step) * step)
    try:
        vol = math.sqrt((1.0 / (4.0 * math.log(2.0))) * ((np.log(df_h/df_l)**2).tail(10).mean())) * math.sqrt(252)
        if math.isnan(vol) or vol == 0: vol = np.log(df_c/df_c.shift(1)).tail(10).std() * math.sqrt(252)
        if math.isnan(vol) or vol == 0: vol = 0.2
    except: vol = 0.2
    
    c_prem = black_scholes(price, atm, dte/365.0, 0.07, vol)
    pt1 = black_scholes(t1, atm, dte/365.0, 0.07, vol)
    pt2 = black_scholes(t2, atm, dte/365.0, 0.07, vol)
    pt3 = black_scholes(t3, atm, dte/365.0, 0.07, vol)
    
    return f"{atm} CE [{label}]", c_prem, round(pt1, 1), round(pt2, 1), round(pt3, 1)

@st.cache_data(ttl=1800)
def run_quant_scan():
    tickers = [f"{s}.NS" for s in STATIC_FNO]
    data = yf.download(tickers, period="3mo", interval="1d", progress=False, threads=True)
    if data.empty: return pd.DataFrame()
    
    closes, highs, lows, volumes = data['Close'], data['High'], data['Low'], data['Volume']
    ema_50_all = closes.ewm(span=50).mean()
    vol_50d_avg_all = volumes.rolling(50).mean()
    
    delta = closes.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rsi_all = 100 - (100 / (1 + (gain / loss)))

    exp1 = closes.ewm(span=12, adjust=False).mean()
    exp2 = closes.ewm(span=26, adjust=False).mean()
    macd_all = exp1 - exp2
    macd_signal_all = macd_all.ewm(span=9, adjust=False).mean()
    
    hl = highs - lows
    hc = (highs - closes.shift(1)).abs()
    lc = (lows - closes.shift(1)).abs()
    tr = pd.DataFrame(np.maximum(hl.values, np.maximum(hc.values, lc.values)), index=hl.index, columns=hl.columns)
    atr_all = tr.ewm(alpha=1/14).mean()

    last_close = closes.iloc[-1]
    last_high = highs.iloc[-1]
    last_low = lows.iloc[-1]
    last_vol = volumes.iloc[-1]
    last_vol_50 = vol_50d_avg_all.iloc[-1]
    last_rsi = rsi_all.iloc[-1]
    last_macd = macd_all.iloc[-1]
    last_macd_signal = macd_signal_all.iloc[-1]
    last_ema_50 = ema_50_all.iloc[-1]
    last_atr = atr_all.iloc[-1]

    sess_type = get_session_info()
    valid_setups = []
    
    stock_dte, stock_label = get_expiry_dte()

    for ticker in closes.columns:
        try:
            close_p = float(last_close[ticker])
            high_p = float(last_high[ticker])
            low_p = float(last_low[ticker])
            vol_today = float(last_vol[ticker])
            
            if pd.isna(close_p) or close_p <= 0 or vol_today < 1000: continue
            vol_50_avg = float(last_vol_50[ticker])
            if pd.isna(vol_50_avg) or vol_50_avg <= 0: continue
            
            rsi_val = float(last_rsi[ticker])
            if pd.isna(rsi_val) or rsi_val > 72.0: continue
            
            macd_val = float(last_macd[ticker])
            macd_sig = float(last_macd_signal[ticker])
            if macd_val < macd_sig: continue
            
            ema_50 = float(last_ema_50[ticker])
            passes_ema = close_p >= ema_50
            atr = float(last_atr[ticker])

            pos = round(((close_p - low_p) / (high_p - low_p)) * 100, 1)
            if pos < 55.0: continue 

            vol_vs = round(vol_today / vol_50_avg, 2)
            if sess_type == "Intraday": hor = "Intraday" if vol_vs >= 1.3 else "Swing"
            else: hor = "BTST" if vol_vs >= 1.2 else "Swing"

            base_score = (2 if 55 <= rsi_val <= 68 else 0) + (2 if vol_vs>=1.5 else 0)
            
            t1 = round(close_p + 1.5 * atr, 1)
            t2 = round(close_p + 3.0 * atr, 1)
            t3 = round(close_p + 4.5 * atr, 1)
            t4 = round(close_p + 6.0 * atr, 1)
            t5 = round(close_p + 7.5 * atr, 1)

            symbol = ticker.replace(".NS", "")
            df_h, df_l, df_c = highs[ticker].dropna(), lows[ticker].dropna(), closes[ticker].dropna()
            
            opt, prem, pt1, pt2, pt3 = generate_quant_option(close_p, t1, t2, t3, df_h, df_l, df_c, stock_dte, stock_label)
            
            tv_clean_sym = symbol.replace("&", "_").replace("-", "_")
            
            record = {
                'Stock': symbol, 'Horizon': hor, 'Entry': round(close_p, 2), 'RSI': round(rsi_val,1), 'Vol vs 50d': vol_vs,
                'EqSL': round(close_p-1.5*atr,1), 'EqT1': t1, 'EqT2': t2, 'EqT3': t3, 'EqT4': t4, 'EqT5': t5,
                'Opt': opt, 'Prem': prem, 'PT1': pt1, 'PT2': pt2, 'PT3': pt3, 'Score': base_score,
                'TV_Link': f"https://in.tradingview.com/chart/?symbol=NSE:{tv_clean_sym}"
            }

            if passes_ema and base_score >= 2:
                valid_setups.append(record)
        except: continue

    if valid_setups:
        df_all = pd.DataFrame(valid_setups).drop_duplicates(subset=['Stock']).sort_values(by=['Score', 'RSI'], ascending=[False, False])
        return df_all
    return pd.DataFrame()

# --- VIEW: DASHBOARD ---
if page == "Dashboard":
    st.title("Institutional Quant Trading System (ISTS Pro)")
    st.markdown("Live Market Top-Down Momentum & Options Engine")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Market Status", "OPEN", "NSE Live Feed")
    col2.metric("Scan Universe", "NSE F&O Liquid", "Firewall-Proof")
    col3.metric("Math Engine", "Black-Scholes", "Options Data")
    col4.metric("Strategy", "5-Target Vector", "ATR/Lorentzian")

# --- VIEW: SCAN MARKET ---
elif page == "Scan Market":
    st.title("🚀 Master Quant Scanner")
    st.markdown("Scans F&O Universe for precise EMA/RSI momentum and runs Black-Scholes premium targets.")

    if st.button("Run Live Quant Scan", type="primary"):
        with st.spinner("Crunching indicator matrix and pricing options..."):
            df_res = run_quant_scan()
            st.session_state['quant_results'] = df_res
            st.success("Quant Scan complete!")

    if 'quant_results' in st.session_state and not st.session_state['quant_results'].empty:
        df_results = st.session_state['quant_results'].copy()
        
        if 'TV_Link' not in df_results.columns:
            df_results['TV_Link'] = df_results['Stock'].apply(
                lambda s: f"https://in.tradingview.com/chart/?symbol=NSE:{str(s).replace('&', '_').replace('-', '_')}"
            )

        df_results['Eq Tgts (1-5)'] = df_results['EqT1'].astype(str) + "/" + df_results['EqT2'].astype(str) + "/" + df_results['EqT3'].astype(str) + "/" + df_results['EqT4'].astype(str) + "/" + df_results['EqT5'].astype(str)
        df_results['Prem Tgts (1-3)'] = df_results['PT1'].astype(str) + "/" + df_results['PT2'].astype(str) + "/" + df_results['PT3'].astype(str)
        
        st.markdown("---")
        st.subheader("🌟 Top 5 High Conviction Setups")
        
        hc_cols = ['Stock', 'Horizon', 'Entry', 'EqSL', 'Eq Tgts (1-5)', 'Opt', 'Prem', 'Prem Tgts (1-3)', 'TV_Link']
        st.dataframe(
            df_results.head(5)[hc_cols], 
            use_container_width=True, 
            hide_index=True,
            column_config={"TV_Link": st.column_config.LinkColumn("Live Chart", display_text="📊 View in TV")}
        )

        st.markdown("---")
        st.subheader("📊 Full Market Scan by Horizon")
        tab1, tab2, tab3 = st.tabs(["⚡ Intraday", "🌙 BTST", "📈 Swing"])
        
        full_cols = ['Stock', 'RSI', 'Vol vs 50d', 'Entry', 'EqSL', 'Eq Tgts (1-5)', 'Opt', 'Prem', 'Prem Tgts (1-3)', 'TV_Link']
        
        with tab1:
            df_intra = df_results[df_results['Horizon'] == 'Intraday']
            if not df_intra.empty: st.dataframe(df_intra[full_cols], use_container_width=True, hide_index=True, column_config={"TV_Link": st.column_config.LinkColumn("Live Chart", display_text="📊 View in TV")})
            else: st.info("No Intraday setups found right now.")
                
        with tab2:
            df_btst = df_results[df_results['Horizon'] == 'BTST']
            if not df_btst.empty: st.dataframe(df_btst[full_cols], use_container_width=True, hide_index=True, column_config={"TV_Link": st.column_config.LinkColumn("Live Chart", display_text="📊 View in TV")})
            else: st.info("No BTST setups found right now.")
                
        with tab3:
            df_swing = df_results[df_results['Horizon'] == 'Swing']
            if not df_swing.empty: st.dataframe(df_swing[full_cols], use_container_width=True, hide_index=True, column_config={"TV_Link": st.column_config.LinkColumn("Live Chart", display_text="📊 View in TV")})
            else: st.info("No Swing setups found right now.")

        st.markdown("---")
        st.subheader("🔍 Live TradingView Analysis & Execution")
        selected_stock = st.selectbox("Select stock to load live chart:", df_results['Stock'].tolist())
        
        tv_symbol = selected_stock.replace("&", "_").replace("-", "_")
        
        tv_widget = f"""
        <div class="tradingview-widget-container" style="height:600px;width:100%;">
          <div id="tradingview_widget_{tv_symbol}" style="height:600px;width:100%;"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
          new TradingView.widget({{
          "autosize": true,
          "symbol": "BSE:{tv_symbol}",
          "interval": "D",
          "timezone": "Asia/Kolkata",
          "theme": "dark",
          "style": "1",
          "locale": "in",
          "enable_publishing": false,
          "allow_symbol_change": true,
          "container_id": "tradingview_widget_{tv_symbol}"
        }});
          </script>
        </div>
        """
        components.html(tv_widget, height=610)

        st.markdown("### ⚡ Execute Trade")
        b1, b2, b3 = st.columns(3)
        with b1: st.link_button("🟠 Trade on Dhan", "https://web.dhan.co/", use_container_width=True)
        with b2: st.link_button("🔵 Trade on Angel One", "https://trade.angelone.in/", use_container_width=True)
        with b3: st.link_button("📈 Open Full Chart", f"https://in.tradingview.com/chart/?symbol=NSE:{tv_symbol}", use_container_width=True)

        st.markdown("---")
        stock_row = df_results[df_results['Stock'] == selected_stock].iloc[0]
        st.subheader(f"🧮 Position Size & Risk Calculator: {selected_stock}")
        c1, c2, c3 = st.columns(3)
        capital = c1.number_input("Account Capital (₹)", min_value=10000, value=500000, step=25000)
        risk_pct = c2.number_input("Risk Limit per Trade (%)", min_value=0.25, max_value=5.0, value=1.0, step=0.25)
        
        entry_p = stock_row['Entry']
        sl_p = c3.number_input("Stop Loss Price (₹) [Default: 1.5x ATR]", min_value=1.0, value=float(stock_row['EqSL']), step=1.0)
        
        risk_per_share = entry_p - sl_p
        if risk_per_share > 0:
            max_risk = (capital * risk_pct) / 100.0
            qty = int(max_risk / risk_per_share)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Quantity to Buy", f"{qty} shares")
            m2.metric("Total Investment", f"₹{(qty * entry_p):,.2f}")
            m3.metric("Max Capital at Risk", f"₹{max_risk:,.2f}")
            m4.metric("Target 3 Profit", f"₹{(qty * (stock_row['EqT3'] - entry_p)):,.2f}")

# --- VIEW: BUDGET SCANNER (< ₹500) ---
elif page == "Budget Scanner (< ₹500)":
    st.title("💡 Sub-₹500 Budget Quant Scanner")

    budget_limit = st.number_input("Max Stock Price (₹)", min_value=50, max_value=1000, value=500, step=50)

    if st.button("Run Budget Market Scan", type="primary"):
        with st.spinner(f"Scanning for setups under ₹{budget_limit}..."):
            full_res = run_quant_scan()
            if not full_res.empty:
                budget_res = full_res[full_res['Entry'] <= budget_limit].copy()
                if not budget_res.empty:
                    st.session_state['budget_results'] = budget_res
                    st.success(f"Found {len(budget_res)} quant setups under ₹{budget_limit}!")
                else:
                    st.session_state['budget_results'] = pd.DataFrame()
                    st.warning(f"No setups found under ₹{budget_limit} today.")

    if 'budget_results' in st.session_state and not st.session_state['budget_results'].empty:
        df_budget = st.session_state['budget_results'].copy()
        
        if 'TV_Link' not in df_budget.columns:
            df_budget['TV_Link'] = df_budget['Stock'].apply(
                lambda s: f"https://in.tradingview.com/chart/?symbol=NSE:{str(s).replace('&', '_').replace('-', '_')}"
            )
        
        df_budget['Eq Tgts (1-5)'] = df_budget['EqT1'].astype(str) + "/" + df_budget['EqT2'].astype(str) + "/" + df_budget['EqT3'].astype(str) + "/" + df_budget['EqT4'].astype(str) + "/" + df_budget['EqT5'].astype(str)
        df_budget['Prem Tgts (1-3)'] = df_budget['PT1'].astype(str) + "/" + df_budget['PT2'].astype(str) + "/" + df_budget['PT3'].astype(str)

        st.subheader(f"🏆 Top Budget Quant Setups Under ₹{budget_limit}")
        b_cols = ['Stock', 'Horizon', 'Entry', 'EqSL', 'Eq Tgts (1-5)', 'Opt', 'Prem', 'Prem Tgts (1-3)', 'TV_Link']
        st.dataframe(
            df_budget[b_cols], 
            use_container_width=True, 
            hide_index=True,
            column_config={"TV_Link": st.column_config.LinkColumn("Live Chart", display_text="📊 View in TV")}
        )

        st.markdown("---")
        st.subheader("🔍 Budget Position Calculator")
        selected_stock = st.selectbox("Select stock to evaluate:", df_budget['Stock'].tolist())
        stock_row = df_budget[df_budget['Stock'] == selected_stock].iloc[0]

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Stock:** `{selected_stock}`")
            st.markdown(f"**Entry Price:** ₹{stock_row['Entry']}")
            st.markdown(f"**Base Quant Score:** {stock_row['Score']}")
            st.markdown(f"**Option Recommendation:** `{stock_row['Opt']}` at ₹{stock_row['Prem']}")
        
        with col2:
            trade_capital = st.number_input("Allocated Capital for this Trade (₹)", min_value=5000, value=50000, step=5000)
            shares_qty = int(trade_capital // stock_row['Entry'])
            actual_inv = round(shares_qty * stock_row['Entry'], 2)
            st.metric("Affordable Shares", f"{shares_qty} shares")
            st.metric("Total Investment Required", f"₹{actual_inv:,.2f}")
