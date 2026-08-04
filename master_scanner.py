def run():
    print("🚀 Starting Automated Master Quant Scanner...")
    sess_title, sess_type = get_session_info()
    print(f"🕒 Timeframe Registered: {sess_title}")
    
    if sess_type == "Intraday":
        print("📈 Fetching Index Options for Intraday (NIFTY & BANKNIFTY)...")
        df_index = get_index_options_ideas()
    else:
        print("⏭️ Skipping Index Options for BTST to avoid overnight theta/gap risk...")
        df_index = pd.DataFrame()  # STRICTLY EMPTY FOR BTST
    
    fno_list = get_fno_symbols()
    tickers = get_all_nse_tickers()
    
    print(f"📥 Downloading live market data for {len(tickers)} stocks... (Please wait ~1 minute)")
    data = yf.download(tickers, period="3mo", interval="1d", progress=False, threads=True)
    if data.empty: 
        print("❌ CRITICAL ERROR: Could not fetch stock data from Yahoo Finance.")
        return
    
    print("✅ Data Downloaded Successfully! Initiating Matrix Vectorization Math...")
    
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

    valid_setups = []
    
    print("🔍 Scanning matrix against strict Momentum & Options Criteria...")

    for ticker in closes.columns:
        try:
            close_p = float(last_close[ticker])
            high_p = float(last_high[ticker])
            low_p = float(last_low[ticker])
            vol_today = float(last_vol[ticker])
            
            if pd.isna(close_p) or close_p <= 0 or high_p == low_p or vol_today < 1000: continue
            
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
            if symbol in fno_list:
                df_h, df_l, df_c = highs[ticker].dropna(), lows[ticker].dropna(), closes[ticker].dropna()
                opt, prem, pt1, pt2, pt3 = generate_quant_option(close_p, t1, t2, t3, df_h, df_l, df_c)
            else:
                opt, prem, pt1, pt2, pt3 = "N/A (Cash)", "-", "-", "-", "-"
            
            record = {'Stock': symbol, 'Horizon': hor, 'Entry': round(close_p, 2), 'RSI': round(rsi_val,1), 'EqSL': round(close_p-1.5*atr,1), 'EqT1': t1, 'EqT2': t2, 'EqT3': t3, 'EqT4': t4, 'EqT5': t5, 'Opt': opt, 'Prem': prem, 'PT1': pt1, 'PT2': pt2, 'PT3': pt3, 'Score': base_score}

            if passes_ema and base_score >= 2:
                valid_setups.append(record)
        except: continue

    print(f"🎯 Total Valid Breakout Setups Found: {len(valid_setups)}")
    
    df_all = pd.DataFrame(valid_setups).drop_duplicates(subset=['Stock']).sort_values(by=['Score', 'RSI'], ascending=[False, False]) if valid_setups else pd.DataFrame()

    df_intra = df_all[df_all['Horizon'] == 'Intraday'].head(20) if not df_all.empty else pd.DataFrame()
    df_btst = df_all[df_all['Horizon'] == 'BTST'].head(20) if not df_all.empty else pd.DataFrame()
    df_swing = df_all[df_all['Horizon'] == 'Swing'].head(20) if not df_all.empty else pd.DataFrame()

    print("💾 Saving Markdown Files for GitHub Repository...")
    if sess_type == "Intraday":
        generate_tabular_markdown(df_intra, df_index, f"⚡ Intraday Report — {sess_title}", "intraday_report.md", include_index=True)
        generate_tabular_markdown(df_swing, pd.DataFrame(), f"📈 Swing Trade Report — {sess_title}", "swing_report.md", include_index=False)
        open("btst_report.md", "w").close() 
    else:
        # STRICTLY PASSING EMPTY DATAFRAME FOR df_index AND False FOR include_index
        generate_tabular_markdown(df_btst, pd.DataFrame(), f"🌙 BTST Carry-Forward Report — {sess_title}", "btst_report.md", include_index=False)
        generate_tabular_markdown(df_swing, pd.DataFrame(), f"📈 Swing Trade Report — {sess_title}", "swing_report.md", include_index=False)
        open("intraday_report.md", "w").close() 

    print("📱 Generating specialized mobile text cards for Telegram Bot...")
    if sess_type == "Intraday":
        generate_telegram_cards(df_intra, df_index, f"⚡ Intraday Report — {sess_title}", "intraday_tg.txt", include_index=True)
        generate_telegram_cards(df_swing, pd.DataFrame(), f"📈 Swing Trade Report — {sess_title}", "swing_tg.txt", include_index=False)
        open("btst_tg.txt", "w").close()
    else:
        generate_telegram_cards(df_btst, pd.DataFrame(), f"🌙 BTST Carry-Forward Report — {sess_title}", "btst_tg.txt", include_index=False)
        generate_telegram_cards(df_swing, pd.DataFrame(), f"📈 Swing Trade Report — {sess_title}", "swing_tg.txt", include_index=False)
        open("intraday_tg.txt", "w").close()

    print("🎉 Master Scanner Cycle Complete! Passing data to Telegram Push script.")
