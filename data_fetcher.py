
import streamlit as st
import pandas as pd
import requests

@st.cache_data(ttl=3600)  # Cache the list of schemes for 1 hour
def get_scheme_list():
    """
    Fetches the list of all mutual fund schemes from the AMFI website.
    This is used to populate the dropdown for scheme selection.
    """
    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.text.splitlines()
        
        schemes = []
        for line in data:
            if ";" in line and len(line.split(';')) == 6:
                parts = line.split(';')
                # Create a unique identifier for the dropdown
                scheme_name = f"{parts[3].strip()} ({parts[0].strip()})"
                schemes.append({
                    "code": parts[0].strip(),
                    "name": parts[3].strip(),
                    "display_name": scheme_name
                })
        
        if not schemes:
            st.error("Could not parse any schemes from the AMFI file.")
            return pd.DataFrame()
            
        return pd.DataFrame(schemes)

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching scheme list from AMFI: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600) # Cache historical data for 1 hour
def get_historical_nav(scheme_code):
    """
    Fetches historical NAV data for a specific scheme using the MFAPI.
    """
    url = f"https://api.mfapi.in/mf/{scheme_code}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()["data"]
        
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')
        df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
        df = df.set_index('date').sort_index()
        return df

    except (requests.exceptions.RequestException, KeyError, ValueError) as e:
        st.warning(f"Could not fetch or parse historical data for scheme {scheme_code}. It might be a new fund or the API is unavailable.")
        return pd.DataFrame()
