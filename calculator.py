import pandas as pd
import numpy as np

def calculate_cagr(total_investment, current_value, start_date, end_date):
    """Calculates the Compound Annual Growth Rate for a lumpsum investment."""
    if total_investment == 0:
        return 0
    start_ts = pd.to_datetime(start_date)
    end_ts = pd.to_datetime(end_date)
    investment_duration_years = (end_ts - start_ts).days / 365.25
    if investment_duration_years <= 0:
        return 0
    return ((current_value / total_investment) ** (1 / investment_duration_years) - 1) * 100

def xirr_func(rate, cashflows):
    """The XIRR equation. Used by the numerical solver."""
    return sum([cf['value'] / ((1 + rate) ** ((cf['date'] - cashflows[0]['date']).days / 365.0)) for cf in cashflows])

def calculate_xirr(cashflows, guess=0.1, max_iter=100, tol=1e-6):
    """Calculates XIRR using a numerical bisection method."""
    if not cashflows or len(cashflows) < 2:
        return 0.0

    low_rate, high_rate = -0.99, 5.0  # -99% to 500%
    try:
        f_low = xirr_func(low_rate, cashflows)
        f_high = xirr_func(high_rate, cashflows)
        if f_low * f_high > 0:
            return 0.0  # No solution in the bracket

        for _ in range(max_iter):
            mid_rate = (low_rate + high_rate) / 2
            if abs(high_rate - low_rate) < tol:
                return mid_rate * 100
            f_mid = xirr_func(mid_rate, cashflows)
            if np.sign(f_mid) == np.sign(f_low):
                low_rate = mid_rate
                f_low = f_mid
            else:
                high_rate = mid_rate
        return mid_rate * 100
    except (ValueError, ZeroDivisionError):
        return 0.0

def calculate_sip_returns(selected_codes, selected_names, start_date, end_date, monthly_investment, get_historical_nav):
    all_results = []
    portfolio_chart_data = pd.DataFrame()
    portfolio_cashflows = []

    investment_dates = pd.date_range(start=start_date, end=end_date, freq='MS')

    for scheme_code, scheme_name in zip(selected_codes, selected_names):
        hist_data = get_historical_nav(scheme_code)
        if hist_data.empty: continue

        # --- Robustness Fix: Clean data first ---
        hist_data['nav'] = pd.to_numeric(hist_data['nav'], errors='coerce')
        hist_data.dropna(subset=['nav'], inplace=True)

        trade_data = hist_data[(hist_data.index >= pd.to_datetime(start_date)) & (hist_data.index <= pd.to_datetime(end_date))]
        if trade_data.empty: continue

        scheme_cashflows = []
        total_units, total_invested = 0, 0

        for inv_date in investment_dates:
            try:
                nav_on_date = trade_data.asof(inv_date)['nav']
                # --- Robustness Fix: Check for valid NAV ---
                if pd.notna(nav_on_date) and nav_on_date > 0:
                    units_bought = monthly_investment / nav_on_date
                    total_units += units_bought
                    total_invested += monthly_investment
                    scheme_cashflows.append({'date': inv_date, 'value': -monthly_investment})
            except (TypeError, KeyError, IndexError):
                continue
        
        if total_invested == 0: continue

        # --- Robustness Fix: Find last valid NAV ---
        last_valid_nav_row = trade_data.iloc[-1]
        latest_nav = last_valid_nav_row['nav']
        final_value = total_units * latest_nav

        # --- Robustness Fix: Final check ---
        if pd.isna(final_value):
            continue

        scheme_cashflows.append({'date': last_valid_nav_row.name, 'value': final_value})
        
        portfolio_cashflows.extend(scheme_cashflows)

        xirr = calculate_xirr(scheme_cashflows)
        abs_return_pct = ((final_value - total_invested) / total_invested) * 100 if total_invested > 0 else 0

        all_results.append({
            "Scheme Name": scheme_name,
            "Total Investment": f"₹{total_invested:,.2f}",
            "Current Value": f"₹{final_value:,.2f}",
            "Total Gain/Loss": f"₹{final_value - total_invested:,.2f}",
            "Absolute Return (%)": f"{abs_return_pct:.2f}%",
            "Annualized Return (XIRR %)": f"{xirr:.2f}%"
        })
        portfolio_chart_data = pd.concat([portfolio_chart_data, trade_data['nav'].rename(scheme_name)], axis=1)

    return all_results, portfolio_chart_data, portfolio_cashflows

def calculate_lumpsum_returns(selected_codes, selected_names, start_date, end_date, lumpsum_investment, get_historical_nav):
    all_results = []
    portfolio_chart_data = pd.DataFrame()
    total_portfolio_investment = 0
    total_portfolio_final_value = 0

    for scheme_code, scheme_name in zip(selected_codes, selected_names):
        hist_data = get_historical_nav(scheme_code)
        if hist_data.empty: continue

        trade_data = hist_data[(hist_data.index >= pd.to_datetime(start_date)) & (hist_data.index <= pd.to_datetime(end_date))]
        if trade_data.empty: continue

        try:
            start_record = trade_data.iloc[0]
            start_nav = start_record['nav']
            actual_start_date = start_record.name
            end_record = trade_data.iloc[-1]
            end_nav = end_record['nav']
            actual_end_date = end_record.name
        except (TypeError, KeyError, IndexError):
            continue

        total_invested = lumpsum_investment
        units_bought = total_invested / start_nav
        final_value = units_bought * end_nav
        total_portfolio_investment += total_invested
        total_portfolio_final_value += final_value

        cagr = calculate_cagr(total_invested, final_value, actual_start_date, actual_end_date)
        abs_return_pct = ((final_value - total_invested) / total_invested) * 100 if total_invested > 0 else 0

        all_results.append({
            "Scheme Name": scheme_name,
            "Total Investment": f"₹{total_invested:,.2f}",
            "Current Value": f"₹{final_value:,.2f}",
            "Total Gain/Loss": f"₹{final_value - total_invested:,.2f}",
            "Absolute Return (%)": f"{abs_return_pct:.2f}%",
            "CAGR (%)": f"{cagr:.2f}%"
        })
        portfolio_chart_data = pd.concat([portfolio_chart_data, trade_data['nav'].rename(scheme_name)], axis=1)

    return all_results, portfolio_chart_data, total_portfolio_investment, total_portfolio_final_value