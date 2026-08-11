import os
import requests
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import math
from scipy.stats import norm
import warnings
warnings.filterwarnings('ignore')

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
BASE_CAPITAL_PER_TRADE = 50000  
HIGH_CONVICTION_MULTIPLIER = 2  

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"})
    except Exception: pass

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

def get_session_info():
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    hour, minute = now_ist.hour, now_ist.minute
    is_github_action = os.environ.get("GITHUB_ACTIONS") == "true"
    is_manual_dispatch = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
    is_manual = (not is_github_action) or is_manual_dispatch

    if is_manual: return now_ist.strftime("%d %b %Y | %I:%M %p (Manual Override)"), "Manual"
    elif hour < 14 or (hour == 14 and minute < 30): return now_ist.strftime("%d %b %Y | %I:%M %p (Intraday)"), "Intraday"
    else: return now_ist.strftime("%d %b %Y | %I:%M %p (BTST/Afternoon)"), "Afternoon"

def black_scholes(S, K, T, r, sigma, opt_type="CE"):
    if T <= 0 or sigma == 0: return max(0, S - K) if opt_type == "CE" else max(0, K - S)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if opt_type == "CE": return round(S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2), 2)
    else: return round(K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1), 2)

def get_index_dte(ticker):
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    today = now_ist.weekday() 
    target_day = 2 if "BANK" in ticker else 3 
    days_to_expiry = target_day - today
    if days_to_expiry < 0: days_to_expiry += 7
    if days_to_expiry == 0 and now_ist.hour >= 15: days_to_expiry = 7
    return max(0.5, days_to_expiry)

def calculate_dynamic_targets(close_p, atr, df_h, df_l, direction="Bullish", is_squeeze=False):
    recent_high = float(df_h.tail(20).max())
    recent_low = float(df_l.tail(20).min())
    diff = max(2.0, recent_high - recent_low)
    
    if direction == "Bullish":
        f_t1 = close_p + diff * 0.618
        f_t2 = close_p + diff * 1.000
        f_t3 = close_p + diff * 1.618
        f_t4 = close_p + diff * 2.618
        f_t5 = close_p + diff * 4.236
        
        a_t1 = close_p + 1.5 * atr
        a_t2 = close_p + 3.0 * atr
        a_t3 = close_p + 5.0 * atr
        a_t4 = close_p + 7.5 * atr
        a_t5 = close_p + 10.0 * atr
    else:
        f_t1 = close_p - diff * 0.618
        f_t2 = close_p - diff * 1.000
        f_t3 = close_p - diff * 1.618
        f_t4 = close_p - diff * 2.618
        f_t5 = close_p - diff * 4.236
        
        a_t1 = close_p - 1.5 * atr
        a_t2 = close_p - 3.0 * atr
        a_t3 = close_p - 5.0 * atr
        a_t4 = close_p - 7.5 * atr
        a_t5 = close_p - 10.0 * atr

    return (
        round((a_t1 + f_t1) / 2, 1), 
        round((a_t2 + f_t2) / 2, 1), 
        round((a_t3 + f_t3) / 2, 1), 
        round((a_t4 + f_t4) / 2, 1), 
        round((a_t5 + f_t5) / 2, 1)
    )

def generate_quant_option(symbol, price, t1, t2, t3, t4, t5, eq_sl, df_h, df_l, df_c, direction="Bullish"):
    if "^NSE" in symbol or symbol in ["NIFTY", "BANKNIFTY"]:
        dte = get_index_dte(symbol)
        step = 100 if "BANK" in symbol else 50
        vol = 0.14 
    else:
        dte = 15 
        step = 100 if price > 5000 else (50 if price > 2000 else (20 if price > 1000 else (10 if price > 500 else 5)))
        try:
            vol = math.sqrt((1.0 / (4.0 * math.log(2.0))) * ((np.log(df_h/df_l)**2).tail(10).mean())) * math.sqrt(252)
            if math.isnan(vol) or vol == 0: vol = np.log(df_c/df_c.shift(1)).tail(10).std() * math.sqrt(252)
            if math.isnan(vol) or vol == 0: vol = 0.2
        except: vol = 0.2
    
    atm = int(round(price / step) * step)
    opt_type = "CE" if direction == "Bullish" else "PE"
    
    c_prem = black_scholes(price, atm, dte/365.0, 0.07, vol, opt_type)
    pt1 = black_scholes(t1, atm, dte/365.0, 0.07, vol, opt_type)
    pt2 = black_scholes(t2, atm, dte/365.0, 0.07, vol, opt_type)
    pt3 = black_scholes(t3, atm, dte/365.0, 0.07, vol, opt_type)
    pt4 = black_scholes(t4, atm, dte/365.0, 0.07, vol, opt_type)
    pt5 = black_scholes(t5, atm, dte/365.0, 0.07, vol, opt_type)
    opt_sl = max(5.0, black_scholes(eq_sl, atm, dte/365.0, 0.07, vol, opt_type))
    
    return f"{atm} {opt_type}", c_prem, round(pt1, 1), round(pt2, 1), round(pt3, 1), round(pt4, 1), round(pt5, 1), round(opt_sl, 1)

def check_structure_hh_hl(df_h, df_l):
    if len(df_h) < 20: return True
    h_half1, h_half2 = df_h.iloc[-20:-10].max(), df_h.iloc[-10:].max()
    l_half1, l_half2 = df_l.iloc[-20:-10].min(), df_l.iloc[-10:].min()
    return (h_half2 >= h_half1) and (l_half2 >= l_half1)

def check_bullish_divergence(closes, rsi):
    try:
        if len(closes) < 30: return False
        w1_c = closes.iloc[-25:-10]
        w2_c = closes.iloc[-10:]
        p1_idx = w1_c.idxmin()
        p2_idx = w2_c.idxmin()
        p1, p2 = w1_c.min(), w2_c.min()
        r1, r2 = rsi.loc[p1_idx], rsi.loc[p2_idx]
        if (p2 < p1 and r2 > r1) or (p2 > p1 and r2 < r1):
            return True
    except: pass
    return False

def check_vwap_gate(ticker, close_p):
    try:
        df_intra = yf.download(ticker, period="1d", interval="5m", progress=False, threads=False)
        if df_intra.empty: return True
        if isinstance(df_intra.columns, pd.MultiIndex): df_intra.columns = df_intra.columns.get_level_values(0)
        v = df_intra['Volume']
        tp = (df_intra['High'] + df_intra['Low'] + df_intra['Close']) / 3
        vwap = (tp * v).sum() / v.sum() if v.sum() > 0 else close_p
        return close_p >= vwap
    except: return True

def validate_mtf_confluence(ticker):
    try:
        df_hr = yf.download(ticker, period="5d", interval="1h", progress=False, threads=False)
        if df_hr.empty: return True
        if isinstance(df_hr.columns, pd.MultiIndex): df_hr.columns = df_hr.columns.get_level_values(0)
        df_4h = df_hr['Close'].resample('4H').last().dropna()
        if len(df_4h) >= 3: return float(df_4h.iloc[-1]) >= float(df_4h.iloc[-2])
    except: pass
    return True

def get_index_options_ideas():
    indices = {'^NSEI': 'NIFTY 50', '^NSEBANK': 'BANK NIFTY'}
    results = []
    for ticker, name in indices.items():
        try:
            data = yf.download(ticker, period="5d", interval="15m", progress=False, threads=False)
            if data.empty: continue
            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
            
            df_c, df_h, df_l = data['Close'].dropna(), data['High'].dropna(), data['Low'].dropna()
            if df_c.empty: continue
            
            close_p = float(df_c.iloc[-1])
            ema_20_15m = float(df_c.ewm(span=20).mean().iloc[-1])
            
            hl = df_h - df_l
            tr = pd.concat([hl, (df_h - df_c.shift(1)).abs(), (df_l - df_c.shift(1)).abs()], axis=1).max(axis=1)
            atr_15m = float(tr.ewm(alpha=1/14).mean().iloc[-1])
            
            delta = df_c.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rsi_val = float((100 - (100 / (1 + (gain / loss)))).iloc[-1])
            
            if close_p > ema_20_15m:
                direction = "Bullish"
                t1, t2, t3, t4, t5 = round(close_p + 1.5*atr_15m, 1), round(close_p + 3.0*atr_15m, 1), round(close_p + 5.0*atr_15m, 1), round(close_p + 7.5*atr_15m, 1), round(close_p + 10.0*atr_15m, 1)
                eq_sl = round(close_p - 1.5 * atr_15m, 1)
            else:
                direction = "Bearish"
                t1, t2, t3, t4, t5 = round(close_p - 1.5*atr_15m, 1), round(close_p - 3.0*atr_15m, 1), round(close_p - 5.0*atr_15m, 1), round(close_p - 7.5*atr_15m, 1), round(close_p - 10.0*atr_15m, 1)
                eq_sl = round(close_p + 1.5 * atr_15m, 1)
            
            opt, prem, pt1, pt2, pt3, pt4, pt5, opt_sl = generate_quant_option(ticker, close_p, t1, t2, t3, t4, t5, eq_sl, df_h, df_l, df_c, direction)
            tv_sym = "NIFTY" if name == "NIFTY 50" else "BANKNIFTY"
            
            dir_label = "Bullish (Call)" if direction == "Bullish" else "Bearish (Put)"
            results.append({
                'Stock': f"{name} {dir_label}", 'RawStock': tv_sym, 'Horizon': 'Intraday', 'Entry': round(close_p, 2),
                'RSI': round(rsi_val, 1), 'EqSL': eq_sl,
                'EqT1': t1, 'EqT2': t2, 'EqT3': t3, 'EqT4': t4, 'EqT5': t5,
                'Opt': opt, 'Prem': prem, 'PT1': pt1, 'PT2': pt2, 'PT3': pt3, 'PT4': pt4, 'PT5': pt5, 'OptSL': opt_sl, 'Score': 10, 'Tag': 'Index 15m Scalp'
            })
        except Exception as e: pass
    return pd.DataFrame(results)

def generate_tabular_markdown(df_stocks, df_index, title, filename, include_index=False):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write("> **System:** 1200+ Mega Universe + Expanded Volatility Targets\n\n")
        if df_stocks.empty and df_index.empty:
            f.write("*Market conditions did not trigger any quantitative setups meeting institutional gates for this timeframe.*\n")
            return
        if include_index and not df_index.empty:
            f.write("## 👑 Index Options (15M Scalps)\n\n")
            f.write("| # | Index Signal | Price | Option | Buy Above | TGT // T1/T2/T3/T4/T5+ | SL |\n")
            f.write("| :--- | :--- | :---: | :---: | :---: | :---: | :---: |\n")
            for idx, r in df_index.reset_index().iterrows():
                tgts = f"{r['PT1']}/{r['PT2']}/{r['PT3']}/{r['PT4']}/{r['PT5']}+"
                f.write(f"| {idx+1} | **{r['Stock']}** | ₹{r['Entry']} | **{r['Opt']}** | ₹{r['Prem']} | {tgts} | ₹{r['OptSL']} |\n")
            f.write("\n---\n\n")
        if not df_stocks.empty:
            f.write("## 📊 Validated Setups & Options\n\n")
            f.write("| # | Stock | Setup Type | Price | Score | Qty | Risk | Option Signal (Buy/TGT/SL) |\n")
            f.write("| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |\n")
            for idx, r in df_stocks.reset_index().iterrows():
                badge = f"🔥 {r['Score']}/10"
                opt_str = str(r['Opt'])
                prem_str = str(r['Prem'])
                if "N/A" not in opt_str and prem_str != "-" and prem_str != "nan":
                    opt_info = f"**{r['Opt']}**<br>Buy Above: ₹{r['Prem']}<br>TGT: {r['PT1']}/{r['PT2']}/{r['PT3']}/{r['PT4']}/{r['PT5']}+<br>SL: ₹{r['OptSL']}"
                else:
                    opt_info = f"Cash Equity Only<br><b>Equity Targets:</b> ₹{r['EqT1']} / ₹{r['EqT2']} / ₹{r['EqT3']}"
                f.write(f"| {idx+1} | **{r['Stock']}** | {r['Tag']} | ₹{r['Entry']} | {badge} | {r['Qty']} | ₹{r['Risk']} | {opt_info} |\n")

def format_telegram_text(df_stocks, df_index, title):
    msg = f"🚨 *{title}* 🚨\n\n"
    if not df_index.empty:
        msg += "👑 *INDEX OPTIONS SIGNALS*\n"
        for _, r in df_index.iterrows():
            idx_name = "NIFTY" if "NIFTY 50" in r['Stock'] else "BANKNIFTY"
            ce_pe = r['Opt']
            msg += f"*{idx_name} {ce_pe}*\n"
            msg += f"Buy Above {r['Prem']}\n"
            msg += f"TGT // {r['PT1']}/{r['PT2']}/{r['PT3']}/{r['PT4']}/{r['PT5']}+\n"
            msg += f"SL {r['OptSL']}\n\n"
            
    if not df_stocks.empty:
        msg += "📊 *TOP POSITION SIZED SETUPS & OPTIONS*\n"
        for idx, r in df_stocks.head(25).reset_index().iterrows():
            stock_clean = r['Stock'].replace(" (↑)", "")
            msg += f"{idx+1}. *{stock_clean}* | *{r['Tag']}* (Score: *{r['Score']}/10*)\n"
            msg += f"   🛒 Qty: {r['Qty']} | 📉 Risk: ₹{r['Risk']}\n"
            msg += f"   Eq Entry: ₹{r['Entry']} | SL: ₹{r['EqSL']}\n"
            
            opt_str = str(r['Opt'])
            prem_str = str(r['Prem'])
            if "N/A" not in opt_str and prem_str != "-" and prem_str != "nan":
                msg += f"   🔹 *{stock_clean} {r['Opt']}*\n"
                msg += f"      Buy Above {r['Prem']}\n"
                msg += f"      TGT // {r['PT1']}/{r['PT2']}/{r['PT3']}/{r['PT4']}/{r['PT5']}+\n"
                msg += f"      SL {r['OptSL']}\n"
            else:
                msg += f"   🎯 *Eq Targets:* ₹{r['EqT1']} / ₹{r['EqT2']} / ₹{r['EqT3']}\n"
            msg += "\n"
    else: msg += "No setups cleared the institutional gates for this scan."
    return msg

def run():
    print("🚀 Starting Automated Master Quant Scanner (Expanded Volatility Targets)...")
    sess_title, sess_type = get_session_info()
    now_ist = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
    
    market_open = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
    if now_ist.weekday() >= 5 or now_ist > market_close or now_ist < market_open: minutes_elapsed = 375.0
    else: minutes_elapsed = min(max(1.0, (now_ist - market_open).total_seconds() / 60.0), 375.0)
    
    df_index = get_index_options_ideas() if sess_type in ["Intraday", "Manual"] else pd.DataFrame()
    
    nifty_df = yf.download("^NSEI", period="1y", interval="1d", progress=False)
    nifty_return_20d = 0.0
    if not nifty_df.empty:
        if isinstance(nifty_df.columns, pd.MultiIndex): nifty_df.columns = nifty_df.columns.get_level_values(0)
        nifty_closes = nifty_df['Close'].squeeze()
        if len(nifty_closes) >= 20: nifty_return_20d = float(nifty_closes.iloc[-1] / nifty_closes.iloc[-20] - 1)

    tickers = [f"{s}.NS" for s in EXTENDED_UNIVERSE]
    data = yf.download(tickers, period="1y", interval="1d", progress=False, threads=True)
    if data.empty: return
    
    if isinstance(data.columns, pd.MultiIndex): closes, highs, lows, volumes = data['Close'], data['High'], data['Low'], data['Volume']
    else: closes, highs, lows, volumes = data['Close'], data['High'], data['Low'], data['Volume']

    ema_50_daily = closes.ewm(span=50).mean()
    ema_20_daily = closes.ewm(span=20).mean()
    ema_200_daily = closes.ewm(span=200).mean()
    vol_50d_avg_daily = volumes.rolling(50).mean()
    
    delta = closes.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rsi_daily = 100 - (100 / (1 + (gain / loss)))

    macd_daily = closes.ewm(span=12, adjust=False).mean() - closes.ewm(span=26, adjust=False).mean()
    macd_signal_daily = macd_daily.ewm(span=9, adjust=False).mean()
    
    tr = pd.DataFrame(np.maximum((highs - lows).values, np.maximum((highs - closes.shift(1)).abs().values, (lows - closes.shift(1)).abs().values)), index=highs.index, columns=highs.columns)
    atr_daily = tr.ewm(alpha=1/14).mean()
    ema_50_weekly = closes.resample('W').last().dropna(how='all').ewm(span=50).mean()

    last_vol, last_vol_50 = volumes.iloc[-1], vol_50d_avg_daily.iloc[-1]
    last_rsi, last_macd, last_macd_signal = rsi_daily.iloc[-1], macd_daily.iloc[-1], macd_signal_daily.iloc[-1]
    last_ema_50, last_ema_20, last_ema_200, last_atr = ema_50_daily.iloc[-1], ema_20_daily.iloc[-1], ema_200_daily.iloc[-1], atr_daily.iloc[-1]
    last_ema_50_weekly = ema_50_weekly.iloc[-1]

    valid_setups = []

    for ticker in closes.columns:
        symbol = ticker.replace(".NS", "")
        try:
            close_p = float(closes[ticker].iloc[-1])
            vol_today, vol_50_avg = float(last_vol[ticker]), float(last_vol_50[ticker])
            if pd.isna(close_p) or close_p <= 0 or vol_today < 200000 or vol_50_avg < 200000: continue
            
            rsi_val, macd_val, macd_sig = float(last_rsi[ticker]), float(last_macd[ticker]), float(last_macd_signal[ticker])
            d_ema, w_ema, atr = float(last_ema_50[ticker]), float(last_ema_50_weekly[ticker]), float(last_atr[ticker])
            d_ema20 = float(last_ema_20[ticker])
            d_ema200 = float(last_ema_200[ticker]) if not pd.isna(last_ema_200[ticker]) else 0.0
            
            adjusted_vol_50 = vol_50_avg * (minutes_elapsed / 375.0)
            vol_vs = round(vol_today / adjusted_vol_50, 2)

            recent_vol_avg, recent_range_avg = float(volumes[ticker].tail(3).mean()), float((highs[ticker].tail(3) - lows[ticker].tail(3)).mean())
            recent_20d_high = float(highs[ticker].tail(20).max())
            
            dist_to_20d_high = (recent_20d_high - close_p) / close_p
            dist_to_20ema = (close_p - d_ema20) / d_ema20 if d_ema20 > 0 else 0
            dist_to_200ema = abs(close_p - d_ema200) / d_ema200 if d_ema200 > 0 else 999

            is_squeeze = (recent_vol_avg < vol_50_avg * 0.85) and (recent_range_avg < atr * 0.85)
            is_relative_strong = (float(closes[ticker].dropna().iloc[-1] / closes[ticker].dropna().iloc[-20] - 1) > nifty_return_20d) if len(closes[ticker].dropna()) >= 20 else False
            
            is_pre_breakout = (0.002 <= dist_to_20d_high <= 0.035) and (close_p > d_ema20) and (vol_vs <= 1.25)
            is_200ma_retest = (d_ema200 > 0) and (dist_to_200ema <= 0.025) and (vol_vs <= 1.0) and (close_p >= d_ema200)
            is_swing_retest = (0.025 <= dist_to_20d_high <= 0.15) and (0.0 <= dist_to_20ema <= 0.04) and (vol_vs <= 1.0)
            
            is_rsi_div = check_bullish_divergence(closes[ticker].dropna(), rsi_daily[ticker].dropna())

            if is_pre_breakout: hor, sl_m, tag = "Pre-Breakout", 1.0, "💥 Pre-Breakout Coil"
            elif is_200ma_retest: hor, sl_m, tag = "Swing", 1.5, "🏦 200 MA Retest"
            elif is_swing_retest: hor, sl_m, tag = "Swing", 1.2, "🔄 Breakout Retest"
            elif vol_vs >= 1.5: hor, sl_m, tag = "Intraday", 0.8, "🚀 Volume Breakout"
            elif is_squeeze or vol_vs >= 1.2: hor, sl_m, tag = "BTST", 1.0, "🔥 Squeeze Blast"
            else: continue
            
            if is_rsi_div: tag += " (📉 +RSI Div)"

            if close_p > d_ema and close_p > w_ema and macd_val > macd_sig and (45 <= rsi_val <= 85) and is_relative_strong and check_structure_hh_hl(highs[ticker], lows[ticker]):
                if hor in ["Intraday", "BTST"] and not check_vwap_gate(ticker, close_p): continue
                if not validate_mtf_confluence(ticker): continue

                t1, t2, t3, t4, t5 = calculate_dynamic_targets(close_p, atr, highs[ticker], lows[ticker], "Bullish", is_squeeze)
                eq_sl = round(close_p - sl_m * atr, 1)
                
                risk, reward = close_p - eq_sl, (t2 - close_p) if hor in ["Swing", "Pre-Breakout"] else (t1 - close_p)
                if risk <= 0 or (reward / risk) < 1.5: continue
                
                score = 0
                if close_p > d_ema: score += 1
                if close_p > w_ema: score += 1
                if 55 <= rsi_val <= 70: score += 2
                elif 45 <= rsi_val <= 85: score += 1
                if macd_val > macd_sig: score += 1
                if macd_val > 0: score += 1
                if is_relative_strong: score += 1
                if is_relative_strong and (float(closes[ticker].dropna().iloc[-1] / closes[ticker].dropna().iloc[-20] - 1) > nifty_return_20d + 0.02): score += 1
                
                if hor == "Swing" and vol_vs < 0.8: score += 2
                elif hor == "Swing" and vol_vs <= 1.0: score += 1
                elif hor == "Pre-Breakout" and is_squeeze: score += 2
                elif hor == "Pre-Breakout": score += 1
                elif hor == "Intraday" and vol_vs >= 2.0: score += 2
                elif hor == "Intraday": score += 1
                elif hor == "BTST" and is_squeeze: score += 2
                elif hor == "BTST": score += 1
                
                if is_rsi_div: score += 2
                final_score = min(10, score)
                
                is_high_conviction = (final_score >= 8) 
                if is_high_conviction and not is_pre_breakout and not is_swing_retest and not is_200ma_retest and not is_rsi_div: tag += " (⭐ 2x Size)"
                cash_qty = int((BASE_CAPITAL_PER_TRADE * HIGH_CONVICTION_MULTIPLIER if is_high_conviction else BASE_CAPITAL_PER_TRADE) / close_p)

            else: continue 

            df_h, df_l, df_c = highs[ticker].dropna(), lows[ticker].dropna(), closes[ticker].dropna()
            
            if symbol in STATIC_FNO:
                try: opt, prem, pt1, pt2, pt3, pt4, pt5, opt_sl = generate_quant_option(symbol, close_p, t1, t2, t3, t4, t5, eq_sl, df_h, df_l, df_c, "Bullish")
                except: opt, prem, pt1, pt2, pt3, pt4, pt5, opt_sl = "N/A (Data Err)", "-", "-", "-", "-", "-", "-", "-"
            else: opt, prem, pt1, pt2, pt3, pt4, pt5, opt_sl = "N/A (Cash)", "-", "-", "-", "-", "-", "-", "-"
            
            valid_setups.append({
                'Stock': f"{symbol} (↑)", 'RawStock': symbol, 'Horizon': hor, 'Tag': tag, 'Entry': round(close_p, 2), 
                'Qty': cash_qty, 'Risk': round(cash_qty * (close_p - eq_sl), 2), 'RSI': round(rsi_val,1), 'Vol vs 50d': vol_vs,
                'EqSL': eq_sl, 'EqT1': t1, 'EqT2': t2, 'EqT3': t3, 'EqT4': t4, 'EqT5': t5, 
                'Opt': opt, 'Prem': prem, 'PT1': pt1, 'PT2': pt2, 'PT3': pt3, 'PT4': pt4, 'PT5': pt5, 'OptSL': opt_sl, 'Score': final_score
            })
        except: continue

    df_all = pd.DataFrame(valid_setups).drop_duplicates(subset=['Stock']).sort_values(by=['Score', 'RSI'], ascending=[False, False]) if valid_setups else pd.DataFrame()

    if not df_all.empty: df_all.to_csv("all_setups.csv", index=False)
    else: pd.DataFrame(columns=['Stock','RawStock','Horizon','Tag','Entry','Qty','Risk','RSI','Vol vs 50d','EqSL','EqT1','EqT2','EqT3','EqT4','EqT5','Opt','Prem','PT1','PT2','PT3','PT4','PT5','OptSL','Score']).to_csv("all_setups.csv", index=False)
    
    if not df_index.empty: df_index.to_csv("index_setups.csv", index=False)
    else: pd.DataFrame(columns=['Stock','RawStock','Horizon','Entry','RSI','EqSL','EqT1','EqT2','EqT3','EqT4','EqT5','Opt','Prem','PT1','PT2','PT3','PT4','PT5','OptSL','Score','Tag']).to_csv("index_setups.csv", index=False)

    df_pre = df_all[df_all['Horizon'] == 'Pre-Breakout'].head(25) if not df_all.empty else pd.DataFrame()
    df_intra = df_all[df_all['Horizon'] == 'Intraday'].head(25) if not df_all.empty else pd.DataFrame()
    df_btst = df_all[df_all['Horizon'] == 'BTST'].head(25) if not df_all.empty else pd.DataFrame()
    df_swing = df_all[df_all['Horizon'] == 'Swing'].head(25) if not df_all.empty else pd.DataFrame()

    generate_tabular_markdown(df_pre, pd.DataFrame(), f"💥 Soon to Breakout Report (Top 25) — {sess_title}", "prebreakout_report.md", False)
    generate_tabular_markdown(df_intra, df_index, f"⚡ Intraday Report (Top 25) — {sess_title}", "intraday_report.md", True)
    generate_tabular_markdown(df_btst, pd.DataFrame(), f"🌙 BTST Report (Top 25) — {sess_title}", "btst_report.md", False)
    generate_tabular_markdown(df_swing, pd.DataFrame(), f"📈 Swing Trade Retest Report (Top 25) — {sess_title}", "swing_report.md", False)

    if not df_pre.empty: send_telegram_message(format_telegram_text(df_pre.head(25), pd.DataFrame(), f"💥 Soon to Breakout — {sess_title}"))
    if not df_intra.empty or not df_index.empty: send_telegram_message(format_telegram_text(df_intra.head(25), df_index, f"⚡ Intraday Report — {sess_title}"))
    if not df_btst.empty: send_telegram_message(format_telegram_text(df_btst.head(25), pd.DataFrame(), f"🌙 BTST Report — {sess_title}"))
    if not df_swing.empty: send_telegram_message(format_telegram_text(df_swing.head(25), pd.DataFrame(), f"📈 Swing Trade (Retest) Report — {sess_title}"))

if __name__ == "__main__":
    run()
