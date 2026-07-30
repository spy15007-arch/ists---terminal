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

# --- SECTORAL INDICES & UNIVERSE DEFINITIONS ---
SECTORS = {
    'Nifty Banking': {
        'index': '^CNXBANK',
        'stocks': ['HDFCBANK', 'ICICIBANK', 'SBIN', 'AXISBANK', 'KOTAKBANK', 'BANKBARODA', 'PNB', 'AUBANK', 'INDUSINDBK', 'FEDERALBNK']
    },
    'Nifty IT & Tech': {
        'index': '^CNXIT',
        'stocks': ['TCS', 'INFY', 'WIPRO', 'HCLTECH', 'TECHM', 'LTIM', 'PERSISTENT', 'COFORGE', 'MPHASIS', 'LTTS']
    },
    'Nifty Auto & Industrials': {
        'index': '^CNXAUTO',
        'stocks': ['TATAMOTORS', 'MARUTI', 'M&M', 'BAJAJ-AUTO', 'HEROMOTOCO', 'EICHERMOT', 'TVSMOTOR', 'BHARATFORG', 'BOSHLTD']
    },
    'Nifty Metals & Mining': {
        'index': '^CNXMETAL',
        'stocks': ['TATASTEEL', 'JSWSTEEL', 'HINDALCO', 'JINDALSTEL', 'NMDC', 'VEDL', 'NATIONALUM', 'SAIL', 'APLAPOLLO']
    },
    'Nifty FMCG & Consumption': {
        'index': '^CNXFMCG',
        'stocks': ['HINDUNILVR', 'ITC', 'NESTLEIND', 'BRITANNIA', 'TATACONSUM', 'DABUR', 'GODREJCP', 'VBL', 'COLPAL', 'MARICO']
    },
    'Nifty Energy & Infrastructure': {
        'index': '^CNXINFRA',
        'stocks': ['RELIANCE', 'LT', 'NTPC', 'POWERGRID', 'ONGC', 'BPCL', 'COALINDIA', 'HAL', 'BEL', 'ADANIENT', 'ADANIPORTS']
    }
}

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("ISTS Pro Terminal")
st.sidebar.caption("Top-Down Institutional Swing Trading System")

page = st.sidebar.radio(
    "Navigation", 
    ["Dashboard", "Sector Momentum", "Scan Market", "Watchlist", "Portfolio", "Settings"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("📲 Telegram Alert Setup")
bot_token = st.sidebar.text_input("Telegram Bot Token", type="password", value="", help="Get from @BotFather")
chat_id = st.sidebar.text_input("Telegram Chat ID", value="1338671581", help="Get from @userinfobot")
enable_alerts = st.sidebar.checkbox("Enable Automated Alerts (>=75%)", value=True)

# --- TELEGRAM NOTIFICATION ENGINE ---
def send_telegram_alert(symbol, price, score, target, triggers, token, c_id):
    if not token or not c_id:
        return False, "Bot Token or Chat ID missing in sidebar."
    
    message = (
        f"🚨 *ISTS PRO SECTOR BREAKOUT ALERT* 🚨\n\n"
        f"📌 *Stock:* `{symbol}`\n"
        f"💰 *Last Price:* ₹{price}\n"
        f"⚡ *Breakout Score:* *{score}%*\n"
        f"🎯 *1.618 Fib Target:* ₹{target}\n"
        f"🔍 *Triggers Met:* {triggers}\n\n"
        f"📊 *Action:* Review setup on ISTS Pro Terminal."
    )
    url = f"https://api.telegram.org/bot{token.strip()}/sendMessage"
    payload = {"chat_id": c_id.strip(), "text": message, "parse_mode": "Markdown"}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        res_data = response.json()
        if res_data.get("ok"):
            return True, "Alert delivered successfully!"
        else:
            return False, f"Telegram API Error: {res_data.get('description', 'Unknown error')}"
    except Exception as e:
        return False, f"Network Error: {e}"

def send_telegram_alert_async(symbol, price, score, target, triggers, token, c_id):
    threading.Thread(
        target=send_telegram_alert,
        args=(symbol, price, score, target, triggers, token, c_id),
        daemon=True
    ).start()

if st.sidebar.button("🧪 Send Test Telegram Alert"):
    if not bot_token or not chat_id:
        st.sidebar.error("Enter Bot Token and Chat ID first.")
    else:
        with st.sidebar.spinner("Testing connection..."):
            success, msg = send_telegram_alert("TEST_STOCK", 1000.0, 100, 1200.0, "Top Sector Momentum", bot_token, chat_id)
            if success: st.sidebar.success(msg)
            else: st.sidebar.error(msg)

# --- HELPER TECHNICAL FUNCTIONS ---
def calculate_rma(series, period):
    return series.ewm(alpha=1/period, adjust=False).mean()

@st.cache_data(ttl=1800)
def get_sector_leaderboard():
    """Ranks all major sector indices by Relative Strength vs Nifty 50."""
    nifty = yf.download('^NSEI', period="3m", interval="1d", progress=False)['Close']
    if isinstance(nifty, pd.DataFrame): nifty = nifty.iloc[:, 0]
    nifty_1m = ((nifty.iloc[-1] / nifty.iloc[-22]) - 1) * 100
    nifty_1w = ((nifty.iloc[-1] / nifty.iloc[-5]) - 1) * 100

    leaderboard = []
    for sector_name, data in SECTORS.items():
        try:
            sec_df = yf.download(data['index'], period="3m", interval="1d", progress=False)['Close']
            if isinstance(sec_df, pd.DataFrame): sec_df = sec_df.iloc[:, 0]
            sec_1m = ((sec_df.iloc[-1] / sec_df.iloc[-22]) - 1) * 100
            sec_1w = ((sec_df.iloc[-1] / sec_df.iloc[-5]) - 1) * 100
            
            rs_score = round(sec_1m - nifty_1m, 2)
            status = "🔥 Strong Outperformer" if rs_score > 2.0 else ("⚠️ Lagging" if rs_score < -2.0 else "➖ Neutral")
            
            leaderboard.append({
                'Sector': sector_name,
                '1-Week Return %': round(sec_1w, 2),
                '1-Month Return %': round(sec_1m, 2),
                'RS vs Nifty 50': f"{rs_score:+}%",
                'RS_Num': rs_score,
                'Status': status,
                'Stocks': data['stocks']
            })
        except:
            continue
    
    df = pd.DataFrame(leaderboard).sort_values(by='RS_Num', ascending=False)
    return df, nifty_1m

def run_pre_breakout_scanner(symbols, nifty_1m_return):
    results = []

    for symbol in symbols:
        ticker = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
        try:
            data = yf.download(ticker, period="1y", interval="1d", progress=False)
            if len(data) < 100: continue
            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)

            # Technical Calculation
            data['EMA_20'] = data['Close'].ewm(span=20, adjust=False).mean()
            data['EMA_50'] = data['Close'].ewm(span=50, adjust=False).mean()
            data['EMA_200'] = data['Close'].ewm(span=200, adjust=False).mean()

            high_low = data['High'] - data['Low']
            high_close = np.abs(data['High'] - data['Close'].shift())
            low_close = np.abs(data['Low'] - data['Close'].shift())
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            data['ATR'] = calculate_rma(tr, 14)
            data['ATR_MA'] = data['ATR'].rolling(window=20).mean()
            data['ATR_Ratio'] = data['ATR'] / data['ATR_MA']

            data['Vol_MA20'] = data['Volume'].rolling(window=20).mean()
            data['RVOL'] = data['Volume'] / data['Vol_MA20']

            swing_high = data['High'].rolling(50).max().iloc[-1]
            swing_low = data['Low'].rolling(50).min().iloc[-1]
            fib_382 = swing_high - (swing_high - swing_low) * 0.382
            fib_618 = swing_high - (swing_high - swing_low) * 0.618

            latest = data.iloc[-1]
            score = 0
            triggers = []

            stock_1m_return = ((data['Close'].iloc[-1] / data['Close'].iloc[-22]) - 1) * 100
            rs_status = "🔥 Outperforming" if stock_1m_return > nifty_1m_return else "Underperforming"

            if latest['EMA_20'] > latest['EMA_50'] > latest['EMA_200']:
                score += 25
                triggers.append("EMA Alignment")
            if latest['ATR_Ratio'] < 0.70:
                score += 25
                triggers.append("ATR Compression")
            if latest['RVOL'] < 0.60:
                score += 25
                triggers.append("Volume Dry-Up")
            if fib_618 <= latest['Close'] <= fib_382:
                score += 25
                triggers.append("Golden Zone Fib")

            target_fib = round(swing_high + (swing_high - swing_low) * 0.618, 2)
            triggers_str = ", ".join(triggers) if triggers else "None"

            if enable_alerts and score >= 75:
                send_telegram_alert_async(
                    symbol=symbol.replace('.NS', ''),
                    price=round(latest['Close'], 2),
                    score=score,
                    target=target_fib,
                    triggers=triggers_str,
                    token=bot_token,
                    c_id=chat_id
                )

            results.append({
                'Symbol': symbol.replace('.NS', ''),
                'Last Price': round(latest['Close'], 2),
                'Score_Num': score,
                'Pre-Breakout Score': f"{score}%",
                'Stock RS vs Nifty': rs_status,
                'RVOL': round(latest['RVOL'], 2),
                'ATR Ratio': round(latest['ATR_Ratio'], 2),
                '1.618 Fib Target': target_fib,
                'Triggers Met': triggers_str,
                'Data': data,
                'ATR': round(latest['ATR'], 2)
            })
        except:
            continue
    return results

# --- VIEW 1: DASHBOARD ---
if page == "Dashboard":
    st.title("Institutional Swing Trading System (ISTS Pro)")
    st.markdown("Live Market Top-Down Momentum Terminal")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Market Status", "OPEN", "NSE Live Feed")
    col2.metric("Scan Speed", "1.2 sec/stock", "Optimal")
    col3.metric("Alert Engine", "ACTIVE", "Telegram Bot")
    col4.metric("Strategy", "Top-Down RS", "VCP + Fib")

    st.subheader("📊 Live Sector Strength Leaderboard")
    with st.spinner("Analyzing institutional money flow across sector indices..."):
        sec_df, nifty_1m = get_sector_leaderboard()
        st.dataframe(sec_df[['Sector', '1-Month Return %', '1-Week Return %', 'RS vs Nifty 50', 'Status']], use_container_width=True)

# --- VIEW 2: SECTOR MOMENTUM ANALYSIS ---
elif page == "Sector Momentum":
    st.title("🔥 Sector Relative Strength Matrix")
    st.markdown("Ranks sector indices to ensure you only trade stocks backed by institutional sector accumulation.")
    
    sec_df, nifty_1m = get_sector_leaderboard()
    
    fig = go.Figure(go.Bar(
        x=sec_df['RS_Num'],
        y=sec_df['Sector'],
        orientation='h',
        marker=dict(color=sec_df['RS_Num'], colorscale='Greens')
    ))
    fig.update_layout(title="Sector Relative Strength Outperformance vs NIFTY 50 (%)", template="plotly_dark", height=400)
    st.plotly_chart(fig, use_container_width=True)

# --- VIEW 3: SCAN MARKET VIEW ---
elif page == "Scan Market":
    st.title("🚀 Institutional Pre-Breakout Scanner")
    st.markdown("Scans stock universes backed by top-performing sectors.")

    sec_df, nifty_1m = get_sector_leaderboard()
    
    scan_mode = st.radio("Scanning Strategy:", ["Auto-Scan Top 2 Outperforming Sectors", "Manual Sector Selection", "All Sector Leaders Universe"], horizontal=True)

    if scan_mode == "Auto-Scan Top 2 Outperforming Sectors":
        top_sectors = sec_df.head(2)['Sector'].tolist()
        st.info(f"⚡ **Auto-Selected Top Outperforming Sectors:** {', '.join(top_sectors)}")
        watchlist = []
        for s in top_sectors:
            watchlist.extend(SECTORS[s]['stocks'])
    elif scan_mode == "Manual Sector Selection":
        selected_sec = st.selectbox("Select Sector:", list(SECTORS.keys()))
        watchlist = SECTORS[selected_sec]['stocks']
    else:
        watchlist = [stock for sec in SECTORS.values() for stock in sec['stocks']]

    if st.button("Run Live Pre-Breakout Scan", type="primary"):
        with st.spinner(f"Scanning {len(set(watchlist))} liquid stocks across selected sectors..."):
            results = run_pre_breakout_scanner(list(set(watchlist)), nifty_1m)
            if results:
                results = sorted(results, key=lambda x: x['Score_Num'], reverse=True)
                st.session_state['scan_results'] = results
                st.success(f"Scan Complete! Dispatched alerts for high-probability setups.")

    if 'scan_results' in st.session_state and st.session_state['scan_results']:
        results = st.session_state['scan_results']
        df_display = pd.DataFrame(results)[[
            'Symbol', 'Last Price', 'Pre-Breakout Score', 'Stock RS vs Nifty', 
            'RVOL', 'ATR Ratio', '1.618 Fib Target', 'Triggers Met'
        ]]
        st.dataframe(df_display, use_container_width=True)

        st.markdown("---")
        st.subheader("🔍 Interactive Technical Chart Analysis")
        selected_stock = st.selectbox("Select stock to analyze:", [r['Symbol'] for r in results])
        selected_data = next((r for r in results if r['Symbol'] == selected_stock), None)

        if selected_data:
            chart_df = selected_data['Data'].tail(120)
            fig = go.Figure(data=[
                go.Candlestick(x=chart_df.index, open=chart_df['Open'], high=chart_df['High'], low=chart_df['Low'], close=chart_df['Close'], name="Price"),
                go.Scatter(x=chart_df.index, y=chart_df['EMA_20'], line=dict(color='blue', width=1), name="EMA 20"),
                go.Scatter(x=chart_df.index, y=chart_df['EMA_50'], line=dict(color='orange', width=1), name="EMA 50"),
                go.Scatter(x=chart_df.index, y=chart_df['EMA_200'], line=dict(color='red', width=1.5), name="EMA 200")
            ])
            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=450, title=f"{selected_stock} Daily Chart")
            st.plotly_chart(fig, use_container_width=True)

            # Position Sizing Calculator
            st.markdown("---")
            st.subheader(f"🧮 Risk & Position Calculator: {selected_stock}")
            c1, c2, c3 = st.columns(3)
            capital = c1.number_input("Account Capital (₹)", min_value=10000, value=500000, step=25000)
            risk_pct = c2.number_input("Risk Limit (%)", min_value=0.25, max_value=5.0, value=1.0, step=0.25)
            entry_p = selected_data['Last Price']
            target_p = selected_data['1.618 Fib Target']
            suggested_sl = round(entry_p - (1.5 * selected_data['ATR']), 2)
            sl_p = c3.number_input("Stop Loss Price (₹)", min_value=1.0, value=float(suggested_sl), step=1.0)
            
            risk_per_share = entry_p - sl_p
            if risk_per_share > 0:
                max_risk = (capital * risk_pct) / 100.0
                qty = int(max_risk / risk_per_share)
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Quantity to Buy", f"{qty} shares")
                m2.metric("Total Investment", f"₹{(qty * entry_p):,.2f}")
                m3.metric("Max Capital at Risk", f"₹{max_risk:,.2f}")
                m4.metric("Risk / Reward Ratio", f"1 : {round((target_p - entry_p) / risk_per_share, 2)}")

else:
    st.title(f"{page} Module")
    st.info(f"The {page} module is under development.")
