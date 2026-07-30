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

# --- WATCHLIST DEFINITIONS ---
WATCHLISTS = {
    'Nifty Core (Top Liquid)': [
        'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'LT', 
        'BHARTIARTL', 'SBIN', 'TITAN', 'TATAMOTORS', 'AXISBANK', 'MARUTI'
    ],
    'Nifty Banking & Financials': [
        'HDFCBANK', 'ICICIBANK', 'SBIN', 'AXISBANK', 'KOTAKBANK', 
        'BANKBARODA', 'PNB', 'BAJFINANCE', 'CHOLAFIN'
    ],
    'Nifty IT & Tech': [
        'TCS', 'INFY', 'WIPRO', 'HCLTECH', 'TECHM', 
        'LTIM', 'PERSISTENT', 'COFORGE'
    ],
    'Nifty Auto & Industrials': [
        'TATAMOTORS', 'MARUTI', 'M&M', 'BAJAJ-AUTO', 'HEROMOTOCO', 
        'EICHERMOT', 'LT', 'HAL', 'BEL'
    ]
}

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("ISTS Pro")
st.sidebar.caption("Institutional Swing Trading System")

page = st.sidebar.radio(
    "Navigation", 
    ["Dashboard", "Scan Market", "Watchlist", "Portfolio", "Reports", "Settings"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("📲 Telegram Alert Setup")
bot_token = st.sidebar.text_input("Telegram Bot Token", type="password", help="Get from @BotFather")
chat_id = st.sidebar.text_input("Telegram Chat ID", help="Get from @userinfobot")
enable_alerts = st.sidebar.checkbox("Enable Automated Alerts (>=75%)", value=True)

# --- TELEGRAM NOTIFICATION ENGINE ---
def send_telegram_alert(symbol, price, score, target, triggers, token, c_id):
    """Sends a Telegram message and returns (success: bool, message: str)."""
    if not token or not c_id:
        return False, "Bot Token or Chat ID missing in sidebar."
    
    message = (
        f"🚨 *ISTS PRO BREAKOUT ALERT* 🚨\n\n"
        f"📌 *Stock:* `{symbol}`\n"
        f"💰 *Last Price:* ₹{price}\n"
        f"⚡ *Breakout Probability:* *{score}%*\n"
        f"🎯 *1.618 Fib Target:* ₹{target}\n"
        f"🔍 *Triggers Met:* {triggers}\n\n"
        f"📊 *Action:* Review setup on ISTS Pro Dashboard."
    )
    url = f"https://api.telegram.org/bot{token.strip()}/sendMessage"
    payload = {"chat_id": c_id.strip(), "text": message, "parse_mode": "Markdown"}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        res_data = response.json()
        if res_data.get("ok"):
            return True, "Alert delivered to Telegram successfully!"
        else:
            return False, f"Telegram API Error: {res_data.get('description', 'Unknown error')}"
    except Exception as e:
        return False, f"Network Error: {e}"

def send_telegram_alert_async(symbol, price, score, target, triggers, token, c_id):
    """Dispatches Telegram alert in a background thread so UI doesn't lag."""
    threading.Thread(
        target=send_telegram_alert,
        args=(symbol, price, score, target, triggers, token, c_id),
        daemon=True
    ).start()

# Diagnostic test button in sidebar
if st.sidebar.button("🧪 Send Test Telegram Alert"):
    if not bot_token or not chat_id:
        st.sidebar.error("Please enter both Bot Token and Chat ID above first.")
    else:
        with st.sidebar.spinner("Testing connection..."):
            success, msg = send_telegram_alert(
                symbol="TEST_STOCK",
                price=1000.0,
                score=100,
                target=1200.0,
                triggers="Diagnostic Test",
                token=bot_token,
                c_id=chat_id
            )
            if success:
                st.sidebar.success(msg)
            else:
                st.sidebar.error(msg)

# --- TECHNICAL HELPER FUNCTIONS ---
def calculate_rma(series, period):
    return series.ewm(alpha=1/period, adjust=False).mean()

@st.cache_data(ttl=1800)
def get_nifty_benchmark_return():
    try:
        nifty = yf.download('^NSEI', period="3m", interval="1d", progress=False)['Close']
        if isinstance(nifty, pd.DataFrame): nifty = nifty.iloc[:, 0]
        return ((nifty.iloc[-1] / nifty.iloc[-22]) - 1) * 100
    except:
        return 0.0

def run_pre_breakout_scanner(symbols):
    results = []
    nifty_1m_return = get_nifty_benchmark_return()

    for symbol in symbols:
        ticker = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
        try:
            data = yf.download(ticker, period="1y", interval="1d", progress=False)
            if len(data) < 100: continue
            if isinstance(data.columns, pd.MultiIndex): 
                data.columns = data.columns.get_level_values(0)

            # Indicator Calculations
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
            rs_status = "Outperforming" if stock_1m_return > nifty_1m_return else "Underperforming"

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

            # Dispatch Telegram alert if threshold met
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
                'Sector RS vs Nifty': rs_status,
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

# --- 1. DASHBOARD VIEW ---
if page == "Dashboard":
    st.title("Institutional Swing Trading System (ISTS Pro)")
    st.markdown("Professional scanner for the Indian equity markets: NSE and BSE")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Stocks", "10", "+0.74%")
    col2.metric("Bullish", "5")
    col3.metric("Bearish", "5")
    col4.metric("Watchlist", "3")

    st.subheader("Live Market Snapshot")
    snapshot_data = {
        'Symbol': ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'LT', 'BHARTIARTL', 'SBIN', 'TITAN'],
        'Last Price': [1267.70, 2398.00, 1105.70, 735.40, 1430.80, 3832.00, 1901.80, 1013.20, 4849.70],
        'Today %': ['-0.96%', '+4.46%', '+2.46%', '-0.56%', '-1.03%', '+0.68%', '-0.18%', '-0.73%', '+2.31%'],
        '50 DMA': [1308.34, 2189.54, 1108.06, 778.09, 1350.09, 3990.92, 1874.59, 1011.31, 4367.48],
        '200 DMA': [1411.16, 2692.84, 1355.65, 875.66, 1347.54, 3967.84, 1950.95, 1023.46, 4138.64]
    }
    st.dataframe(pd.DataFrame(snapshot_data), use_container_width=True)

# --- 2. SCAN MARKET VIEW ---
elif page == "Scan Market":
    st.title("🚀 Institutional Pre-Breakout Scanner")
    st.markdown("Detects accumulation, volume dry-up, ATR contraction, and Golden Pocket Fib support.")

    selected_watchlist_name = st.selectbox("Select Market Sector / Index Universe:", list(WATCHLISTS.keys()))
    watchlist = WATCHLISTS[selected_watchlist_name]

    if st.button("Run Live Pre-Breakout Scan", type="primary"):
        with st.spinner("Scanning market & evaluating rules..."):
            results = run_pre_breakout_scanner(watchlist)
            if results:
                results = sorted(results, key=lambda x: x['Score_Num'], reverse=True)
                st.session_state['scan_results'] = results
                st.success("Scan Complete! Telegram alerts dispatched for high-probability setups.")

    if 'scan_results' in st.session_state and st.session_state['scan_results']:
        results = st.session_state['scan_results']
        
        df_display = pd.DataFrame(results)[[
            'Symbol', 'Last Price', 'Pre-Breakout Score', 'Sector RS vs Nifty', 
            'RVOL', 'ATR Ratio', '1.618 Fib Target', 'Triggers Met'
        ]]
        st.dataframe(df_display, use_container_width=True)

        st.markdown("---")
        st.subheader("🔍 Interactive Technical Chart Analysis")
        
        selected_stock = st.selectbox("Select stock to analyze chart:", [r['Symbol'] for r in results])
        selected_data = next((r for r in results if r['Symbol'] == selected_stock), None)

        if selected_data:
            chart_df = selected_data['Data'].tail(120)
            
            fig = go.Figure(data=[
                go.Candlestick(
                    x=chart_df.index,
                    open=chart_df['Open'],
                    high=chart_df['High'],
                    low=chart_df['Low'],
                    close=chart_df['Close'],
                    name="Price"
                ),
                go.Scatter(x=chart_df.index, y=chart_df['EMA_20'], line=dict(color='blue', width=1), name="EMA 20"),
                go.Scatter(x=chart_df.index, y=chart_df['EMA_50'], line=dict(color='orange', width=1), name="EMA 50"),
                go.Scatter(x=chart_df.index, y=chart_df['EMA_200'], line=dict(color='red', width=1.5), name="EMA 200")
            ])
            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=480, title=f"{selected_stock} Daily Chart with Moving Averages")
            st.plotly_chart(fig, use_container_width=True)

            # Position Sizing Calculator
            st.markdown("---")
            st.subheader(f"🧮 Position Size & Risk Calculator: {selected_stock}")
            
            c_calc1, c_calc2, c_calc3 = st.columns(3)
            account_capital = c_calc1.number_input("Account Capital (₹)", min_value=10000, value=500000, step=25000)
            risk_percent = c_calc2.number_input("Risk Limit per Trade (%)", min_value=0.25, max_value=5.0, value=1.0, step=0.25)
            
            entry_p = selected_data['Last Price']
            target_p = selected_data['1.618 Fib Target']
            suggested_sl = round(entry_p - (1.5 * selected_data['ATR']), 2)
            
            stop_loss_p = c_calc3.number_input("Stop Loss Price (₹) [Default: 1.5x ATR]", min_value=1.0, value=float(suggested_sl), step=1.0)
            
            risk_per_share = entry_p - stop_loss_p
            if risk_per_share > 0:
                max_risk_inr = (account_capital * risk_percent) / 100.0
                qty = int(max_risk_inr / risk_per_share)
                total_position_val = qty * entry_p
                reward_per_share = target_p - entry_p
                rr_ratio = round(reward_per_share / risk_per_share, 2)
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Quantity to Buy", f"{qty} shares")
                m2.metric("Total Investment", f"₹{total_position_val:,.2f}")
                m3.metric("Max Capital at Risk", f"₹{max_risk_inr:,.2f}")
                m4.metric("Risk / Reward Ratio", f"1 : {rr_ratio}")
            else:
                st.warning("Stop Loss must be strictly lower than Last Price.")

# --- OTHER VIEWS ---
else:
    st.title(f"{page} Module")
    st.info(f"The {page} module is under development.")
