import streamlit as st
import requests
import pandas as pd
import time
import datetime

# --- CONFIGURATION ---
# PASTE YOUR CLEANED RAW URL HERE (The one without the long hash!)
RAW_URL = "https://gist.githubusercontent.com/joshbird98/9de20220c7cd1e3c359c22b4775faa46/raw/status.json"

st.set_page_config(page_title="IPIDS Monitor", layout="wide")
st.title("☁️ Ion Source Gist Monitor")

# Function to fetch data
def get_gist_data():
    try:
        # We add a random number to the URL to prevent Streamlit from 
        # caching the old data (Cache busting)
        nocache_url = f"{RAW_URL}?t={time.time()}"
        
        response = requests.get(nocache_url, timeout=5)
        
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None

# --- MAIN LOOP ---
if st.button('Refresh Now'):
    st.rerun()

# Auto-refresh placeholder
time.sleep(1) 
st.empty() 

data = get_gist_data()

if data is None or "status" in data and data["status"] == "waiting":
    st.warning("Waiting for Lab PC connection...")
    st.info(f"Checking URL: {RAW_URL}")
else:
    # GitHub doesn't give us a timestamp in the raw file, 
    # so we assume "Live" means "Just fetched now".
    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    st.success(f"Data Received at {current_time}")

    # --- METRICS ---
    k1, k2, k3, k4 = st.columns(4)
    
    # Use .get() to safely access tags
    volts = data.get("ionSource.general.beamVoltage", 0)
    k1.metric("Beam Voltage", f"{volts:.1f} kV")
    
    press = data.get("system.vacuumSystem.gauges.source.readback_mB", 0)
    k2.metric("Source Pressure", f"{press:.1e} mbar")
    
    mag = data.get("beamline.magnet.readbackA", 0)
    k3.metric("Magnet", f"{mag:.2f} A")

    status = data.get("system.ionSource.general.status", 0)
    status_map = {0: "OFF", 1: "STARTING", 2: "RUNNING", 99: "FAULT"}
    k4.metric("State", status_map.get(status, status))

    # --- TABLE ---
    st.divider()
    df = pd.DataFrame(list(data.items()), columns=["Tag Name", "Value"])
    st.dataframe(df, use_container_width=True, height=500)

# Refresh every 5 seconds (GitHub rate limits are generous but not infinite)
time.sleep(5)
st.rerun()
