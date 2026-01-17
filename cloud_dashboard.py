import streamlit as st
import requests
import time
import json
import datetime
import pandas as pd

# --- CONFIGURATION ---
# The raw link to your status.json file
RAW_URL = "https://gist.githubusercontent.com/joshbird98/9de20220c7cd1e3c359c22b4775faa46/raw/status.json"

st.set_page_config(
    page_title="IPIDS Monitor",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS STYLING ---
st.markdown("""
    <style>
        /* 1. The Card Container */
        .stMetric {
            background-color: #1E1E1E; /* Material Dark Grey */
            border: 1px solid #333333;
            padding: 15px 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            height: 140px; /* FORCE EQUAL HEIGHT for all cards */
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        /* 2. The Label (Small text at the top) */
        [data-testid="stMetricLabel"] {
            color: #B0B0B0 !important;
            font-weight: 500;
            font-size: 0.9rem;
        }

        /* 3. The Value (Big text in the middle) */
        [data-testid="stMetricValue"] {
            color: #FFFFFF !important;
            font-family: 'Roboto Mono', monospace;
            font-size: 1.8rem !important; /* Fixed font size for alignment */
        }

        /* 4. Center alignment fix */
        div[data-testid="column"] {
            text-align: center;
        }
        
        /* 5. Clean up top spacing */
        .block-container {
            padding-top: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

# --- DATA FETCHING ---
def get_raw_data():
    """Fetches the JSON directly from the raw GitHub URL"""
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
                except (ValueError, TypeError):
                    try:
                        dt = pd.to_datetime(raw_ts)
                        ts_val = dt.timestamp()
                    except Exception:
                        pass 

            return snapshot, ts_val

    except Exception:
        pass
    return None, None

def get_val(data, path, default=0):
    if not data: return default
    return data.get(path, default)

# --- MAIN UI ---

# 1. Title (No Refresh Button)
st.title("⚡ IPIDS Monitor")

# 2. Intelligent Data Fetching (Monotonic)
if "best_snapshot" not in st.session_state:
    st.session_state["best_snapshot"] = None
if "best_ts" not in st.session_state:
    st.session_state["best_ts"] = 0.0

fresh_snapshot, fresh_ts = get_raw_data()

# Update only if newer
if fresh_snapshot and fresh_ts:
    if fresh_ts >= st.session_state["best_ts"]:
        st.session_state["best_snapshot"] = fresh_snapshot
        st.session_state["best_ts"] = fresh_ts

raw_snapshot = st.session_state["best_snapshot"]
msg_timestamp = st.session_state["best_ts"]

# 3. Connection Logic (Wait screen)
if raw_snapshot is None:
    st.warning("📡 Connecting to GitHub...")
    time.sleep(2)
    st.rerun()

data = raw_snapshot.get("data", {})

# Calculate Freshness
age_seconds = time.time() - msg_timestamp if msg_timestamp else 0
is_stale = age_seconds > 80  # 80s threshold for "Slow" (since we upload every 60s)
is_offline = age_seconds > 300

# 4. Status Variables
fault_active = get_val(data, "system.general.systemFault", False)
state_code = get_val(data, "system.ionSource.general.status", 0)
state_map = {0: "OFF", 1: "STARTING", 2: "RUNNING", 99: "FAULT"}
sys_state = state_map.get(state_code, "UNKNOWN")

# 5. HEADER ROW (Unified Metrics)
c1, c2, c3 = st.columns([1, 2, 1])

# A. System State
c1.metric("System State", sys_state)

# B. Diagnostics (The "Banner" replacement)
# We combine Fault Status (Big Text) and Connection Status (Delta)
if fault_active:
    diag_value = "FAULT ACTIVE"
    diag_delta = "-CRITICAL ERROR"
    diag_color = "inverse" # Red
elif is_offline:
    diag_value = "OFFLINE"
    diag_delta = f"-Last seen {int(age_seconds)}s ago"
    diag_color = "inverse"
elif is_stale:
    diag_value = "SYSTEM NORMAL"
    diag_delta = f"!Slow Connection ({int(age_seconds)}s)"
    diag_color = "off" # Grey/Orange
else:
    diag_value = "SYSTEM NORMAL"
    diag_delta = "Online"
    diag_color = "normal" # Green

c2.metric("Diagnostics", diag_value, delta=diag_delta, delta_color=diag_color)

# C. Last Update
if msg_timestamp:
    pretty_time = datetime.datetime.fromtimestamp(msg_timestamp).strftime('%H:%M:%S')
else:
    pretty_time = "Unknown"
c3.metric("Last Update", pretty_time)

st.divider()

# --- METRICS GRID ---

# ROW 1
st.subheader("🚀 Primary Parameters")
r1c1, r1c2, r1c3, r1c4 = st.columns(4)

v_beam = get_val(data, "system.ionSource.general.beamVoltage", 0)
r1c1.metric("Beam Voltage", f"{v_beam:.2f} kV")

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
# Refresh faster if we are online (10s), slower if offline
refresh_rate = 10 if not is_offline else 30
time.sleep(refresh_rate)
st.rerun()
