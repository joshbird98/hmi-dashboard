import streamlit as st
import requests
import pandas as pd
import time
import datetime
import json

st.set_page_config(page_title="Ion Source Cloud", layout="wide")
st.title("☁️ Ion Source Remote Monitor")

# CONFIG: Must match the name in your Lab PC script
THING_NAME = "ibc-ipids-monitor"


def get_ntfy_data():
    try:
        # Fetch the last 1 message from the topic
        resp = requests.get(f"https://ntfy.sh/{THING_NAME}/json?poll=1", timeout=2)
        for line in resp.iter_lines():
            if line:
                data = json.loads(line)
                if data['event'] == 'message':
                     # ntfy stores the JSON string inside the 'message' field
                    return json.loads(data['message']), data['time']
    except Exception:
        return None, None


# --- MAIN LOOP ---
# Streamlit Cloud handles auto-refresh differently than local
if st.button('Refresh Data'):
    st.rerun()

# Auto-refresh logic (Experimental for cloud)
time.sleep(1)  # Add a small delay to prevent rapid-fire reloading
st.empty()  # Placeholder

data, timestamp = get_ntfy_data()

if data is None:
    st.warning("Waiting for data stream...")
else:
    # Calculate Age
    # dweet timestamp is usually ISO string, but we can just use "Time since update"
    # For simplicity, we just show the received values

    st.success(f"Data Received. Cloud Timestamp: {timestamp}")

    # --- YOUR DASHBOARD UI HERE ---
    k1, k2, k3 = st.columns(3)

    # Example Tags
    volts = data.get("ionSource.general.beamVoltage", 0)
    k1.metric("Beam Voltage", f"{volts} kV")

    press = data.get("system.vacuumSystem.gauges.source.readback_mB", 0)
    k2.metric("Pressure", f"{press:.1e} mbar")

    status = data.get("system.ionSource.general.status", 0)
    k3.metric("Status", status)

    st.divider()
    df = pd.DataFrame(list(data.items()), columns=["Tag", "Value"])
    st.dataframe(df, use_container_width=True)

# Force a reload every 2 seconds
time.sleep(2)
st.rerun()
