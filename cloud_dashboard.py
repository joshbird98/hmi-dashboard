import streamlit as st
import requests
import time
import json
import datetime
import pandas as pd

# --- CONFIGURATION ---
RAW_URL = "https://gist.githubusercontent.com/joshbird98/9de20220c7cd1e3c359c22b4775faa46/raw/status.json"
REFRESH_INTERVAL = 30  # Seconds for auto-refresh

st.set_page_config(
    page_title="IPIDS Monitor",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS STYLING ---
# Custom CSS to make metrics pop and reduce wasted whitespace
st.markdown("""
    <style>
        .stMetric {
            background-color: #0E1117;
            border: 1px solid #303030;
            padding: 15px;
            border-radius: 5px;
        }
        div[data-testid="column"] {
            text-align: center;
        }
        .block-container {
            padding-top: 2rem;
        }
    </style>
""", unsafe_allow_html=True)


# --- DATA FETCHING ---
def get_raw_data():
    """Fetches the JSON directly from the raw GitHub URL"""
    try:
        # Add a timestamp query param to bypass GitHub's CDN cache
        # This ensures we get the FRESH file every time.
        cache_buster = f"?t={int(time.time())}"
        final_url = RAW_URL + cache_buster

        response = requests.get(final_url, timeout=5)

        if response.status_code == 200:
            snapshot = response.json()

            # Extract timestamp
            # It might be a float (Unix) or String (ISO)
            raw_ts = snapshot.get('timestamp')

            # Helper to parse timestamp into a usable float
            ts_val = None
            if raw_ts:
                try:
                    ts_val = float(raw_ts)
                except ValueError:
                    try:
                        # Parse ISO string "2026-01-17T..."
                        # Handle potential fractional seconds
                        clean_ts = raw_ts.replace("Z", "")
                        dt = datetime.datetime.fromisoformat(clean_ts)
                        ts_val = dt.timestamp()
                    except ValueError:
                        pass  # Keep as None if failed

            return snapshot, ts_val

    except Exception as e:
        # print(f"Fetch Error: {e}")
        pass
    return None, None


def get_val(data, path, default=0):
    """Helper to safely extract nested keys or return default"""
    if not data:
        return default
    # The log file structure is flat: "data": {"key.subkey": val}
    # So we just look up the string key directly.
    return data.get(path, default)


# --- MAIN UI ---

# 1. Header & Controls
col_title, col_btn = st.columns([6, 1])
with col_title:
    st.title("⚡ IPIDS Remote Dashboard")
with col_btn:
    if st.button('🔄 Refresh'):
        st.rerun()

# 2. Fetch Data
raw_snapshot, msg_timestamp = get_raw_data()

# 3. Connection Logic
if raw_snapshot is None:
    st.warning("📡 Connecting to GitHub...")
    st.info(f"Target: {RAW_URL}")
    time.sleep(2)
    st.rerun()

# Extract the 'data' dictionary from the snapshot
data = raw_snapshot.get("data", {})

# Calculate "Freshness"
age_seconds = 0
status_color = "green"
status_msg = "ONLINE"

if msg_timestamp:
    age_seconds = time.time() - msg_timestamp
    if age_seconds > 120:  # 2 minutes considered stale
        status_color = "red"
        status_msg = "OFFLINE / STALE"
    elif age_seconds > 30:
        status_color = "orange"
        status_msg = "SLOW CONNECTION"

# 4. Status Banner
fault_active = get_val(data, "system.general.systemFault", False)
state_code = get_val(data, "system.ionSource.general.status", 0)
state_map = {0: "OFF", 1: "STARTING", 2: "RUNNING", 99: "FAULT"}
sys_state = state_map.get(state_code, "UNKNOWN")

# Banner Container
with st.container():
    c1, c2, c3 = st.columns([1, 2, 1])

    # System State Box
    c1.metric("System State", sys_state)

    # Large Banner
    if fault_active:
        c2.error(f"⚠️ SYSTEM FAULT ACTIVE ({status_msg})")
    elif status_color == "green":
        c2.success(f"🟢 SYSTEM NORMAL ({status_msg})")
    else:
        c2.warning(f"🟠 {status_msg} (Last saw {int(age_seconds)}s ago)")

    # Timestamp
    try:
        # Parse the ISO timestamp from the log if possible
        pretty_time = datetime.datetime.fromtimestamp(msg_timestamp).strftime('%H:%M:%S')
    except:
        pretty_time = "Unknown"
    c3.metric("Last Update", pretty_time)

st.divider()

# --- KEY METRICS LAYOUT ---

# ROW 1: The "Big Three" (Voltage, Pressure, Beam)
st.subheader("🚀 Primary Parameters")
r1c1, r1c2, r1c3, r1c4 = st.columns(4)

v_beam = get_val(data, "system.ionSource.general.beamVoltage", 0)
r1c1.metric("Beam Voltage", f"{v_beam:.2f} kV")

p_source = get_val(data, "system.vacuumSystem.gauges.source.readback_mB", 0)
r1c2.metric("Source Pressure", f"{p_source:.1e} mbar")

# Check which cup is active or sum them
cup_current = get_val(data, "beamline.drop_in_cup.measured_current_A", 0)
if cup_current == 0:
    cup_current = get_val(data, "beamline.straight_thru_cup.measured_current_A", 0)
    label = "Beam Current (Straight)"
else:
    label = "Beam Current (Cup)"
r1c3.metric(label, f"{cup_current * 1e6:.1f} µA")  # Display in micro-amps

# Magnet
v_mag = get_val(data, "beamline.magnet.readbackA", 0)
r1c4.metric("Magnet Current", f"{v_mag:.2f} A")

# ROW 2: Ion Source Internals
st.subheader("⚛️ Ion Source Control")
r2c1, r2c2, r2c3, r2c4 = st.columns(4)

fil_a = get_val(data, "system.ionSource.ioniser.filament.readbackA", 0)
r2c1.metric("Filament", f"{fil_a:.2f} A")

# Power is nicer to see than volts sometimes for ionisers
ion_w = get_val(data, "system.ionSource.ioniser.readbackW", 0)
r2c2.metric("Ioniser Power", f"{ion_w:.1f} W")

ext_v = get_val(data, "system.ionSource.extraction.readbackV", 0)
r2c3.metric("Extraction", f"{ext_v:.1f} V")

# Cesium or Thermionic depending on what is non-zero?
cs_temp = get_val(data, "system.ionSource.cesium.readbackC", 0)
r2c4.metric("Cesium Temp", f"{cs_temp:.1f} °C")

# ROW 3: Vacuum & Mechanical
st.subheader("💨 Vacuum & Cooling")
r3c1, r3c2, r3c3, r3c4 = st.columns(4)

turbo_spd = get_val(data, "system.vacuumSystem.pumps.turbo.source_1.speed", 0)
r3c1.metric("Turbo Speed", f"{turbo_spd:.0f} Hz")

coolant = get_val(data, "system.general.coolantStatus", False)
r3c2.metric("Coolant Flow", "OK" if coolant else "LOW", delta_color="normal" if coolant else "inverse")

gate_val = get_val(data, "system.vacuumSystem.valves.gate.open", False)
r3c3.metric("Gate Valve", "OPEN" if gate_val else "CLOSED")

# Placeholder for sample stage or other
stage_z = get_val(data, "endstation.stage.motion.readback_z_mm", 0)
r3c4.metric("Stage Z", f"{stage_z:.1f} mm")

# --- DEBUG / RAW DATA TOGGLE ---
st.divider()
with st.expander("🛠️ View Raw Telemetry Data"):
    # Filter out the boring 'false' fault arrays to make the table readable
    filtered_data = {k: v for k, v in data.items() if "faultArray" not in k and "messageBuffer" not in k}
    df = pd.DataFrame(list(filtered_data.items()), columns=["Tag", "Value"])
    st.dataframe(df, use_container_width=True)

# Auto-reload logic
time.sleep(1)
st.empty()  # Placeholder clearing
if age_seconds < 600:  # Only auto-rerun if the page is somewhat active
    time.sleep(2)
    st.rerun()
