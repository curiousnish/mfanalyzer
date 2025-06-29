
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from data_fetcher import get_scheme_list, get_historical_nav
from calculator import calculate_sip_returns

# --- Streamlit App ---
st.set_page_config(layout="wide", page_title="Mutual Fund SIP Analyzer")

st.title("Mutual Fund SIP Return Analyzer")
st.markdown("Analyze the historical performance of your Systematic Investment Plan (SIP) in Indian mutual funds.")

# Fetch the list of schemes
scheme_df = get_scheme_list()

if not scheme_df.empty:
    # --- Sidebar for User Inputs ---
    st.sidebar.header("Investment Parameters")

    all_schemes_display = sorted(scheme_df['display_name'].unique())
    
    selected_schemes_display = st.sidebar.multiselect(
        "Select Mutual Fund Schemes",
        options=all_schemes_display,
        default=[]
    )

    today = datetime.today()
    default_start = today - timedelta(days=3*365) # 3 years ago
    default_end = today

    start_date = st.sidebar.date_input("Start Date", value=default_start)
    end_date = st.sidebar.date_input("End Date", value=default_end)

    monthly_investment = st.sidebar.number_input(
        "Monthly SIP Amount (per scheme)",
        min_value=500,
        value=5000,
        step=500
    )

    if st.sidebar.button("Analyze Returns"):
        if not selected_schemes_display:
            st.warning("Please select at least one mutual fund scheme.")
        elif start_date >= end_date:
            st.warning("The Start Date must be before the End Date.")
        else:
            selected_codes = scheme_df[scheme_df['display_name'].isin(selected_schemes_display)]['code'].tolist()
            selected_names = scheme_df[scheme_df['display_name'].isin(selected_schemes_display)]['name'].tolist()
            
            with st.spinner("Fetching historical data and calculating returns... This may take a moment."):
                all_results, portfolio_chart_data, total_portfolio_investment, total_portfolio_final_value = calculate_sip_returns(
                    selected_codes, selected_names, start_date, end_date, monthly_investment, get_historical_nav
                )

                if not all_results:
                    st.error("Could not calculate returns. Please check the selected schemes and date range.")
                else:
                    st.subheader("Overall Portfolio Performance")
                    
                    overall_abs_return = total_portfolio_final_value - total_portfolio_investment
                    overall_pct_return = (overall_abs_return / total_portfolio_investment) * 100 if total_portfolio_investment > 0 else 0

                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Total Invested Capital", f"₹{total_portfolio_investment:,.2f}")
                    col2.metric("Total Final Capital", f"₹{total_portfolio_final_value:,.2f}")
                    col3.metric("Absolute Return", f"₹{overall_abs_return:,.2f}", delta=f"{overall_pct_return:.2f}%")
                    col4.metric("Percentage Return", f"{overall_pct_return:.2f}%")

                    st.divider()

                    st.subheader("Scheme-wise Performance")
                    results_df = pd.DataFrame(all_results)
                    st.dataframe(results_df, use_container_width=True, hide_index=True)

                    if not portfolio_chart_data.empty:
                        st.subheader("Fund NAV Growth Over Time")
                        normalized_chart_data = (portfolio_chart_data.ffill() / portfolio_chart_data.ffill().iloc[0]) * 100
                        st.line_chart(normalized_chart_data, use_container_width=True)
                        st.caption("The chart shows the normalized growth of each fund's NAV, assuming a starting value of 100. This helps compare the performance of different funds irrespective of their actual NAV values.")

else:
    st.error("Failed to load the list of mutual funds from AMFI. The application cannot proceed. Please try again later.")

st.sidebar.info(
    "This app uses data from AMFI and the free MFAPI.in service. "
    "Always verify data with official sources before making financial decisions."
)
