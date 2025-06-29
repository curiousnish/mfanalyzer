
import pandas as pd

def calculate_sip_returns(selected_codes, selected_names, start_date, end_date, monthly_investment, get_historical_nav):
    all_results = []
    portfolio_chart_data = pd.DataFrame()
    
    total_portfolio_investment = 0
    total_portfolio_final_value = 0

    investment_dates = pd.date_range(start=start_date, end=end_date, freq='MS')

    for scheme_code, scheme_name in zip(selected_codes, selected_names):
        hist_data = get_historical_nav(scheme_code)
        
        if hist_data.empty:
            continue

        total_units = 0
        total_invested = 0
        
        trade_data = hist_data[(hist_data.index >= pd.to_datetime(start_date)) & (hist_data.index <= pd.to_datetime(end_date))]

        if trade_data.empty:
            continue

        for inv_date in investment_dates:
            try:
                nav_on_date = trade_data.asof(inv_date)['nav']
                units_bought = monthly_investment / nav_on_date
                total_units += units_bought
                total_invested += monthly_investment
            except (TypeError, KeyError, IndexError):
                continue
        
        if total_invested == 0:
            continue

        latest_nav = trade_data.iloc[-1]['nav']
        final_value = total_units * latest_nav

        total_portfolio_investment += total_invested
        total_portfolio_final_value += final_value

        abs_return = final_value - total_invested
        pct_return = (abs_return / total_invested) * 100 if total_invested > 0 else 0
        
        all_results.append({
            "Scheme Name": scheme_name,
            "Invested Capital": f"₹{total_invested:,.2f}",
            "Final Capital": f"₹{final_value:,.2f}",
            "Absolute Return": f"₹{abs_return:,.2f}",
            "Percentage Return (%)": f"{pct_return:.2f}%"
        })

        chart_series = trade_data['nav'].rename(scheme_name)
        portfolio_chart_data = pd.concat([portfolio_chart_data, chart_series], axis=1)

    return all_results, portfolio_chart_data, total_portfolio_investment, total_portfolio_final_value
