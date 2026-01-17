import streamlit as st
import requests
import time
import json
import datetime
import pandas as pd

# --- CONFIGURATION ---
RAW_URL = "https://gist.githubusercontent.com/joshbird98/9de20220c7cd1e3c359c22b4775faa46/raw/status.json"

# --- FAULT DICTIONARY (Edit these to match your PLC Logic) ---
# Maps the Index of "system.general.faultArray[i]" to a string
FAULT_MAP = {
    0: "Unknown fault - reserved",
    1: "HV door interlock reads open",
    2: "Water coolant primary flow reads off",
    3: "Water coolant primary temp exceeds safe limit",
    4: "Chiller unit reports fault",
    5: "Source body temp exceeds safe limit",
    6: "Thermionic current exceeds safe conditioning level",
    7: "Thermionic current exceeds safe limit",
    8: "Thermionic voltage exceeds safe limit",
    9: "Thermionic power exceeds safe limit",
    10: "Filament current exceeds safe limit",
    11: "Filament voltage exceeds safe limit",
    12: "Filament power exceeds safe limit",
    13: "Filament resistance too high - possible open circuit",
    14: "Filament resistance too low - possible short circuit",
    15: "Ioniser power exceeds safe limit",
    16: "Ioniser PID control error",
    17: "Target current exceeds safe conditioning limit",
    18: "Target current exceeds safe limit",
    19: "Target voltage exceeds safe limit",
    20: "Target power exceeds safe limit",
    21: "Extraction current exceeds safe conditioning limit",
    22: "Extraction current exceeds safe limit",
    23: "Extraction voltage exceeds safe limit",
    24: "Extraction power exceeds safe limit",
    25: "Cesium temperature exceeds safe limit",
    26: "Cesium cooldown has exceeded time limit",
    27: "Cesium temperature reading failed",
    28: "Cesium temperature has not increased within time limit",
    29: "Cesium PID control error",
    30: "Vaccum level in source too high",
    31: "Time Fault",
    32: "Flow rate for source coolant is insufficient",
    33: "PLC Diagnostic Error - OB82",
    34: "Rack Error - cannot reach IO module",
}

st.set_page_config(
    page_title="IPIDS Monitor",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed", # Hides the sidebar by default on mobile
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# --- CSS STYLING ---
st.markdown("""
    <style>
        /* 1. STANDARD METRIC CARDS */
        .stMetric {
            background-color: #1E1E1E;
            border: 1px solid #333333;
            padding: 15px 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            height: 140px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        [data-testid="stMetricLabel"] { color: #B0B0B0 !important; font-weight: 500; font-size: 0.9rem; }
        [data-testid="stMetricValue"] { color: #FFFFFF !important; font-family: 'Roboto Mono', monospace; font-size: 1.8rem !important; }

        /* 2. CUSTOM STATUS CARD STYLES */
        .status-card {
            padding: 15px 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            height: 140px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            text-align: center;
            font-family: "Source Sans Pro", sans-serif;
        }
        
        /* FAULT STATE (Red) */
        .status-critical { background-color: #5a1a1a; border: 2px solid #ff4b4b; }
        .status-critical .stat-label { color: #ffcccc; font-size: 0.9rem; font-weight: 500; }
        .status-critical .stat-value { color: #ffffff; font-size: 1.8rem; font-weight: 700; font-family: 'Roboto Mono', monospace; }
        .status-critical .stat-delta { color: #ff9999; font-size: 1.0rem; margin-top: 5px; font-weight: 600; }

        /* WARNING/STALE STATE (Orange) */
        .status-warning { background-color: #1E1E1E; border: 1px solid #ff9f1c; }
        .status-warning .stat-label { color: #B0B0B0; }
        .status-warning .stat-value { color: #ffffff; font-family: 'Roboto Mono', monospace; font-size: 1.8rem; }
        .status-warning .stat-delta { color: #ff9f1c; margin-top: 5px; }

        /* NORMAL STATE (Green) */
        .status-normal { background-color: #1E1E1E; border: 1px solid #09ab3b; }
        .status-normal .stat-label { color: #B0B0B0; }
        .status-normal .stat-value { color: #ffffff; font-family: 'Roboto Mono', monospace; font-size: 1.8rem; }
        .status-normal .stat-delta { color: #09ab3b; font-size: 0.9rem; margin-top: 5px; }

        /* 3. ACTIVE FAULT LIST (Red Box below header) */
        .fault-banner {
            background-color: #5a1a1a;
            border-left: 5px solid #ff4b4b;
            padding: 15px;
            margin-top: 10px;
            border-radius: 5px;
            color: #ffcccc;
        }

        div[data-testid="column"] { text-align: center; }
        .block-container { padding-top: 2rem; }

        /* DISABLE PULL-TO-REFRESH */
        html, body, [data-testid="stAppViewContainer"] {
            overscroll-behavior-y: none !important;
        }
        
    </style>
""", unsafe_allow_html=True)

# --- HIDE STREAMLIT STYLE ---
st.markdown("""
    <style>
        /* Hide the top header (Hamburger menu, Running man icon) */
        header {
            visibility: hidden;
            height: 0px;
        }

        /* Hide the bottom footer (Made with Streamlit) */
        footer {
            visibility: hidden;
            height: 0px;
        }
        
        /* Optional: Hide the top colored decoration bar */
        .stApp > header {
            background-color: transparent;
        }
        
        /* Adjust top padding since header is gone */
        .block-container {
            padding-top: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def render_status_card(container, label, value, sub_text, style="normal"):
    """Renders the custom HTML status card."""
    css_class = f"status-{style}"
    html_code = f"""
    <div class="status-card {css_class}">
        <div class="stat-label">{label}</div>
        <div class="stat-value">{value}</div>
        <div class="stat-delta">{sub_text}</div>
    </div>
    """
    container.markdown(html_code, unsafe_allow_html=True)

def get_active_fault_messages(data):
    """Scans data for faultArray[i] == True and returns list of strings."""
    active_faults = []
    if not data:
        return []
        
    # Check the standard fault array keys
    # We assume keys look like: system.general.faultArray[0], system.general.faultArray[1]...
    for i in range(99): # Check up to 99 faults
        try:
            key = f"system.general.faultArray[{i}]"
            is_active = data.get(key, False)
        
            if is_active:
                # Look up the description, or default to "Unknown Fault #X"
                desc = FAULT_MAP.get(i, f"Fault Code #{i}")
                active_faults.append(desc)
        except KeyError:
            pass
            
    return active_faults

def get_raw_data():
    try:
        cache_buster = f"?t={int(time.time())}"
        final_url = RAW_URL + cache_buster
        response = requests.get(final_url, timeout=5)
        
        if response.status_code == 200:
            try:
                snapshot = response.json()
            except json.JSONDecodeError:
                return None, None
            
            raw_ts = snapshot.get('timestamp')
            ts_val = None
            if raw_ts:
                try:
                    ts_val = float(raw_ts)
                except:
                    pass
            return snapshot, ts_val
    except:
        pass
    return None, None

def get_val(data, path, default=0):
    if not data: return default
    return data.get(path, default)

# --- MAIN UI ---

st.title("⚡ IPIDS Monitor")

# Memory / Fetch Logic
if "best_snapshot" not in st.session_state:
    st.session_state["best_snapshot"] = None
if "best_ts" not in st.session_state:
    st.session_state["best_ts"] = 0.0

fresh_snapshot, fresh_ts = get_raw_data()
if fresh_snapshot and fresh_ts:
    if fresh_ts >= st.session_state["best_ts"]:
        st.session_state["best_snapshot"] = fresh_snapshot
        st.session_state["best_ts"] = fresh_ts

raw_snapshot = st.session_state["best_snapshot"]
msg_timestamp = st.session_state["best_ts"]

if raw_snapshot is None:
    st.warning("📡 Connecting to GitHub...")
    time.sleep(2)
    st.rerun()

data = raw_snapshot.get("data", {})

# Calculations
age_seconds = time.time() - msg_timestamp if msg_timestamp else 0
is_stale = age_seconds > 80
is_offline = age_seconds > 300

# Status & Faults
fault_active_bit = get_val(data, "system.general.systemFault", False)
active_fault_list = get_active_fault_messages(data)

# If the global bit is true OR we found specific faults in the list
is_fault_condition = fault_active_bit or (len(active_fault_list) > 0)

state_code = get_val(data, "system.ionSource.general.status", 0)
state_map = {0: "OFF", 1: "STARTING", 2: "RUNNING", 99: "FAULT"}
sys_state = state_map.get(state_code, "UNKNOWN")

# --- HEADER ROW ---
c1, c2, c3 = st.columns([1, 2, 1])

c1.metric("System State", sys_state)

# LOGIC: What to show in the center card?
if is_fault_condition:
    # 1. Determine what text to show
    if len(active_fault_list) == 1:
        # If only one fault, show it directly in the card
        sub_text = f"⚠️ {active_fault_list[0]}"
    elif len(active_fault_list) > 1:
        # If multiple, show count
        sub_text = f"⚠️ {len(active_fault_list)} Active Faults"
    else:
        # Fallback if bit is true but no array match
        sub_text = "⚠️ Check PLC Logs"

    render_status_card(c2, "Diagnostics", "FAULT ACTIVE", sub_text, style="critical")

elif is_offline:
    render_status_card(c2, "Diagnostics", "OFFLINE", f"Last seen {int(age_seconds)}s ago", style="warning")
elif is_stale:
    render_status_card(c2, "Diagnostics", "SYSTEM NORMAL", f"⚠️ Slow Connection ({int(age_seconds)}s)", style="warning")
else:
    render_status_card(c2, "Diagnostics", "SYSTEM NORMAL", "✅ Online and Stable", style="normal")

if msg_timestamp:
    pretty_time = datetime.datetime.fromtimestamp(msg_timestamp).strftime('%H:%M:%S')
else:
    pretty_time = "Unknown"
c3.metric("Last Update", pretty_time)

# --- DETAILED FAULT LIST (New Section) ---
# If there is more than 1 fault, or if we just want to be explicit, list them here.
if is_fault_condition and len(active_fault_list) > 0:
    st.markdown('<div class="fault-banner"><strong>❌ Active System Faults:</strong><ul>' + 
                "".join([f"<li>{err}</li>" for err in active_fault_list]) + 
                "</ul></div>", unsafe_allow_html=True)

st.divider()

# --- METRICS GRID ---
st.subheader("🚀 Primary Parameters")
r1c1, r1c2, r1c3, r1c4 = st.columns(4)

p_filament = get_val(data, "system.ionSource.ioniser.filament.readbackW", 0)
r1c1.metric("Filament Power", f"{p_filament:.2f} W")

p_source = get_val(data, "system.vacuumSystem.gauges.source.readback_mB", 0)
r1c2.metric("Source Pressure", f"{p_source:.1e} mbar")

cup_current = get_val(data, "beamline.drop_in_cup.measured_current_A", 0)
if cup_current == 0:
    cup_current = get_val(data, "beamline.straight_thru_cup.measured_current_A", 0)
    label = "Beam Current (Str)"
else:
    label = "Beam Current (Cup)"
r1c3.metric(label, f"{cup_current*1e6:.1f} µA")

v_mag = get_val(data, "beamline.magnet.readbackA", 0)
r1c4.metric("Magnet Current", f"{v_mag:.2f} A")

# ROW 2
st.subheader("⚛️ Ion Source Control")
r2c1, r2c2, r2c3, r2c4 = st.columns(4)

fil_a = get_val(data, "system.ionSource.ioniser.filament.readbackA", 0)
r2c1.metric("Filament", f"{fil_a:.2f} A")

ion_w = get_val(data, "system.ionSource.ioniser.readbackW", 0)
r2c2.metric("Ioniser Power", f"{ion_w:.1f} W")

ext_v = get_val(data, "system.ionSource.extraction.readbackV", 0)
r2c3.metric("Extraction", f"{ext_v:.1f} V")

cs_temp = get_val(data, "system.ionSource.cesium.readbackC", 0)
r2c4.metric("Cesium Temp", f"{cs_temp:.1f} °C")

# ROW 3
st.subheader("💨 Vacuum & Cooling")
r3c1, r3c2, r3c3, r3c4 = st.columns(4)

turbo_spd = get_val(data, "system.vacuumSystem.pumps.turbo.source_1.speed", 0)
r3c1.metric("Turbo Speed", f"{turbo_spd:.0f} Hz")

coolant = get_val(data, "system.general.coolantStatus", False)
r3c2.metric("Coolant Flow", "OK" if coolant else "LOW", delta="Normal" if coolant else "-Fault", delta_color="normal" if coolant else "inverse")

gate_val = get_val(data, "system.vacuumSystem.valves.gate.open", False)
r3c3.metric("Gate Valve", "OPEN" if gate_val else "CLOSED")

stage_z = get_val(data, "endstation.stage.motion.readback_z_mm", 0)
r3c4.metric("Stage Z", f"{stage_z:.1f} mm")

# Auto-reload logic
time.sleep(1) 
st.empty()
refresh_rate = 10 if not is_offline else 30
time.sleep(refresh_rate)
st.rerun()
