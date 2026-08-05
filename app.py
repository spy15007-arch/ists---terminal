import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import math
import uuid
from scipy.stats import norm

st.set_page_config(page_title="ISTS Pro Dashboard", page_icon="📈", layout="wide")

# --- FIREWALL-PROOF F&O UNIVERSE ---
STATIC_FNO = ["AARTIIND", "ABB", "ABBOTINDIA", "ABCAPITAL", "ABFRL", "ACC", "ADANIENT", "ADANIPORTS", "ALKEM", "AMBUJACEM", "APOLLOHOSP", "APOLLOTYRE", "ASHOKLEY", "ASIANPAINT", "ASTRAL", "ATUL", "AUBANK", "AUROPHARMA", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BALKRISIND", "BALRAMCHIN", "BANDHANBNK", "BANKBARODA", "BATAINDIA", "BEL", "BERGEPAINT", "BHARATFORG", "BHARTIARTL", "BHEL", "BIOCON", "BOSCHLTD", "BPCL", "BRITANNIA", "CANBK", "CANFINHOME", "CHAMBLFERT", "CHOLAFIN", "CIPLA", "COALINDIA", "COFORGE", "COLPAL", "CONCOR", "COROMANDEL", "CROMPTON", "CUB", "CUMMINSIND", "DABUR", "DALBHARAT", "DEEPAKNTR", "DIVISLAB", "DIXON", "DLF", "DRREDDY", "EICHERMOT", "ESCORTS", "EXIDEIND", "FEDERALBNK", "GAIL", "GLENMARK", "GMRINFRA", "GNFC", "GODREJCP", "GODREJPROP", "GRANULES", "GRASIM", "GUJGASLTD", "HAL", "HAVELLS", "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDCOPPER", "HINDPETRO", "HINDUNILVR", "ICICIBANK", "ICICIGI", "ICICIPRULI", "IDEA", "IDFCFIRSTB", "IEX", "IGL", "INDHOTEL", "INDIACEM", "INDIAMART", "INDIGO", "INDUSINDBK", "INFY", "IOC", "IPCALAB", "IRCTC", "ITC", "JINDALSTEL", "JSWSTEEL", "JUBLFOOD", "KOTAKBANK", "LALPATHLAB", "LAURUSLABS", "LICHSGFIN", "LT", "LTIM", "LTTS", "LUPIN", "M&M", "M&MFIN", "MANAPPURAM", "MARICO", "MARUTI", "MCDOWELL-N", "MCX", "METROPOLIS", "MFSL", "MGL", "MOTHERSON", "MPHASIS", "MRF", "MUTHOOTFIN", "NATIONALUM", "NAUKRI", "NAVINFLUOR", "NESTLEIND", "NMDC", "NTPC", "OBEROIRLTY", "OFSS", "ONGC", "PAGEIND", "PEL", "PETRONET", "PFC", "PIDILITIND", "PIIND", "PNB", "POLYCAB", "POWERGRID", "PVRINOX", "RAMCOCEM", "RBLBANK", "RECLTD", "RELIANCE", "SAIL", "SBICARD", "SBILIFE", "SBIN", "SHREECEM", "SHRIRAMFIN", "SIEMENS", "SRF", "SUNPHARMA", "SUNTV", "SYNGENE", "TATACHEM", "TATACOMM", "TATACONSUM", "TATAMOTORS", "TATAPOWER", "TATASTEEL", "TCS", "TECHM", "TITAN", "TORNTPHARM", "TRENT", "TVSMOTOR", "UBL", "ULTRACEMCO", "UPL", "VEDL", "VOLTAS", "WIPRO", "ZEEL", "ZYDUSLIFE"]

st.sidebar.title("ISTS Pro Terminal")
page = st.sidebar.radio("Navigation", ["Dashboard", "Scan Market", "Budget Scanner (< ₹500)"])

def get_session_info():
    hour = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)).hour
    return "Intraday" if hour < 14 else "BTST"

def black_scholes(S, K, T, r, sigma, opt_type="CE"):
    if T <= 0 or sigma == 0: return max(0, S - K) if opt_type == "CE" else max(0, K - S)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if opt_type == "CE": return round(S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2), 2)
    else: return round(K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1), 2)

def generate_quant_option(price, t1, t2, t3, df_h, df_l, df_c, direction="Bullish", horizon="Intraday"):
    dte = 5 if horizon == "Intraday" else 15 
    step = 100 if price > 5000 else (50 if price > 2000 else (20 if price > 1000 else (10 if price > 500 else 5)))
    atm = int(round(price / step) * step)
    opt_type = "CE" if direction == "Bullish" else "PE"
    
    try:
        vol = math.sqrt((1.0 / (4.0 * math.log(2.0))) * ((np.log(df_h/df_l)**2).tail(10).mean())) * math.sqrt(252)
        if math.isnan(vol) or vol == 0: vol = np.log(df_c/df_c.shift(1)).tail(10).std() * math.sqrt(252)
        if math.isnan(vol) or vol == 0: vol = 0.2
    except: vol = 0.2
    
    c_prem = black_scholes(price, atm, dte/365.0, 0.07, vol, opt_type)
    
    if horizon == "Intraday":
        ot1 = price + (t1 - price) * 0.4 if direction == "Bullish" else price - (price - t1) * 0.4
        ot2 = price + (t2 - price) * 0.7 if direction == "Bullish" else price - (price - t2) * 0.7
        ot3 = t1
    else:
        ot1, ot2, ot3 = t1, t2, t3

    pt1 = black_scholes(ot1, atm, dte/365.0, 0.07, vol, opt_type)
    pt2 = black_scholes(ot2, atm, dte/365.0, 0.07, vol, opt_type)
    pt3 = black_scholes(ot3, atm, dte/365.0, 0.07, vol, opt_type)
    
    return f"{atm} {opt_type}", c_prem, round(pt1, 1), round(pt2, 1), round(pt3, 1)

@st.cache_data(ttl=1800)
def get_index_options_ideas():
    indices_map = {'^NSEI': 'NIFTY 50', '^NSEBANK': 'BANK NIFTY'}
    results = []
    
    for ticker, name in indices_map.items():
        try:
            data = yf.Ticker(ticker).history(period="6mo")
            if data.empty: continue
            
            df_c = data['Close'].dropna()
            df_h = data['High'].dropna()
            df_l = data['Low'].dropna()
            if df_c.empty: continue
            
            close_p = float(df_c.iloc[-1])
            ema_50 = float(df_c.ewm(span=50).mean().iloc[-1])
            
            hl = df_h - df_l
            hc = (df_h - df_c.shift(1)).abs()
            lc = (df_l - df_c.shift(1)).abs()
            tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
            atr = float(tr.ewm(alpha=1/14).mean().iloc[-1])
            
            delta = df_c.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rsi_val = float((100 - (100 / (1 + (gain / loss)))).iloc[-1])
            
            if close_p > ema_50:
                direction, t1, t2, t3, t4, t5 = "Bullish (Call)", *[round(close_p + m * atr, 1) for m in (0.3, 0.6, 0.9, 1.2, 1.5)]
                eq_sl = round(close_p - 0.6 * atr, 1)
            else:
                direction, t1, t2, t3, t4, t5 = "Bearish (Put)", *[round(close_p - m * atr, 1) for m in (0.3, 0.6, 0.9, 1.2, 1.5)]
                eq_sl = round(close_p + 0.6 * atr, 1)
            
            opt, prem, pt1, pt2, pt3 = generate_quant_option(close_p, t1, t2, t3, df_h, df_l, df_c, direction.split(" ")[0], "Intraday")
            
            tv_sym = "NIFTY" if name == "NIFTY 50" else "BANKNIFTY"
            
            results.append({
                'Stock': f"{name} {direction}", 'RawStock': tv_sym, 'Horizon': 'Intraday', 'Entry': round(close_p, 2),
                'RSI': round(rsi_val, 1), 'Vol vs 50d': 'N/A', 'EqSL': eq_sl,
                'EqT1': t1, 'EqT2': t2, 'EqT3': t3, 'EqT4': t4, 'EqT5': t5,
                'Opt': opt, 'Prem': prem, 'PT1': pt1, 'PT2': pt2, 'PT3': pt3, 'Score': 10,
                'TV_Link': f"https://in.tradingview.com/chart/?symbol=NSE:{tv_sym}"
            })
        except Exception as e: pass
        
    df = pd.DataFrame(results)
    if not df.empty:
        df.insert(0, '#', range(1, len(df) + 1))
    return df

@st.cache_data(ttl=1800)
def run_quant_scan():
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    market_open = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
    minutes_elapsed = min(max(1, (now_ist - market_open).total_seconds() / 60), 375)
    
    tickers = [f"{s}.NS" for s in STATIC_FNO]
    data = yf.download(tickers, period="6mo", interval="1d", progress=False, threads=True)
    if data.empty: return pd.DataFrame()
    
    closes, highs, lows, volumes = data['Close'], data['High'], data['Low'], data['Volume']
    ema_50_daily = closes.ewm(span=50).mean()
    vol_50d_avg_daily = volumes.rolling(50).mean()
    
    delta = closes.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rsi_daily = 100 - (100 / (1 + (gain / loss)))

    exp1, exp2 = closes.ewm(span=12, adjust=False).mean(), closes.ewm(span=26, adjust=False).mean()
    macd_daily = exp1 - exp2
    macd_signal_daily = macd_daily.ewm(span=9, adjust=False).mean()
    
    hl = highs - lows
    hc, lc = (highs - closes.shift(1)).abs(), (lows - closes.shift(1)).abs()
    tr = pd.DataFrame(np.maximum(hl.values, np.maximum(hc.values, lc.values)), index=hl.index, columns=hl.columns)
    atr_daily = tr.ewm(alpha=1/14).mean()
    
    closes_weekly = closes.resample('W').last().dropna(how='all')
    ema_50_weekly = closes_weekly.ewm(span=50).mean()

    last_close, last_high, last_low = closes.iloc[-1], highs.iloc[-1], lows.iloc[-1]
    last_vol, last_vol_50 = volumes.iloc[-1], vol_50d_avg_daily.iloc[-1]
    last_rsi, last_macd, last_macd_sig = rsi_daily.iloc[-1], macd_daily.iloc[-1], macd_signal_daily.iloc[-1]
    last_ema_50, last_atr = ema_50_daily.iloc[-1], atr_daily.iloc[-1]
    last_ema_50_weekly = ema_50_weekly.iloc[-1]

    valid_setups = []

    for ticker in closes.columns:
        try:
            close_p, vol_today = float(last_close[ticker]), float(last_vol[ticker])
            if pd.isna(close_p) or close_p <= 0 or vol_today < 1000: continue
            vol_50_avg = float(last_vol_50[ticker])
            if pd.isna(vol_50_avg) or vol_50_avg <= 0: continue
            
            rsi_val, macd_val, macd_sig = float(last_rsi[ticker]), float(last_macd[ticker]), float(last_macd_sig[ticker])
            d_ema, w_ema, atr = float(last_ema_50[ticker]), float(last_ema_50_weekly[ticker]), float(last_atr[ticker])
            
            adjusted_vol_50 = vol_50_avg * (minutes_elapsed / 375.0)
            vol_vs = round(vol_today / adjusted_vol_50, 2)
            
            if vol_vs >= 1.5:
                hor, m1, m2, m3, m4, m5, sl_m = "Intraday", 0.3, 0.6, 0.9, 1.2, 1.5, 0.6
            elif vol_vs >= 1.2:
                hor, m1, m2, m3, m4, m5, sl_m = "BTST", 0.6, 1.2, 1.8, 2.4, 3.0, 0.8
            else:
                hor, m1, m2, m3, m4, m5, sl_m = "Swing", 1.5, 3.0, 4.5, 6.0, 7.5, 1.5

            if close_p > d_ema and close_p > w_ema and macd_val > macd_sig and (55 <= rsi_val <= 75):
                direction = "Bullish"
                t1, t2, t3, t4, t5 = [round(close_p + m * atr, 1) for m in (m1, m2, m3, m4, m5)]
                eq_sl = round(close_p - sl_m * atr, 1)
                base_score = 2 + (2 if vol_vs >= 1.5 else 0)
            elif close_p < d_ema and close_p < w_ema and macd_val < macd_sig and (25 <= rsi_val <= 45):
                direction = "Bearish"
                t1, t2, t3, t4, t5 = [round(close_p - m * atr, 1) for m in (m1, m2, m3, m4, m5)]
                eq_sl = round(close_p + sl_m * atr, 1)
                base_score = 2 + (2 if vol_vs >= 1.5 else 0)
            else:
                continue 

            symbol = ticker.replace(".NS", "")
            df_h, df_l, df_c = highs[ticker].dropna(), lows[ticker].dropna(), closes[ticker].dropna()
            opt, prem, pt1, pt2, pt3 = generate_quant_option(close_p, t1, t2, t3, df_h, df_l, df_c, direction, hor)
            tv_clean_sym = symbol.replace("&", "_").replace("-", "_")
            
            valid_setups.append({
                'Stock': f"{symbol} (↓)" if direction=="Bearish" else f"{symbol} (↑)", 
                'RawStock': symbol,
                'Horizon': hor, 'Entry': round(close_p, 2), 'RSI': round(rsi_val,1), 'Vol vs 50d': vol_vs,
                'EqSL': eq_sl, 'EqT1': t1, 'EqT2': t2, 'EqT3': t3, 'EqT4': t4, 'EqT5': t5, 
                'Opt': opt, 'Prem': prem, 'PT1': pt1, 'PT2': pt2, 'PT3': pt3, 'Score': base_score,
                'TV_Link': f"https://in.tradingview.com/chart/?symbol=NSE:{tv_clean_sym}"
            })
        except: continue

    if valid_setups:
        df_all = pd.DataFrame(valid_setups).drop_duplicates(subset=['Stock']).sort_values(by=['Score', 'RSI'], ascending=[False, False])
        return df_all
    return pd.DataFrame()

if page == "Dashboard":
    st.title("Institutional Quant Trading System (ISTS Pro)")
    st.markdown("Live Market Top-Down MTF Momentum & Options Engine")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Market Status", "MTF ALIGNED", "NSE Live Feed")
    col2.metric("Scan Universe", "NSE F&O Liquid", "Firewall-Proof")
    col3.metric("Math Engine", "Black-Scholes", "Bi-Directional")
    col4.metric("Strategy", "Scaled ATR Vectors", "Scalp/Swing")

elif page == "Scan Market":
    st.title("🚀 Master Quant Scanner")
    st.markdown("Scans F&O Universe matching Daily & Weekly EMA alignment for CE/PE setups.")

    if st.button("Run Live Quant Scan", type="primary"):
        with st.spinner("Crunching indicator matrix and pricing options..."):
            st.session_state['index_results'] = get_index_options_ideas()
            st.session_state['quant_results'] = run_quant_scan()
            st.success("Quant Scan complete!")

    if 'quant_results' in st.session_state:
        df_results = st.session_state['quant_results'].copy()
        
        if not df_results.empty:
            df_results['Eq Tgts (1-5)'] = df_results['EqT1'].astype(str) + "/" + df_results['EqT2'].astype(str) + "/" + df_results['EqT3'].astype(str) + "/" + df_results['EqT4'].astype(str) + "/" + df_results['EqT5'].astype(str)
            df_results['Prem Tgts (1-3)'] = df_results['PT1'].astype(str) + "/" + df_results['PT2'].astype(str) + "/" + df_results['PT3'].astype(str)
            
            st.markdown("---")
            st.subheader("🌟 Top 5 High Conviction Setups")
            
            df_hc = df_results.head(5).copy()
            df_hc.insert(0, '#', range(1, len(df_hc) + 1))
            
            hc_cols = ['#', 'Stock', 'Horizon', 'Entry', 'EqSL', 'Eq Tgts (1-5)', 'Opt', 'Prem', 'Prem Tgts (1-3)', 'TV_Link']
            st.dataframe(df_hc[hc_cols], use_container_width=True, hide_index=True, column_config={"TV_Link": st.column_config.LinkColumn("Live Chart", display_text="📊 View in TV")})
        
        st.markdown("---")
        st.subheader("📊 Full Market Scan by Horizon")
        tab1, tab2, tab3 = st.tabs(["⚡ Intraday", "🌙 BTST", "📈 Swing"])
        
        full_cols = ['#', 'Stock', 'RSI', 'Vol vs 50d', 'Entry', 'EqSL', 'Eq Tgts (1-5)', 'Opt', 'Prem', 'Prem Tgts (1-3)', 'TV_Link']
        
        with tab1:
            if 'index_results' in st.session_state and not st.session_state['index_results'].empty:
                st.markdown("#### 👑 Index Options (Intraday Scalps)")
                df_idx = st.session_state['index_results'].copy()
                df_idx['Eq Tgts (1-5)'] = df_idx['EqT1'].astype(str) + "/" + df_idx['EqT2'].astype(str) + "/" + df_idx['EqT3'].astype(str) + "/" + df_idx['EqT4'].astype(str) + "/" + df_idx['EqT5'].astype(str)
                df_idx['Prem Tgts (1-3)'] = df_idx['PT1'].astype(str) + "/" + df_idx['PT2'].astype(str) + "/" + df_idx['PT3'].astype(str)
                st.dataframe(df_idx[full_cols], use_container_width=True, hide_index=True, column_config={"TV_Link": st.column_config.LinkColumn("Live Chart", display_text="📊 View")})
                st.markdown("<br>", unsafe_allow_html=True)

            st.markdown("#### 📊 Intraday Equity Scans")
            if not df_results.empty:
                df_intra = df_results[df_results['Horizon'] == 'Intraday'].copy()
                if not df_intra.empty: 
                    df_intra.insert(0, '#', range(1, len(df_intra) + 1)) 
                    st.dataframe(df_intra[full_cols], use_container_width=True, hide_index=True, column_config={"TV_Link": st.column_config.LinkColumn("Live Chart", display_text="📊 View")})
                else: st.info("No Intraday equity setups found based on RVOL parameters.")
                
        with tab2:
            if not df_results.empty:
                df_btst = df_results[df_results['Horizon'] == 'BTST'].copy()
                if not df_btst.empty: 
                    df_btst.insert(0, '#', range(1, len(df_btst) + 1)) 
                    st.dataframe(df_btst[full_cols], use_container_width=True, hide_index=True, column_config={"TV_Link": st.column_config.LinkColumn("Live Chart", display_text="📊 View")})
                else: st.info("No BTST setups found.")
                
        with tab3:
            if not df_results.empty:
                df_swing = df_results[df_results['Horizon'] == 'Swing'].copy()
                if not df_swing.empty: 
                    df_swing.insert(0, '#', range(1, len(df_swing) + 1)) 
                    st.dataframe(df_swing[full_cols], use_container_width=True, hide_index=True, column_config={"TV_Link": st.column_config.LinkColumn("Live Chart", display_text="📊 View")})
                else: st.info("No Swing setups found.")

        # --- Native Embedded TradingView Advanced Chart Hub ---
        st.markdown("---")
        st.subheader("🔍 Live TradingView Native Chart Analysis")
        
        df_all_merged = pd.concat([st.session_state.get('index_results', pd.DataFrame()), df_results]) if not df_results.empty else st.session_state.get('index_results', pd.DataFrame())
        
        if not df_all_merged.empty:
            selected_stock = st.selectbox("Select asset to load live embedded chart:", df_all_merged['Stock'].tolist())
            stock_row = df_all_merged[df_all_merged['Stock'] == selected_stock].iloc[0]
            
            # Use the pure NSE symbol for everything (works for 15-min and doesn't get blocked!)
            raw_sym = str(stock_row['RawStock']).strip().replace("&", "_").replace("-", "_")
            widget_sym = f"NSE:{raw_sym}"
            
            # Generate a 100% unique ID for the chart container EVERY time you switch stocks.
            # This completely stops Streamlit from caching Apple (AAPL)!
            unique_id = "tv_chart_" + str(uuid.uuid4().hex)
            
            tv_advanced_widget = f"""
            <div class="tradingview-widget-container" style="height:600px;width:100%;">
              <div id="{unique_id}" style="height:100%;width:100%;"></div>
              <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
              <script type="text/javascript">
              new TradingView.widget(
              {{
                "autosize": true,
                "symbol": "{widget_sym}",
                "interval": "15",
                "timezone": "Asia/Kolkata",
                "theme": "dark",
                "style": "1",
                "locale": "in",
                "enable_publishing": false,
                "hide_top_toolbar": false,
                "save_image": false,
                "container_id": "{unique_id}"
              }});
              </script>
            </div>
            """
            
            components.html(tv_advanced_widget, height=620)

            st.markdown("### ⚡ Execute Broker Trade")
            b1, b2, b3 = st.columns(3)
            with b1: st.link_button("🟠 Trade on Dhan", "https://web.dhan.co/", use_container_width=True)
            with b2: st.link_button("🔵 Trade on Angel One", "https://trade.angelone.in/", use_container_width=True)
            with b3: st.link_button("📈 Open Full Chart on TV", f"https://in.tradingview.com/chart/?symbol={widget_sym}", use_container_width=True)

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

    if st.button("Run Budget Market Scan", type="primary"):
        with st.spinner(f"Scanning for setups under ₹{budget_limit}..."):
            full_res = run_quant_scan()
            if not full_res.empty:
                budget_res = full_res[full_res['Entry'] <= budget_limit].copy()
                if not budget_res.empty:
                    budget_res.insert(0, '#', range(1, len(budget_res) + 1)) 
                    st.session_state['budget_results'] = budget_res
                    st.success(f"Found {len(budget_res)} quant setups under ₹{budget_limit}!")
                else:
                    st.session_state['budget_results'] = pd.DataFrame()
                    st.warning(f"No setups found under ₹{budget_limit} today.")

    if 'budget_results' in st.session_state and not st.session_state['budget_results'].empty:
        df_budget = st.session_state['budget_results'].copy()
        
        df_budget['Eq Tgts (1-5)'] = df_budget['EqT1'].astype(str) + "/" + df_budget['EqT2'].astype(str) + "/" + df_budget['EqT3'].astype(str) + "/" + df_budget['EqT4'].astype(str) + "/" + df_budget['EqT5'].astype(str)
        df_budget['Prem Tgts (1-3)'] = df_budget['PT1'].astype(str) + "/" + df_budget['PT2'].astype(str) + "/" + df_budget['PT3'].astype(str)

        st.subheader(f"🏆 Top Budget Quant Setups Under ₹{budget_limit}")
        b_cols = ['#', 'Stock', 'Horizon', 'Entry', 'EqSL', 'Eq Tgts (1-5)', 'Opt', 'Prem', 'Prem Tgts (1-3)', 'TV_Link']
        st.dataframe(df_budget[b_cols], use_container_width=True, hide_index=True, column_config={"TV_Link": st.column_config.LinkColumn("Live Chart", display_text="📊 View in TV")})

        st.markdown("---")
        st.subheader("🔍 Budget Position & Share Quantity Calculator")
        selected_stock = st.selectbox("Select stock to evaluate:", df_budget['Stock'].tolist())
        stock_row = df_budget[df_budget['Stock'] == selected_stock].iloc[0]
        
        raw_sym = str(stock_row['RawStock']).strip().replace("&", "_").replace("-", "_")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Stock:** `{selected_stock}`")
            st.markdown(f"**Entry Price:** ₹{stock_row['Entry']}")
            st.markdown(f"**Option Recommendation:** `{stock_row['Opt']}` at ₹{stock_row['Prem']}")
        
        with col2:
            trade_capital = st.number_input("Allocated Capital (₹)", min_value=5000, value=50000, step=5000)
            shares_qty = int(trade_capital // float(stock_row['Entry']))
            actual_inv = round(shares_qty * float(stock_row['Entry']), 2)
            st.metric("Affordable Shares", f"{shares_qty} shares")
            st.metric("Total Investment Required", f"₹{actual_inv:,.2f}")
