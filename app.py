import requests

# --- DYNAMIC NIFTY 500 FETCH ENGINE ---
@st.cache_data(ttl=14400) # Caches universe list for 4 hours
def get_nifty500_tickers():
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        df = pd.read_csv(pd.compat.StringIO(response.text))
        return [f"{symbol}.NS" for symbol in df['Symbol'].tolist()]
    except Exception:
        # High-liquidity fallback list if NSE blocks requests
        fallback = [
            'TVSMOTOR', 'COFORGE', 'HAL', 'BEL', 'DIXON', 'TRENT', 'MCX', 'PERSISTENT',
            'BHARTIARTL', 'RELIANCE', 'SBIN', 'ICICIBANK', 'HDFCBANK', 'TATAMOTORS',
            'INFY', 'TCS', 'LT', 'MARUTI', 'AXISBANK', 'M&M', 'SUNPHARMA', 'TITAN',
            'KALYANKJIL', 'SAREGAMA', 'JYOTICNC', 'FEDERALBNK', 'IEX', 'BHARTIHEXA',
            'LALPATHLAB', 'DIVISLAB', 'PARADEEP', 'PCBL', 'FSL', 'SONATSOFTW', 'RADICO'
        ]
        return [f"{s}.NS" for s in fallback]

@st.cache_data(ttl=1800)
def get_nifty_benchmark_return():
    try:
        nifty = yf.download('^NSEI', period="6m", interval="1d", progress=False)['Close']
        if isinstance(nifty, pd.DataFrame): nifty = nifty.iloc[:, 0]
        return ((nifty.iloc[-1] / nifty.iloc[-63]) - 1) * 100
    except Exception:
        return 0.0

# --- DYNAMIC 500-STOCK SCANNER ---
def run_btst_breakout_scan():
    tickers = get_nifty500_tickers()
    results = []
    nifty_3m_return = get_nifty_benchmark_return()

    # Bulk download all tickers at once for maximum speed
    data = yf.download(tickers, period="1y", interval="1d", group_by='ticker', progress=False)

    for ticker in tickers:
        symbol = ticker.replace(".NS", "")
        try:
            df = data[ticker].dropna() if len(tickers) > 1 else data.dropna()
            if len(df) < 200: continue

            close_p = df['Close'].iloc[-1]
            high_p = df['High'].iloc[-1]
            low_p = df['Low'].iloc[-1]
            vol_today = df['Volume'].iloc[-1]

            # Stage-2 Uptrend Filter (Price > EMA 50 > EMA 200)
            ema_50 = df['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
            ema_200 = df['Close'].ewm(span=200, adjust=False).mean().iloc[-1]

            if not (close_p > ema_50 and ema_50 > ema_200):
                continue

            # Relative Strength Filter vs Nifty 50
            stock_3m_return = ((close_p / df['Close'].iloc[-63]) - 1) * 100
            rs_edge_pct = round(stock_3m_return - nifty_3m_return, 1)

            if rs_edge_pct < 0:
                continue

            close_pos = round(((close_p - low_p) / (high_p - low_p)) * 100, 1) if high_p != low_p else 50.0
            vol_50d_avg = df['Volume'].rolling(50).mean().iloc[-1]
            vol_vs_50d = round(vol_today / vol_50d_avg, 2) if vol_50d_avg > 0 else 1.0

            high_50d = df['High'].rolling(50).max().iloc[-1]
            low_50d = df['Low'].rolling(50).min().iloc[-1]
            base_range_pct = round(((high_50d - low_50d) / low_50d) * 100, 1)
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

            # ATR for Position Sizing
            high_low = df['High'] - df['Low']
            high_close = np.abs(df['High'] - df['Close'].shift())
            low_close = np.abs(df['Low'] - df['Close'].shift())
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = tr.ewm(alpha=1/14, adjust=False).mean().iloc[-1]

            opt_contract, opt_target, opt_sl = generate_option_idea(symbol, close_p, score)

            if enable_alerts and score >= 8:
                send_telegram_alert_async(symbol, round(close_p, 2), score, composite, opt_contract, bot_token, chat_id)

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
                'Option Contract': opt_contract,
                'Spot Target': opt_target,
                'Spot SL': opt_sl,
                'ATR': round(atr, 2),
                'Data': df
            })
        except Exception:
            continue

    df_results = pd.DataFrame(results)
    if not df_results.empty:
        # Sort and return ONLY THE TOP 20 BEST setups
        df_results = df_results.sort_values(by=['Score /10', 'Composite /100'], ascending=[False, False]).head(20)
        df_results['Rank'] = range(1, len(df_results) + 1)
    return df_results
