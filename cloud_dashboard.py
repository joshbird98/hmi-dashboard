import streamlit as st
import requests
import pandas as pd
import time
import datetime

st.set_page_config(page_title="Ion Source Cloud", layout="wide")
st.title("☁️ Ion Source Remote Monitor")

# CONFIG: Must match the name in your Lab PC script
THING_NAME = "ipids-ion-source-monitor-v1"


def get_dweet_data():
    try:
        # Fetch the latest 'dweet' for our thing
        response = requests.get(f"https://dweet.io/get/latest/dweet/for/{THING_NAME}", timeout=2)
        if response.status_code == 200:
            content = response.json()
            # dweet structure: {"with": [ {"thing":..., "created":..., "content": {YOUR_DATA}} ]}
            if "with" in content and len(content["with"]) > 0:
                item = content["with"][0]
                return item["content"], item["created"]
    except Exception:
        return None, None
    return None, None


# --- MAIN LOOP ---
# Streamlit Cloud handles auto-refresh differently than local
if st.button('Refresh Data'):
    st.rerun()

# Auto-refresh logic (Experimental for cloud)
time.sleep(1)  # Add a small delay to prevent rapid-fire reloading
st.empty()  # Placeholder

data, timestamp = get_dweet_data()

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
