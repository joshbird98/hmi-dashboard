import streamlit as st
import requests
import pandas as pd
import time
import json
import datetime

# --- CONFIGURATION ---
# This must match the topic you use in your Lab PC Python script
# e.g. requests.post("https://ntfy.sh/ipids-ion-monitor", ...)
TOPIC_NAME = "ibc-ipids-monitor"

st.set_page_config(page_title="Ion Source Cloud", layout="wide")
st.title("☁️ Ion Source Remote Monitor (ntfy)")


def get_ntfy_data():
    try:
        # Fetch history: Get the last 1 message immediately
        # poll=1 waits for new data, but since=all&limit=1 gets the saved data instantly
        url = f"https://ntfy.sh/{TOPIC_NAME}/json?since=all&limit=1"

        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            # The response is a stream of JSON lines (NDJSON)
            # We just want the first valid message line
            for line in response.iter_lines():
                if line:
                    data_obj = json.loads(line)
                    if data_obj.get('event') == 'message':
                        # The actual data snapshot is stored as a string inside 'message'
                        payload = data_obj.get('message', '{}')

                        # Convert that string back into a Python Dictionary
                        snapshot = json.loads(payload)

                        # Timestamp is Unix epoch
                        timestamp = data_obj.get('time')
                        return snapshot, timestamp
    except Exception as e:
        # print(e) # For debugging locally
        pass

    return None, None


# --- MAIN LOOP ---
if st.button('Refresh Data'):
    st.rerun()

# Auto-refresh placeholder
time.sleep(1)
st.empty()

data, timestamp = get_ntfy_data()

if data is None:
    st.warning(f"Waiting for data on topic: {TOPIC_NAME}...")
    st.info("Check that your Lab PC is running and sending data to ntfy.sh")
else:
    # 1. Calculate Age
    if timestamp:
        msg_time = datetime.datetime.fromtimestamp(timestamp)
        age_seconds = time.time() - timestamp

        # Display Time
        t_str = msg_time.strftime('%H:%M:%S')

        if age_seconds > 60:
            st.error(f"⚠️ Data is Stale! Last update: {t_str} ({int(age_seconds)}s ago)")
        else:
            st.success(f"🟢 Online. Last update: {t_str}")

    # 2. Key Metrics
    k1, k2, k3, k4 = st.columns(4)

    # Use .get() to safely access tags. Default to 0 if missing.
    volts = data.get("ionSource.general.beamVoltage", 0)
    k1.metric("Beam Voltage", f"{volts:.1f} kV")

    # Scientific notation for pressure
    press = data.get("system.vacuumSystem.gauges.source.readback_mB", 0)
    k2.metric("Source Pressure", f"{press:.1e} mbar")

    mag = data.get("beamline.magnet.readbackA", 0)
    k3.metric("Magnet", f"{mag:.2f} A")

    status = data.get("system.ionSource.general.status", 0)
    status_map = {0: "OFF", 1: "STARTING", 2: "RUNNING", 99: "FAULT"}
    k4.metric("State", status_map.get(status, f"Code {status}"))

    # 3. Full Data Table
    st.divider()
    # Convert dict to table
    df = pd.DataFrame(list(data.items()), columns=["Tag Name", "Value"])

    # Optional: Format floats in the table to look nicer
    # (This assumes values are numbers, handles errors if they are strings)
    # df['Value'] = df['Value'].apply(lambda x: f"{x:.4g}" if isinstance(x, (int, float)) else x)

    st.dataframe(df, use_container_width=True, height=500)

# Cloud Auto-Reload
time.sleep(2)
st.rerun()
