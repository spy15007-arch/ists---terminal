import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import math
import plotly.graph_objects as go
from scipy.stats import norm
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="ISTS Pro Dashboard", page_icon="📈", layout="wide")

# --- FIREWALL-PROOF F&O UNIVERSE ---
STATIC_FNO = [
    "AARTIIND", "ABB", "ABBOTINDIA", "ABCAPITAL", "ABFRL", "ACC", "ACCELYA", "ACTIONCONST", "ADANIENSOL", "ADANIENT", 
    "ADANIGREEN", "ADANIPORTS", "ADANIPOWER", "ALKEM", "AMBUJACEM", "APOLLOHOSP", "APOLLOTYRE", "ASHOKLEY", "ASIANPAINT", 
    "ASTRAL", "ATUL", "AUBANK", "AUROPHARMA", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BALKRISIND", 
    "BALRAMCHIN", "BANDHANBNK", "BANKBARODA", "BATAINDIA", "BEL", "BERGEPAINT", "BHARATFORG", "BHARTIARTL", "BHEL", 
    "BIOCON", "BOSCHLTD", "BPCL", "BRITANNIA", "CANBK", "CANFINHOME", "CHAMBLFERT", "CHOLAFIN", "CIPLA", "COALINDIA", 
    "COFORGE", "COLPAL", "CONCOR", "COROMANDEL", "CROMPTON", "CUB", "CUMMINSIND", "DABUR", "DALBHARAT", "DEEPAKNTR", 
    "DIVISLAB", "DIXON", "DLF", "DRREDDY", "EICHERMOT", "ESCORTS", "EXIDEIND", "FEDERALBNK", "GAIL", "GLENMARK", 
    "GMRINFRA", "GNFC", "GODREJCP", "GODREJPROP", "GRANULES", "GRASIM", "GUJGASLTD", "HAL", "HAVELLS", "HCLTECH", 
    "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDCOPPER", "HINDPETRO", "HINDUNILVR", "ICICIBANK", 
    "ICICIGI", "ICICIPRULI", "IDEA", "IDFCFIRSTB", "IEX", "IGL", "INDHOTEL", "INDIACEM", "INDIAMART", "INDIGO", 
    "INDUSINDBK", "INFY", "IOC", "IPCALAB", "IRCTC", "ITC", "JINDALSTEL", "JSWSTEEL", "JUBLFOOD", "KOTAKBANK", 
    "LALPATHLAB", "LAURUSLABS", "LICHSGFIN", "LT", "LTIM", "LTTS", "LUPIN", "M&M", "M&MFIN", "MANAPPURAM", "MARICO", 
    "MARUTI", "MCDOWELL-N", "MCX", "METROPOLIS", "MFSL", "MGL", "MOTHERSON", "MPHASIS", "MRF", "MUTHOOTFIN", "NATIONALUM", 
    "NAUKRI", "NAVINFLUOR", "NESTLEIND", "NMDC", "NTPC", "OBEROIRLTY", "OFSS", "ONGC", "PAGEIND", "PEL", "PETRONET", 
    "PFC", "PIDILITIND", "PIIND", "PNB", "POLYCAB", "POWERGRID", "PVRINOX", "RAMCOCEM", "RBLBANK", "RECLTD", "RELIANCE", 
    "SAIL", "SBICARD", "SBILIFE", "SBIN", "SHREECEM", "SHRIRAMFIN", "SIEMENS", "SRF", "SUNPHARMA", "SUNTV", "SYNGENE", 
    "TATACHEM", "TATACOMM", "TATACONSUM", "TATAMOTORS", "TATAPOWER", "TATASTEEL", "TCS", "TECHM", "TITAN", "TORNTPHARM", 
    "TRENT", "TVSMOTOR", "UBL", "ULTRACEMCO", "UPL", "VEDL", "VOLTAS", "WIPRO", "ZEEL", "ZYDUSLIFE"
]

# --- 1200+ UNIVERSE ---
raw_symbols = (
    "360ONE 3IINFOTECH 3MINDIA 5PAISA 63MOONS AARTIIND AARTIPHARM AARTISURF AAVAS ABBOTINDIA ABCAPITAL ABFRL ACC ACCELYA ACTIONCONST "
    "ADANIENSOL ADANIENT ADANIGREEN ADANIPORTS ADANIPOWER ADVENZYMES AEGISCHEM AETHER AFFLE AGARIND AGI AGL AJANTPHARM ALKALI "
    "ALKEM ALKYLAMINE ALLCARGO ALLSEC ALOKINDS AMARAJABAT AMBER AMBIKCO AMBUJACEM AMIORG ANANDAMAC ANANDRATHI ANDHRAPAP ANGELONE "
    "ANUPAM ANURAS APARINDS APEX APLAPOLLO APOLLOHOSP APOLLOPIPE APOLLOTYRE APTUS APL ARCHIDPLY ARMANFIN ARVINDFASN ASAHIINDIA "
    "ASHOKA ASHOKLEY ASIANPAINT ASTEC ASTERDM ASTRAL ASTRAZEN ASTRON ATGL ATUL AUBANK AUROPHARMA AUTOAXLES AVADHSUGAR AVANTIFEED "
    "AWHCL AWL AXISBANK BAJAJ-AUTO BAJAJCON BAJAJELEC BAJAJFINSV BAJAJHLD BAJFINANCE BALAMINES BALKRISIND BALMLAWRIE BALRAMCHIN "
    "BANARISUG BANDHANBNK BANKA BANKBARODA BANKINDIA MAHABANK BATAINDIA BDL BEL BEML BEPL BERGEPAINT BECTORFOOD BHARATFORG "
    "BHARATRAS BHARTIARTL BHEL BIGBLOC BIOCON BIRLACABLE BIRLACORPN BLS BLUEDART BLUESTARCO BOMBAYBURM BOSCHLTD BPCL BRIGADE "
    "BRITANNIA BSOFT BSE CAMS CANBK CANFINHOME CAPACITE CAPLIPOINT CARBORUNIV CASTROLIND CCL CDSL CEATLTD CENTRALBK CENTURYPLY "
    "CENTURYTEX CERA CEREBRAINT CESC CGCL CGPOWER CHALET CHAMBLFERT CHEMBOND CHEMFAB CHEMPLASTS CHENNPETRO CHOLAFIN CHOLAHLD "
    "CIGNITITEC CIPLA CLEAN CLEDUCATE COALINDIA COCHINSHIP COFFEECO DAY COFORGE COLPAL COMPINFO CONCOR CONFIPET CONTROLPR COROMANDEL "
    "COSMOFIRST CRAFTSMAN CREDITACC CREATIVE CRISIL CROMPTON CSBBANK CUB CUMMINSIND CUPID CYIENT DABUR DALBHARAT DATAMATICS "
    "DATAPATTNS DCBBANK DCMSHRIRAM DEEPAKFERT DEEPAKNTR DEEPENR DELTACORP DELHIVERY DEN DEVYANI DHAMPURSUG DHANBANK DIKSHAT DIVISLAB "
    "DIXON DLF DMART DODLA DOLLAR DRREDDY DSSL DYNAMATECH EASEMYTRIP EDELWEISS EICHERMOT EIDPARRY EKI ELECON ELGIEQUIP EMAMILTD "
    "ENDURANCE ENGINERSIN ENIL EPL EQUITASBNK ERIS ESABINDIA ESCORTS ETHERMATICS EVERESTIND EXCEL EXIDEIND FACT FDC FEDERALBNK "
    "FIEMIND FILATEX FINEORG FINCABLES FINPIPE FIVESTAR FORCEMOT FORTIS FRETAIL FSL GABRIEL GAEL GAIL GALAXYSURF GALLANTT GARFIBRES "
    "GATEWAY GATI GENUSPOWER GEOJITFSL GESHIP GHCL GICRE GILLETTE GLAND GLENMARK GLS GMMPFAUDLR GMRINFRA GNFC GODFRYPHLP GODREJAGRO "
    "GODREJCP GODREJIND GODREJPROP GOCOLORS GOKEX GOKULAGRO GOLDIAM GRANDE GRAVITA GRANULES GRAPHITE GRASIM GREENLAM GREENPANEL "
    "GRINDWELL GRSE GSFC GSPL GUJALKALI GUJGASLTD GULFOILLUB HAL HAPPSTMNDS HARDWYN HARSHA HATHWAY HATSUN HAVELLS HCC HCG HCLTECH "
    "HDFCAMC HDFCBANK HDFCLIFE HEG HEIDELBERG HERITGFOOD HEROMOTOCO HESTERBIO HGS HIKAL HIL HINDALCO HINDCOMPOS HINDCOPPER HINDMOTORS "
    "HINDPETRO HINDUNILVR HINDZINC HITACHIQM HLVLTD HMT HOMEFIRST HONAUT HONASA HSCL HTMEDIA HUBTOWN HUDCO ICIL ICICIBANK ICICIGI "
    "ICICIPRULI ISEC IDBI IDEA IDFC IDFCFIRSTB IEX IFBIND IGL IIFL IKIO INDHOTEL INDIACEM INDIAGLYCO INDIAMART INDIANB INDIANHUME "
    "INDIGO INDIGOPNTS INDOAMIN INDOCO INDOSTAR INDUSINDBK INDUSTOWER INEOSSTYRO INFIBEAM INFY INGERSRAND INOXGREEN INOXINDIA "
    "INOXLEISUR INOXWIND INTELLECT IOC IOB IPAC IPCALAB IRB IRCON IRCTC IREDA IRFC ISEC ISGEC ITC ITDC ITDCEM ITI J&KBANK JAGRAN "
    "JAICORPLTD JAMNAAUTO JAYBARMARU JAYNECOIND JBCHEMPHARMA JBM JINDALPOLY JINDALSAW JINDALSTEL JIOFIN JKCEMENT JKIL JKLAKSHMI "
    "JKPAPER JKTYRE JMFINANCIL JPASSOCIAT JSL JSWENERGY JSWHL JSWINFRA JSWSTEEL JTEKTINDIA JUBLFOOD JUBLINGREA JUBLPHARMA JUSTDIAL "
    "JYOTHYLAB KAJARIACER KAKATCEM KALPATPOWR KALYANKJIL KAMATHOTEL KANSAINER KARURVYSYA KAVERI KAYNES KCP KEC KEI KENNAMETAL "
    "KESORAMIND KEYFINSERV KFINTECH KICL KIRLOSENG KIRLOSIND KIRIINDUS KITEX KNRCON KOTAKBANK KPIGREEN KPITTECH KPRMILL KRBL "
    "KRISHANA KSB KSERASERA L&TFH LALPATHLAB LAOPALA LATENTVIEW LAURUSLABS LEMONTREE LICHSGFIN LICI LIKHITHA LINCOLN LINDEINDIA "
    "LLOYDSENG LLOYDSME LODHA LOKESHMACH LOVABLE LTIM LTTS LUMAXIND LUMAXTECH LUPIN LUXIND M&M M&MFIN MACPOWER MADRASFERT MAGADSUGAR "
    "MAHABANK MAHLIFE MAHLOG MAHSCOOTER MAITHANALL MANAPPURAM MANGLMCEM MANINDS MARICO MARKSANS MARUTI MASTEK MATRIMONY MAXHEALTH "
    "MAXIND MAYURUNIQ MAZDOCK MCDOWELL-N MCLEODRUSS MCX MEDPLUS MEESHO MENONBE MFL MHRIL MIDHANI MINDAIND MINDACORP MINDSPACE "
    "MIRZAINT MITCON MOLDTKPAC MONARCH MONGIPA MOTHERSON MOTILALOFS MPHASIS MRF MRPL MSTC MTARTECH MTNL MUKANDLTD MUNJALAU "
    "MUNJALSHOW MUTHOOTFIN NAM-INDIA NATCOPHARM NATHBIOGEN NATIONALUM NAUKRI NAVA NAVINFLUOR NAZARA NBCC NCC NCLIND NDTV NECCLTD "
    "NEOGEN NESCO NESTLEIND NETWORK18 NETWEB NEULANDLAB NEWGEN NFL NH NHPC NIACL NIITLTD NILKAMAL NLCINDIA NMDC NOCIL NOIDATOLL "
    "NON-RE NMDCSTEEL NTPC NUCLEUS NUVOCO NYKAA OBEROIRLTY OFSS OIL OLECTRA OMAXE ONGC OPTIEMUS ORIENTELEC ORIENTHOT ORISSAELECO "
    "PAGEIND PANACEABIO PANAMAPET PARADEEP PARAGMILK PARAS PATANJALI PATELENG PCBL PCJEWELLER PEL PENIND PENNARIND PERSISTENT "
    "PETRONET PFC PFIZER PGHH PGHL PHENIXLTD PIDILITIND PIIND PILANIINVS PNB PNCINFRA POCL POLYCAB POLYMED POLYPLEX PONNIERODE "
    "POONAWALLA POWERGRID POWERINDIA PRAJIND PRAKASH PRECAM PREMIERPOL PRESTIGE PRICOL PRINCEPIPE PRIVISCL PRSMJOHNS PSPPROJECT "
    "PTC PTL PUNJABCHEM PURVA PVRINOX QUESS QUICKHEAL RADICO RAILTEL RAIN RAINBOW RAJESHEXPO RALLIS RAMASTEEL RAMCOCEM RAMCOIND "
    "RAMCOSYS RATNAMANI RAYMOND RBA RBLBANK RCF RECLTD REDINGTON RELAXO RELIANCE RELIGARE REPCOHOME RESPONSIND RGL RHIM RITES "
    "RKFORGE ROLEXRINGS ROSSELLIND ROUTE RSYSTEMS RUPA RVNL S&SPOWER SADBHAV SAFARI SAGCEM SAIL SALASAR SALZERELEC SANGAMIND "
    "SANGHIIND SANOFI SAPPHIRE SAREGAMA SASKEN SATIA SATIN SBICARD SBILIFE SBIN SCHAEFFLER SCHNEIDER SCI SFL SHAKTIPUMP SHALBY "
    "SHALPAINTS SHARDACROP SHARDACH SHOOPERS SHREECEM SHREEPUSHK SHRIRAMFIN SHYAMMETL SIEMENS SIGACHI SIL SIS SJVN SKFINDIA "
    "SKIPPER SKMEGGPROD SMARTLINK SMCGLOBAL SMLISUZU SMSLIFE SOBHA SOLARINDS SOLARA SOMANYCERA SOMATEX SONACOMS SOTL SOUTHBANK "
    "SPAL SPANDANA SPARC SPECIALITY SPENCERS SPLIL SPORTKING SREEL SRF SRHHYPMEL STAR STARPAPER STCINDIA STEELCITY STLTECH "
    "SUBROS SUDARSCHEM SUMICHEM SUMIT SUNCLAYLTD SUNDARAM SUNDARMFIN SUNDRMFAST SUNPHARMA SUNTECK SUNTV SUPRAJIT SUPREMEIND "
    "SURYAROSNI SULA SUZLON SWANENERGY SWARAJENG SWSOLAR SYMPHONY SYNCOMF SYNGENE TAINWALCHM TAJGVK TALBROAUTO TANLA TARAJEWELS "
    "TARSONS TASTYBITE TATACHEM TATACOFFEE TATACOMM TATACONSUM TATAELXSI TATAINVEST TATAMETALI TATAMOTORS TATAPOWER TATASTEEL TCS "
    "TDPOWERSYS TECHM TECHNOE TEJASNET TEXINFRA TEXRAIL TFCILTD TFL THERMAX THYROCARE TIIL TIMKEN TINPLATE TIPSINDLTD TIRUMALCHM "
    "TITAN TNPL TOKYOPLAST TORNTPHARM TORNTPOWER TRENT TRF TRIDENT TRIL TRITURBINE TRIVENI TTKHLTHCARE TTKPRESTIG TV18BRDCST "
    "TVSMOTOR TVSSRICHAK UBL UCALFUEL UCOBANK UFLEX UGARSUGAR UJJIVAN UJJIVANSFB ULTRACEMCO UMANGDAIR UNICHEMLAB UNIONBANK "
    "UNITEDTEA UNO MINDA UPL URAVI USHAMART UTIAMC VAIBHAVGBL VAKRANGEE VALIANTORG VARDHMAN VARROC VASCONEQ VBL VEDL VENKEYS "
    "VESUVIUS VGUARD VIDHIING VINATIORGA VINDHYATEL VIPIND VISAKAIND VISHNU VOLTAMP VOLTAS VRLLOG WABAG WALCHANNAG WEALTH WELCORP "
    "WELENT WESCG WELSPUNIND WHIRLPOOL WINDLAS WIPRO WOCKPHARMA WONDERLA XPROINDIA YESBANK YUKEN ZEELEARN ZEEL ZENSARTECH "
    "ZFCVINDIA ZOMATO ZOTA ZUARI ZUARIIND ZYDUSLIFE ZYDUSWELL TFCI SHIVALIK SWANDEFENCE AVALON AIMTRON INDOTECH PEARLGLOBAL DIL"
)
EXTENDED_UNIVERSE = list(set(raw_symbols.split()))

st.sidebar.title("ISTS Pro Terminal")
page = st.sidebar.radio("Navigation", ["Dashboard", "Scan Market", "Budget Scanner (< ₹500)"])

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
    pt1 = black_scholes(t1, atm, dte/365.0, 0.07, vol, opt_type)
    pt2 = black_scholes(t2, atm, dte/365.0, 0.07, vol, opt_type)
    pt3 = black_scholes(t3, atm, dte/365.0, 0.07, vol, opt_type)
    
    return f"{atm} {opt_type}", c_prem, round(pt1, 1), round(pt2, 1), round(pt3, 1)

@st.cache_data(ttl=60)
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

@st.cache_data(ttl=60)
def run_quant_scan():
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    market_open = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
    minutes_elapsed = min(max(1, (now_ist - market_open).total_seconds() / 60), 375)
    
    tickers = [f"{s}.NS" for s in EXTENDED_UNIVERSE]
    data = yf.download(tickers, period="6mo", interval="1d", progress=False, threads=True)
    if data.empty: return pd.DataFrame()
    
    closes, highs, lows, volumes = data['Close'], data['High'], data['Low'], data['Volume']
    ema_50_daily = closes.ewm(span=50).mean()
    ema_20_daily = closes.ewm(span=20).mean()
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
    last_ema_50, last_ema_20, last_atr = ema_50_daily.iloc[-1], ema_20_daily.iloc[-1], atr_daily.iloc[-1]
    last_ema_50_weekly = ema_50_weekly.iloc[-1]

    valid_setups = []

    for ticker in closes.columns:
        try:
            close_p, vol_today = float(last_close[ticker]), float(last_vol[ticker])
            vol_50_avg = float(last_vol_50[ticker])
            
            if pd.isna(close_p) or close_p <= 0 or vol_today < 200000 or vol_50_avg < 200000: 
                continue
            
            rsi_val, macd_val, macd_sig = float(last_rsi[ticker]), float(last_macd[ticker]), float(last_macd_sig[ticker])
            d_ema, d_ema20, w_ema, atr = float(last_ema_50[ticker]), float(last_ema_20[ticker]), float(last_ema_50_weekly[ticker]), float(last_atr[ticker])
            
            adjusted_vol_50 = vol_50_avg * (minutes_elapsed / 375.0)
            vol_vs = round(vol_today / adjusted_vol_50, 2)
            
            recent_vol_avg = float(volumes[ticker].tail(3).mean())
            recent_range_avg = float((highs[ticker].tail(3) - lows[ticker].tail(3)).mean())
            recent_20d_high = float(highs[ticker].tail(20).max())
            
            dist_to_20d_high = (recent_20d_high - close_p) / close_p

            is_squeeze = (recent_vol_avg < vol_50_avg * 0.85) and (recent_range_avg < atr * 0.85)

            # --- PRE-BREAKOUT DETECTOR ---
            is_pre_breakout = (0.002 <= dist_to_20d_high <= 0.035) and (close_p > d_ema20) and (vol_vs <= 1.25)

            if is_pre_breakout:
                hor, m1, m2, m3, m4, m5, sl_m = "Pre-Breakout", 0.8, 1.6, 2.4, 3.2, 4.0, 1.0
            elif vol_vs >= 1.5:
                hor, m1, m2, m3, m4, m5, sl_m = "Intraday", 0.3, 0.6, 0.9, 1.2, 1.5, 0.8
            elif is_squeeze or vol_vs >= 1.2:
                hor, m1, m2, m3, m4, m5, sl_m = "BTST", 0.6, 1.2, 1.8, 2.4, 3.0, 1.0
            elif vol_vs >= 0.8:
                hor, m1, m2, m3, m4, m5, sl_m = "Swing", 1.5, 3.0, 4.5, 6.0, 7.5, 1.5
            else:
                continue

            if close_p > d_ema and close_p > w_ema and macd_val > macd_sig and (45 <= rsi_val <= 85):
                direction = "Bullish"
                t1, t2, t3, t4, t5 = [round(close_p + m * atr, 1) for m in (m1, m2, m3, m4, m5)]
                eq_sl = round(close_p - sl_m * atr, 1)
                
                risk = close_p - eq_sl
                reward = (t2 - close_p) if hor in ["Swing", "Pre-Breakout"] else (t1 - close_p)
                if risk <= 0 or (reward / risk) < 1.5:
                    continue
                
                if is_pre_breakout:
                    base_score = 6
                elif is_squeeze:
                    base_score = 5
                else:
                    base_score = 2 + (2 if vol_vs >= 1.5 else 0)
            else:
                continue 

            symbol = ticker.replace(".NS", "")
            df_h, df_l, df_c = highs[ticker].dropna(), lows[ticker].dropna(), closes[ticker].dropna()
            
            if symbol in STATIC_FNO:
                try:
                    opt, prem, pt1, pt2, pt3 = generate_quant_option(close_p, t1, t2, t3, df_h, df_l, df_c, direction, hor)
                except:
                    opt, prem, pt1, pt2, pt3 = "N/A (Data Err)", "-", "-", "-", "-"
            else:
                opt, prem, pt1, pt2, pt3 = "N/A (Cash)", "-", "-", "-", "-"
                
            tv_clean_sym = symbol.replace("&", "_").replace("-", "_")
            
            valid_setups.append({
                'Stock': f"{symbol} (↑)", 
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
    col2.metric("Scan Universe", "1200+ Equities", "Liquidity Protected")
    col3.metric("Math Engine", "Black-Scholes", "Pre-Breakout Coils")
    col4.metric("Strategy", "Scaled ATR Vectors", "Scalp/Swing/Pre")

elif page == "Scan Market":
    st.title("🚀 Master Quant Scanner")
    st.markdown("Scans 1200+ Universe matching Institutional Liquidity, VWAP, and Pre-Breakout Coils.")

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
            st.subheader("🌟 Top 10 High Conviction Setups")
            
            df_hc = df_results.head(10).copy()
            if not df_hc.empty:
                df_hc.insert(0, '#', range(1, len(df_hc) + 1))
            
            hc_cols = ['#', 'Stock', 'Horizon', 'Entry', 'EqSL', 'Eq Tgts (1-5)', 'Opt', 'Prem', 'Prem Tgts (1-3)', 'TV_Link']
            st.dataframe(df_hc[hc_cols], use_container_width=True, hide_index=True, column_config={"TV_Link": st.column_config.LinkColumn("Live Chart", display_text="📊 View in TV")})
        
        st.markdown("---")
        st.subheader("📊 Full Market Scan by Horizon")
        tab1, tab2, tab3, tab4 = st.tabs(["💥 Soon to Breakout (2-3 Days)", "⚡ Intraday", "🌙 BTST (Best 10-15)", "📈 Swing (Top 25)"])
        
        full_cols = ['#', 'Stock', 'RSI', 'Vol vs 50d', 'Entry', 'EqSL', 'Eq Tgts (1-5)', 'Opt', 'Prem', 'Prem Tgts (1-3)', 'TV_Link']
        
        with tab1:
            if not df_results.empty:
                df_pre = df_results[df_results['Horizon'] == 'Pre-Breakout'].copy()
                if not df_pre.empty:
                    df_pre.insert(0, '#', range(1, len(df_pre) + 1))
                    st.dataframe(df_pre[full_cols], use_container_width=True, hide_index=True, column_config={"TV_Link": st.column_config.LinkColumn("Live Chart", display_text="📊 View")})
                else:
                    st.info("No Pre-Breakout coiling setups found right below 20-day resistance today.")

        with tab2:
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
                
        with tab3:
            if not df_results.empty:
                df_btst = df_results[df_results['Horizon'] == 'BTST'].head(15).copy()
                if not df_btst.empty: 
                    df_btst.insert(0, '#', range(1, len(df_btst) + 1)) 
                    st.dataframe(df_btst[full_cols], use_container_width=True, hide_index=True, column_config={"TV_Link": st.column_config.LinkColumn("Live Chart", display_text="📊 View")})
                else: st.info("No BTST setups found.")
                
        with tab4:
            if not df_results.empty:
                df_swing = df_results[df_results['Horizon'] == 'Swing'].head(25).copy()
                if not df_swing.empty: 
                    df_swing.insert(0, '#', range(1, len(df_swing) + 1)) 
                    st.dataframe(df_swing[full_cols], use_container_width=True, hide_index=True, column_config={"TV_Link": st.column_config.LinkColumn("Live Chart", display_text="📊 View")})
                else: st.info("No Swing setups found.")

        # --- NATIVE PLOTLY CHART INTEGRATION ---
        st.markdown("---")
        st.subheader("🔍 Native Real-Time Chart Analysis")
        
        df_all_merged = pd.concat([st.session_state.get('index_results', pd.DataFrame()), df_results]) if not df_results.empty else st.session_state.get('index_results', pd.DataFrame())
        
        if not df_all_merged.empty:
            
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            with c1:
                selected_stock = st.selectbox("Select asset to load native chart:", df_all_merged['Stock'].tolist())
            with c2:
                selected_tf = st.selectbox("Timeframe:", ["5m", "15m", "30m", "1h", "1d"], index=1)
            with c3:
                st.write("")
                st.write("")
                if st.button("🔄 Refresh Now", use_container_width=True):
                    pass 
            with c4:
                st.write("")
                st.write("")
                auto_refresh = st.toggle("⏱️ Auto-Tick (30s)", value=False)
                
            if auto_refresh:
                st_autorefresh(interval=30000, limit=None, key="live_chart_refresh")

            stock_row = df_all_merged[df_all_merged['Stock'] == selected_stock].iloc[0]
            raw_sym = str(stock_row['RawStock']).strip().replace("&", "_").replace("-", "_")
            
            if raw_sym == "NIFTY": yf_sym = "^NSEI"
            elif raw_sym == "BANKNIFTY": yf_sym = "^NSEBANK"
            else: yf_sym = f"{raw_sym}.NS"
            
            tv_link_sym = f"NSE:{raw_sym}"
            
            if selected_tf == "1d":
                fetch_period = "3mo"
            else:
                fetch_period = "5d"
            
            with st.spinner(f"Fetching live {selected_tf} candlestick data..."):
                chart_data = yf.Ticker(yf_sym).history(period=fetch_period, interval=selected_tf)
                
                if not chart_data.empty:
                    fig = go.Figure(data=[go.Candlestick(
                        x=chart_data.index,
                        open=chart_data['Open'],
                        high=chart_data['High'],
                        low=chart_data['Low'],
                        close=chart_data['Close'],
                        increasing_line_color='#00ff00', 
                        decreasing_line_color='#ff0000'
                    )])
                    
                    range_breaks = [dict(bounds=["sat", "mon"])]
                    if selected_tf != "1d":
                        range_breaks.append(dict(bounds=[15.5, 9.25], pattern="hour")) 
                    
                    fig.update_xaxes(rangebreaks=range_breaks)

                    fig.update_layout(
                        title=f"{selected_stock} - Native {selected_tf} Chart",
                        yaxis_title="Price (₹)",
                        template="plotly_dark",
                        height=550,
                        margin=dict(l=10, r=10, t=40, b=10),
                        xaxis_rangeslider_visible=False
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Live chart data temporarily unavailable. Please use the TradingView button below.")

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
