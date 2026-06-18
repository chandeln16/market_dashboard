import streamlit as st
import pandas as pd
import time
from datetime import datetime
import sqlite3
from fyers_apiv3 import fyersModel

# ─────────────────────── PAGE CONFIG ───────────────────────
st.set_page_config(
    page_title="Live PCR Dashboard | Fyers",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────── DATABASE CONFIG ───────────────────
# Initialize SQLite Connection (Cached to prevent reconnecting on every rerun)
@st.cache_resource
def init_db():
    conn = sqlite3.connect('pcr_data.db', check_same_thread=False)
    c = conn.cursor()
    # Create table if it doesn't exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS pcr_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_time TEXT,
            index_name TEXT,
            expiry_date TEXT,
            oi_pcr REAL,
            change_oi_pcr REAL,
            volume_pcr REAL,
            change_volume_pcr REAL
        )
    ''')
    conn.commit()
    return conn

db_conn = init_db()

# ─────────────────────── SESSION STATE ─────────────────────
# Removed 'pcr_history' and 'last_pcr_time' as they are now handled by SQLite
for k, v in {
    "fyers":             None,
    "auto_refresh":      False,
    "current_index":     "NIFTY 50",
    "current_expiry":    None,
    "expiry_options":    [],
    "expiry_timestamps": {},
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────── SIDEBAR ───────────────────────────
st.sidebar.title("⚙️ Fyers Login")
st.sidebar.markdown("---")
client_id    = st.sidebar.text_input("Client ID (App ID)", value="OIROK73TDQ-100")
access_token = st.sidebar.text_input("Access Token", type="password")

if st.sidebar.button("🔗 Connect to Fyers", use_container_width=True):
    if client_id and access_token:
        try:
            obj = fyersModel.FyersModel(client_id=client_id, is_async=False, token=access_token, log_path="")
            r = obj.get_profile()
            if r.get("code") == 200:
                st.session_state.fyers = obj
                st.sidebar.success(f"✅ Connected: {r['data']['name']}")
            else:
                st.sidebar.error(f"❌ {r.get('message', 'Auth failed')}")
        except Exception as e:
            st.sidebar.error(f"❌ {e}")
    else:
        st.sidebar.warning("⚠️ Enter both Client ID & Access Token")

st.sidebar.info("🟢 Connected" if st.session_state.fyers else "🔴 Not connected")
st.sidebar.markdown("---")

# Index & Expiry Selection
index_options = {"NIFTY 50": "NSE:NIFTY50-INDEX", "BANK NIFTY": "NSE:NIFTYBANK-INDEX", "SENSEX": "BSE:SENSEX-INDEX"}
selected_index_name = st.sidebar.selectbox("Choose Index", list(index_options.keys()))
selected_symbol = index_options[selected_index_name]

if st.session_state.current_index != selected_index_name:
    st.session_state.current_index = selected_index_name
    st.session_state.current_expiry = None
    st.session_state.expiry_options = []
    st.session_state.expiry_timestamps = {}
    st.rerun()

if st.session_state.fyers and not st.session_state.expiry_options:
    try:
        base_resp = st.session_state.fyers.optionchain(data={"symbol": selected_symbol, "strikecount": 1, "timestamp": ""})
        if base_resp.get("code") == 200:
            exp_data = base_resp["data"].get("expiryData", [])
            st.session_state.expiry_options = [ex["date"] for ex in exp_data]
            st.session_state.expiry_timestamps = {ex["date"]: ex["timestamp"] for ex in exp_data}
    except: pass

selected_timestamp = ""
if st.session_state.expiry_options:
    selected_expiry = st.sidebar.selectbox("📅 Select Expiry", st.session_state.expiry_options)
    selected_timestamp = st.session_state.expiry_timestamps.get(selected_expiry, "")
    if st.session_state.current_expiry != selected_expiry:
        st.session_state.current_expiry = selected_expiry
        st.rerun()

st.sidebar.markdown("---")
refresh_sec = st.sidebar.slider("Interval (seconds)", 1, 10, 5)
auto_on = st.sidebar.toggle("Enable Auto-Refresh", value=st.session_state.auto_refresh)
st.session_state.auto_refresh = auto_on

# 👨‍💻 Author Info
st.sidebar.markdown("---")
st.sidebar.subheader("👨‍💻 Developer")
st.sidebar.markdown("**Narendra** [📸 Instagram (@chandeln16)](https://instagram.com/chandeln16)")

# ─────────────────────── FIXED HELPERS ──────────────────

def fetch_chain(fyers_obj, symbol, timestamp):
    return fyers_obj.optionchain(data={"symbol": symbol, "strikecount": 50, "timestamp": str(timestamp)})

def parse_chain(resp):
    if resp.get('s') != 'ok':
        raise ValueError(resp.get("message", "API error"))
    
    data_dict = resp.get("data", {})
    raw = data_dict.get("optionsChain", [])
    if not raw: raise ValueError("No data available.")
    
    # Force float type to avoid calculation errors
    atm = float(data_dict.get("atm", 0))
    
    df = pd.DataFrame(raw)
    
    df_c = df[df['option_type'] == 'CE'].copy().rename(columns={"oi":"OI", "oich":"Chng OI", "volume":"Volume", "ltp":"LTP", "strike_price":"Strike"})
    df_p = df[df['option_type'] == 'PE'].copy().rename(columns={"oi":"OI", "oich":"Chng OI", "volume":"Volume", "ltp":"LTP", "strike_price":"Strike"})
    
    for d in [df_c, df_p]:
        if 'IV' not in d: d['IV'] = 0.0
        if 'Chng Volume' not in d: d['Chng Volume'] = 0
            
    return df_c.sort_values("Strike"), df_p.sort_values("Strike"), atm

def compute_summary(df_c, df_p):
    def sdiv(a, b): return round(a / b, 4) if b else 0.0
    tc_oi, tp_oi = df_c["OI"].sum(), df_p["OI"].sum()
    tc_co, tp_co = df_c["Chng OI"].sum(), df_p["Chng OI"].sum()
    tc_vol, tp_vol = df_c["Volume"].sum(), df_p["Volume"].sum()
    
    return {
        "Total Call OI": tc_oi, "Total Put OI": tp_oi, "Call Chng OI": tc_co, "Put Chng OI": tp_co,
        "OI PCR": sdiv(tp_oi, tc_oi), "Change OI PCR": sdiv(tp_co, tc_co),
        "Total Call Volume": tc_vol, "Total Put Volume": tp_vol,
        "Volume PCR": sdiv(tp_vol, tc_vol), "Change Volume PCR": 0.0, "Call Chng Volume": 0, "Put Chng Volume": 0
    }

def maybe_record_pcr(s_data, index_name, expiry_date):
    """Saves data to SQLite if 5 minutes have passed since the last record for the selected index & expiry."""
    c = db_conn.cursor()
    # Check the latest timestamp for this specific index & expiry
    c.execute('''
        SELECT record_time FROM pcr_history 
        WHERE index_name = ? AND expiry_date = ? 
        ORDER BY record_time DESC LIMIT 1
    ''', (index_name, expiry_date))
    
    row = c.fetchone()
    now = datetime.now()
    should_record = False
    
    if row is None:
        should_record = True
    else:
        last_time = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        if (now - last_time).total_seconds() >= 300:
            should_record = True

    if should_record:
        c.execute('''
            INSERT INTO pcr_history 
            (record_time, index_name, expiry_date, oi_pcr, change_oi_pcr, volume_pcr, change_volume_pcr) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            now.strftime("%Y-%m-%d %H:%M:%S"), 
            index_name, 
            expiry_date, 
            s_data["OI PCR"], 
            s_data["Change OI PCR"], 
            s_data["Volume PCR"], 
            s_data["Change Volume PCR"]
        ))
        db_conn.commit()

def sentiment(v):
    if v > 1.2: return "🟢 Bullish"
    if v < 0.8: return "🔴 Bearish"
    return "🟡 Neutral"


# ─────────────────────── MAIN DASHBOARD ────────────────────
st.title(f"📊 {selected_index_name} PCR Metrics Dashboard")

if not st.session_state.fyers or not st.session_state.current_expiry:
    st.warning("👈 Connect Fyers and select Expiry from the sidebar.")
    st.stop()

try:
    raw_resp = fetch_chain(st.session_state.fyers, selected_symbol, selected_timestamp)
    df_c, df_p, api_atm = parse_chain(raw_resp)
    
    strikes_list = sorted(df_c['Strike'].unique().tolist())
    
    if strikes_list:
        # SMART ATM LOGIC
        if api_atm <= 0:
            try:
                merged = pd.merge(df_c[['Strike', 'LTP']], df_p[['Strike', 'LTP']], on='Strike', suffixes=('_C', '_P'))
                merged['diff'] = abs(merged['LTP_C'] - merged['LTP_P'])
                atm_closest = merged.loc[merged['diff'].idxmin()]['Strike']
            except:
                atm_closest = strikes_list[len(strikes_list)//2]
        else:
            atm_closest = min(strikes_list, key=lambda x: abs(x - api_atm))
            
        atm_index = strikes_list.index(atm_closest)
        
        # 1. Lower Strikes Generator
        lower_options = []
        lower_map = {}
        for i in range(-12, 1):
            idx = atm_index + i
            if 0 <= idx < len(strikes_list):
                s = strikes_list[idx]
                label = f"{s:,.0f} (ATM {i})" if i < 0 else f"{s:,.0f} (ATM)"
                lower_options.append(label)
                lower_map[label] = s
                
        # 2. Upper Strikes Generator
        upper_options = []
        upper_map = {}
        for i in range(0, 13):
            idx = atm_index + i
            if 0 <= idx < len(strikes_list):
                s = strikes_list[idx]
                label = f"{s:,.0f} (ATM +{i})" if i > 0 else f"{s:,.0f} (ATM)"
                upper_options.append(label)
                upper_map[label] = s

        # 3. UI 3 Box Menu
        st.sidebar.markdown("---")
        st.sidebar.subheader("🎯 Strike Range Menu")
        
        selected_lower_label = st.sidebar.selectbox("📉 Select Lower Strike (-12 to ATM)", options=lower_options, index=0)
        st.sidebar.selectbox("📍 Current ATM (Fixed)", options=[f"{atm_closest:,.0f} (ATM)"], disabled=True)
        selected_upper_label = st.sidebar.selectbox("📈 Select Upper Strike (ATM to +12)", options=upper_options, index=len(upper_options)-1)
        
        start_strike = lower_map[selected_lower_label]
        end_strike = upper_map[selected_upper_label]
        
        # Filter Data
        df_c = df_c[(df_c['Strike'] >= start_strike) & (df_c['Strike'] <= end_strike)]
        df_p = df_p[(df_p['Strike'] >= start_strike) & (df_p['Strike'] <= end_strike)]
        
        st.caption(f"Fyers API v3 • Current ATM: **{atm_closest:,.0f}** • Calculating data for strikes: **{start_strike:,.0f}** to **{end_strike:,.0f}**")

    # Metrics calculation 
    s = compute_summary(df_c, df_p)
    # Record to DB logic
    maybe_record_pcr(s, selected_index_name, st.session_state.current_expiry)

    # UI Row 1 - Metrics
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("📞 Total Call OI", f"{s['Total Call OI']:,}")
    a2.metric("🤙 Total Put OI", f"{s['Total Put OI']:,}")
    a3.metric("📞 Call Chng OI", f"{s['Call Chng OI']:,}")
    a4.metric("🤙 Put Chng OI", f"{s['Put Chng OI']:,}")

    # UI Row 2 - PCR Metrics
    b1, b2, b3, b4 = st.columns(4)
    b1.metric("⚖️ OI PCR", s["OI PCR"], delta=sentiment(s["OI PCR"]), delta_color="off")
    b2.metric("⚖️ Change OI PCR", s["Change OI PCR"], delta=sentiment(s["Change OI PCR"]), delta_color="off")
    b3.metric("📊 Volume PCR", s["Volume PCR"], delta=sentiment(s["Volume PCR"]), delta_color="off")
    b4.metric("📊 Chng Vol PCR", s["Change Volume PCR"], delta=sentiment(s["Change Volume PCR"]), delta_color="off")

    # SECTION 2 — Separate Tables & Chart Fetching from Database
    query = '''
        SELECT 
            record_time, 
            oi_pcr as "OI PCR", 
            change_oi_pcr as "Change OI PCR", 
            volume_pcr as "Volume PCR", 
            change_volume_pcr as "Change Volume PCR" 
        FROM pcr_history 
        WHERE index_name = ? AND expiry_date = ?
        ORDER BY record_time ASC
    '''
    df_h = pd.read_sql_query(query, db_conn, params=(selected_index_name, st.session_state.current_expiry))
    
    if not df_h.empty:
        st.markdown("---")
        st.subheader("🕐 5-Minute PCR Snapshot Tables")
        
        # Formatting 'record_time' to show only HH:MM:SS format
        df_h['Time'] = pd.to_datetime(df_h['record_time']).dt.strftime('%H:%M:%S')
        
        t1, t2, t3, t4 = st.columns(4)
        
        with t1:
            st.markdown("**(1) OI PCR History**")
            st.dataframe(df_h[["Time", "OI PCR"]], use_container_width=True, hide_index=True)
            
        with t2:
            st.markdown("**(2) Change OI PCR History**")
            st.dataframe(df_h[["Time", "Change OI PCR"]], use_container_width=True, hide_index=True)
            
        with t3:
            st.markdown("**(3) Volume PCR History**")
            st.dataframe(df_h[["Time", "Volume PCR"]], use_container_width=True, hide_index=True)
            
        with t4:
            st.markdown("**(4) Change Volume PCR History**")
            st.dataframe(df_h[["Time", "Change Volume PCR"]], use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("📈 PCR Trends Chart")
        st.line_chart(df_h.set_index("Time")[["OI PCR", "Change OI PCR", "Volume PCR"]], use_container_width=True)

except Exception as ex:
    st.error(f"❌ Error: {ex}")

if st.session_state.auto_refresh:
    time.sleep(refresh_sec)
    st.rerun()
