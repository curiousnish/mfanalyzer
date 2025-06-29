import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- Data Fetching Functions ---

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

# --- Streamlit App ---
st.set_page_config(layout="wide", page_title="Mutual Fund SIP Analyzer")

st.title("Mutual Fund SIP Return Analyzer")
st.markdown("Analyze the historical performance of your Systematic Investment Plan (SIP) in Indian mutual funds.")

# Fetch the list of schemes
scheme_df = get_scheme_list()

if not scheme_df.empty:
    # --- Sidebar for User Inputs ---
    st.sidebar.header("Investment Parameters")

    # Use the display_name for the multiselect options
    all_schemes_display = sorted(scheme_df['display_name'].unique())
    
    selected_schemes_display = st.sidebar.multiselect(
        "Select Mutual Fund Schemes",
        options=all_schemes_display,
        default=[]
    )

    # Date range selection
    # Set reasonable defaults for date inputs
    today = datetime.today()
    default_start = today - timedelta(days=3*365) # 3 years ago
    default_end = today

    start_date = st.sidebar.date_input("Start Date", value=default_start)
    end_date = st.sidebar.date_input("End Date", value=default_end)

    # Monthly investment amount
    monthly_investment = st.sidebar.number_input(
        "Monthly SIP Amount (per scheme)",
        min_value=500,
        value=5000,
        step=500
    )

    # --- Main Panel for Results ---
    if st.sidebar.button("Analyze Returns"):
        if not selected_schemes_display:
            st.warning("Please select at least one mutual fund scheme.")
        elif start_date >= end_date:
            st.warning("The Start Date must be before the End Date.")
        else:
            # Get the corresponding scheme codes for the selected display names
            selected_codes = scheme_df[scheme_df['display_name'].isin(selected_schemes_display)]['code'].tolist()
            selected_names = scheme_df[scheme_df['display_name'].isin(selected_schemes_display)]['name'].tolist()
            
            with st.spinner("Fetching historical data and calculating returns... This may take a moment."):
                
                all_results = []
                portfolio_chart_data = pd.DataFrame()
                
                total_portfolio_investment = 0
                total_portfolio_final_value = 0

                # Generate a date range for monthly investments
                investment_dates = pd.date_range(start=start_date, end=end_date, freq='MS')

                for scheme_code, scheme_name in zip(selected_codes, selected_names):
                    hist_data = get_historical_nav(scheme_code)
                    
                    if hist_data.empty:
                        st.warning(f"No historical data found for '{scheme_name}'. Skipping.")
                        continue

                    total_units = 0
                    total_invested = 0
                    
                    # Filter historical data for the selected date range
                    trade_data = hist_data[(hist_data.index >= pd.to_datetime(start_date)) & (hist_data.index <= pd.to_datetime(end_date))]

                    if trade_data.empty:
                        st.warning(f"No NAV data available for '{scheme_name}' in the selected date range. It may be a newer fund.")
                        continue

                    for inv_date in investment_dates:
                        # Find the closest available NAV date for the investment
                        try:
                            nav_on_date = trade_data.asof(inv_date)['nav']
                            units_bought = monthly_investment / nav_on_date
                            total_units += units_bought
                            total_invested += monthly_investment
                        except (TypeError, KeyError, IndexError):
                            # This can happen if the fund didn't exist for part of the early date range
                            continue
                    
                    if total_invested == 0:
                        continue # Skip if no investments were made

                    # Calculate final value using the last available NAV
                    latest_nav = trade_data.iloc[-1]['nav']
                    final_value = total_units * latest_nav

                    # Update portfolio totals
                    total_portfolio_investment += total_invested
                    total_portfolio_final_value += final_value

                    # Calculate returns for the individual scheme
                    abs_return = final_value - total_invested
                    pct_return = (abs_return / total_invested) * 100 if total_invested > 0 else 0
                    
                    all_results.append({
                        "Scheme Name": scheme_name,
                        "Invested Capital": f"₹{total_invested:,.2f}",
                        "Final Capital": f"₹{final_value:,.2f}",
                        "Absolute Return": f"₹{abs_return:,.2f}",
                        "Percentage Return (%)": f"{pct_return:.2f}%"
                    })

                    # For the chart, we'll just use the NAVs within the range
                    chart_series = trade_data['nav'].rename(scheme_name)
                    portfolio_chart_data = pd.concat([portfolio_chart_data, chart_series], axis=1)

                if not all_results:
                    st.error("Could not calculate returns. Please check the selected schemes and date range.")
                else:
                    # --- Display Overall Metrics ---
                    st.subheader("Overall Portfolio Performance")
                    
                    overall_abs_return = total_portfolio_final_value - total_portfolio_investment
                    overall_pct_return = (overall_abs_return / total_portfolio_investment) * 100 if total_portfolio_investment > 0 else 0

                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Total Invested Capital", f"₹{total_portfolio_investment:,.2f}")
                    col2.metric("Total Final Capital", f"₹{total_portfolio_final_value:,.2f}")
                    col3.metric("Absolute Return", f"₹{overall_abs_return:,.2f}", delta=f"{overall_pct_return:.2f}%")
                    col4.metric("Percentage Return", f"{overall_pct_return:.2f}%")

                    st.divider()

                    # --- Display Detailed Results Table ---
                    st.subheader("Scheme-wise Performance")
                    results_df = pd.DataFrame(all_results)
                    st.dataframe(results_df, use_container_width=True, hide_index=True)

                    # --- Display Investment Growth Chart ---
                    if not portfolio_chart_data.empty:
                        st.subheader("Fund NAV Growth Over Time")
                        # Normalize NAVs to compare performance from a common starting point
                        normalized_chart_data = (portfolio_chart_data.ffill() / portfolio_chart_data.ffill().iloc[0]) * 100
                        st.line_chart(normalized_chart_data, use_container_width=True)
                        st.caption("The chart shows the normalized growth of each fund's NAV, assuming a starting value of 100. This helps compare the performance of different funds irrespective of their actual NAV values.")

else:
    st.error("Failed to load the list of mutual funds from AMFI. The application cannot proceed. Please try again later.")

st.sidebar.info(
    "This app uses data from AMFI and the free MFAPI.in service. "
    "Always verify data with official sources before making financial decisions."
)