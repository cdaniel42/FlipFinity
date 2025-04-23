"""
File: streamlit_app.py
Description: Streamlit application for the FlipFinity Business Simulator.
Provides a web interface to input parameters, run simulations, and view results.
"""

import streamlit as st
import pandas as pd
import numpy as np # Needed for linear interpolation

# Import core logic
from simulation import run_monte_carlo_simulations
from visualization import plot_asset_growth, plot_accumulated_profit, plot_monthly_revenue

st.set_page_config(layout="wide", initial_sidebar_state="expanded") # Use wide layout & expanded sidebar

st.title("FlipFinity Business Simulator")

st.sidebar.header("Simulation Parameters")

# --- Run Button (Top) ---
run_button = st.sidebar.button("Run Simulation", key='run_sim_button_top')

# --- Display Calculated Values (Below Button) ---
st.sidebar.subheader("Calculated Totals per Project")
# Access widget values using session state, providing the correct widget default as the fallback
sqm_buy_value_ke_disp = st.session_state.get('disp_buy_val', 2.0) # Default from widget
sqm_sell_value_ke_disp = st.session_state.get('disp_sell_val', 3.0) # Default from widget
total_sqm_disp = st.session_state.get('disp_sqm_val', 100.0) # Default from widget
renovation_cost_per_sqm_eur_disp = st.session_state.get('disp_reno_val', 500.0) # Default from widget
land_transfer_tax_percent_disp = st.session_state.get('disp_land_tax', 6.5) # Default from widget
notary_fee_percent_disp = st.session_state.get('disp_notary', 1.5) # Default from widget
agent_fee_purchase_percent_disp = st.session_state.get('disp_agent_buy', 3.57) # Default from widget
agent_fee_sale_percent_disp = st.session_state.get('disp_agent_sell', 3.57) # Default from widget
TAX_RATE_FIXED = 29.0

# Perform calculations directly using the retrieved/default values
# Add basic type/value checks before calculation to avoid errors
all_vars_valid = True
inputs_for_calc = {
    'sqm_buy_value_ke': sqm_buy_value_ke_disp,
    'sqm_sell_value_ke': sqm_sell_value_ke_disp,
    'total_sqm': total_sqm_disp,
    'renovation_cost_per_sqm_eur': renovation_cost_per_sqm_eur_disp,
    'land_transfer_tax_percent': land_transfer_tax_percent_disp,
    'notary_fee_percent': notary_fee_percent_disp,
    'agent_fee_purchase_percent': agent_fee_purchase_percent_disp,
    'agent_fee_sale_percent': agent_fee_sale_percent_disp
}

for key, val in inputs_for_calc.items():
    if not isinstance(val, (int, float)):
        all_vars_valid = False
        break
# Specific value checks
if all_vars_valid and (inputs_for_calc['total_sqm'] <= 0 or inputs_for_calc['sqm_buy_value_ke'] <= 0):
    all_vars_valid = False

if all_vars_valid:
    # Calculations using validated values
    buy_value_ke = inputs_for_calc['sqm_buy_value_ke'] * inputs_for_calc['total_sqm']
    sell_value_ke = inputs_for_calc['sqm_sell_value_ke'] * inputs_for_calc['total_sqm']
    reno_cost_ke = (inputs_for_calc['renovation_cost_per_sqm_eur'] / 1000.0) * inputs_for_calc['total_sqm']
    purchase_tx_costs_ke = buy_value_ke * (
        (inputs_for_calc['land_transfer_tax_percent'] + inputs_for_calc['notary_fee_percent'] + inputs_for_calc['agent_fee_purchase_percent']) / 100.0
    )
    sale_tx_costs_ke = sell_value_ke * (inputs_for_calc['agent_fee_sale_percent'] / 100.0)
    total_additional_costs_ke = purchase_tx_costs_ke + sale_tx_costs_ke
    total_project_cost_ke = buy_value_ke + reno_cost_ke + purchase_tx_costs_ke
    profit_before_tax_ke = sell_value_ke - total_project_cost_ke - sale_tx_costs_ke
    profit_after_tax_ke = profit_before_tax_ke * (1 - (TAX_RATE_FIXED / 100.0))
    margin_percent = ((sell_value_ke - total_project_cost_ke - sale_tx_costs_ke) / total_project_cost_ke) * 100 if total_project_cost_ke > 0 else 0

    # Calculate financing based on total upfront cost
    financing_ratio = st.session_state.get('disp_finance_ratio', 90.0) / 100.0 # Need financing ratio
    interest_rate_percent = st.session_state.get('disp_interest', 5.0) # Need interest rate
    project_duration_months = st.session_state.get('disp_duration', 9) # Need duration

    financed_per_project_ke = total_project_cost_ke * financing_ratio
    equity_per_project_ke = total_project_cost_ke - financed_per_project_ke

    # Estimate interest for this single project's loan over its duration
    monthly_interest_rate = (interest_rate_percent / 100.0) / 12.0
    estimated_interest_ke = financed_per_project_ke * monthly_interest_rate * project_duration_months

    # Calculate Total Capital Invest (Equity + Estimated Interest)
    total_capital_invest_ke = equity_per_project_ke + estimated_interest_ke

    # Display Rows with Formatting
    # Row 1: Project Cost | Capital Invest
    colA, colB = st.sidebar.columns(2)
    colA.metric(label="Total Project Cost", value=f"{total_project_cost_ke:.1f} k€") # Displayed first
    colB.metric(label="Est. Capital Invest", value=f"{total_capital_invest_ke:.1f} k€")

    col1, col2 = st.sidebar.columns(2)
    col1.metric(label="Total Buy Value", value=f"{buy_value_ke:.0f} k€")
    col2.metric(label="Total Sell Value", value=f"{sell_value_ke:.0f} k€")

    col3, col4 = st.sidebar.columns(2)
    col3.metric(label="Total Reno Cost", value=f"{reno_cost_ke:.1f} k€")
    col4.metric(label="Total Add. Costs", value=f"{total_additional_costs_ke:.1f} k€")

    col5, col6 = st.sidebar.columns(2)
    col5.metric(label="Margin (on Total Cost)", value=f"{margin_percent:.1f} %")
    col6.metric(label="Profit After Tax", value=f"{profit_after_tax_ke:.1f} k€")
else:
    # Placeholder display
    colA, colB = st.sidebar.columns(2)
    colA.metric(label="Total Project Cost", value="...") # Placeholder first
    colB.metric(label="Est. Capital Invest", value="...")

    col1, col2 = st.sidebar.columns(2)
    col1.metric(label="Total Buy Value", value="...")
    col2.metric(label="Total Sell Value", value="...")
    col3, col4 = st.sidebar.columns(2)
    col3.metric(label="Total Reno Cost", value="...")
    col4.metric(label="Total Add. Costs", value="...")
    col5, col6 = st.sidebar.columns(2)
    col5.metric(label="Margin (%)", value="...")
    col6.metric(label="Profit After Tax", value="...")
    col7, col8 = st.sidebar.columns(2)
    col7.metric(label="Total Capital Invest", value="...")

st.sidebar.markdown("---") # Separator

# --- Input Widgets (All grouped below separator) ---
st.sidebar.subheader("Project Base Values")
sqm_buy_value_ke = st.sidebar.number_input("SqM Buy Value (k€/sqm)", value=2.25, step=0.05, min_value=0.01, key='disp_buy_val') # Key links to display above
sqm_sell_value_ke = st.sidebar.number_input("SqM Sell Value (k€/sqm)", value=4.0, step=0.05, min_value=0.01, key='disp_sell_val')
total_sqm = st.sidebar.number_input("Total SqM per Project", value=100.0, step=10.0, min_value=1.0, key='disp_sqm_val')
renovation_cost_per_sqm_eur = st.sidebar.number_input("Renovation Cost (€/sqm)", value=600.0, step=50.0, min_value=0.0, key='disp_reno_val')
land_transfer_tax_percent = st.sidebar.number_input("Land Transfer Tax (% of Buy)", value=6.5, step=0.1, min_value=0.0, key='disp_land_tax')
notary_fee_percent = st.sidebar.number_input("Notary Fee (% of Buy)", value=1.5, step=0.1, min_value=0.0, key='disp_notary')
agent_fee_purchase_percent = st.sidebar.number_input("Agent Fee - Purchase (% of Buy)", value=3.57, step=0.1, min_value=0.0, key='disp_agent_buy')
agent_fee_sale_percent = st.sidebar.number_input("Agent Fee - Sale (% of Sell)", value=3.57, step=0.1, min_value=0.0, key='disp_agent_sell')

st.sidebar.subheader("Project Timing & Finance")
project_duration_months = st.sidebar.number_input("Project Duration (months)", value=9, step=1, min_value=1, key='disp_duration')
starting_capital_ke = st.sidebar.number_input("Starting Capital (k€)", value=60.0, step=1.0, min_value=0.0)
financing_ratio_percent = st.sidebar.slider("Financing Ratio (%)", 0, 100, 90, 1, key='disp_finance_ratio')
interest_rate_percent = st.sidebar.number_input("Interest Rate (% annual)", value=5.0, step=0.1, min_value=0.0, key='disp_interest')
hausgeld_eur_per_month = st.sidebar.number_input("Hausgeld (€ per Project/Month)", value=400.0, step=10.0, min_value=0.0, key='disp_hausgeld')
st.sidebar.metric(label="Tax Rate (%)", value=f"{TAX_RATE_FIXED:.1f}")

st.sidebar.subheader("Simulation Settings")
duration_jitter_percent = st.sidebar.number_input("Duration Jitter (% +/-)", value=20.0, step=1.0, min_value=0.0)
sell_price_jitter_percent = st.sidebar.number_input("Sell Price Jitter (% +/-)", value=10.0, step=1.0, min_value=0.0)
total_simulation_months = st.sidebar.number_input("Total Simulation Months", value=60, step=1, min_value=1)
num_simulations = st.sidebar.number_input("Number of Simulations", value=200, step=50, min_value=10)

# --- Helper Functions for Star Rating ---
def calculate_star_rating(profit_me: float) -> float:
    """Maps final accumulated profit (in M€) to a star rating (1.0 to 5.0)."""
    min_profit_me = 0.05  # 50 k€ = 0.05 M€ => 1 star
    max_profit_me = 10.0  # 10,000 k€ = 10 M€ => 5 stars

    if profit_me <= min_profit_me:
        return 1.0
    if profit_me >= max_profit_me:
        return 5.0

    # Linear interpolation
    rating = np.interp(profit_me, [min_profit_me, max_profit_me], [1.0, 5.0])

    # Round to nearest 0.5 star
    return round(rating * 2) / 2

def display_star_rating(rating: float):
    """Generates HTML/CSS to display a star rating with partial fills."""
    stars_html = "<div style='line-height: 1; font-size: 1.5em; color: #ffc107;'>"
    full_stars = int(rating)
    half_star = (rating - full_stars) >= 0.5
    empty_stars = 5 - full_stars - (1 if half_star else 0)

    stars_html += "★" * full_stars
    if half_star:
        # Use CSS linear gradient for a half-filled star
        stars_html += "<span style='position: relative; display: inline-block;'>" \
                      "<span style='position: absolute; width: 50%; overflow: hidden;'>★</span>" \
                      "<span style='color: #e0e0e0;'>★</span>" \
                      "</span>"
        # Alternative: Use specific half-star unicode if preferred and supported U+1F7D6
        # stars_html += "<span style='color: #ffc107;'>✭</span>"
    stars_html += "<span style='color: #e0e0e0;'>★</span>" * empty_stars # Use ☆ for empty if preferred

    stars_html += "</div>"
    st.markdown(stars_html, unsafe_allow_html=True)

# --- Simulation Execution and Results Display ---
if run_button:
    st.header("Simulation Results")
    # Prepare parameters dictionary using the widget state variables
    params = {
        "starting_capital_ke": starting_capital_ke,
        "sqm_buy_value_ke": sqm_buy_value_ke,
        "sqm_sell_value_ke": sqm_sell_value_ke,
        "total_sqm": total_sqm,
        "renovation_cost_per_sqm_ke": renovation_cost_per_sqm_eur / 1000.0,
        "project_duration_months": project_duration_months,
        "financing_ratio_percent": float(financing_ratio_percent),
        "interest_rate_percent": interest_rate_percent,
        "tax_rate_percent": TAX_RATE_FIXED,
        "hausgeld_eur_per_month": hausgeld_eur_per_month,
        "land_transfer_tax_percent": land_transfer_tax_percent,
        "notary_fee_percent": notary_fee_percent,
        "agent_fee_purchase_percent": agent_fee_purchase_percent,
        "agent_fee_sale_percent": agent_fee_sale_percent,
        "duration_jitter_percent": duration_jitter_percent,
        "sell_price_jitter_percent": sell_price_jitter_percent,
        "total_simulation_months": total_simulation_months,
        "num_simulations": num_simulations
    }

    try:
        with st.spinner(f"Running {num_simulations} simulations for {total_simulation_months} months..."):
            simulation_results = run_monte_carlo_simulations(**params)
            summary_stats = simulation_results['summary_stats'] # This is a DataFrame

        # Extract final summary stats
        final_month_stats = summary_stats.iloc[-1]

        # Get values in k€ first
        assets_mean_ke = final_month_stats.get('Assets_mean', 0.0)
        assets_std_ke = final_month_stats.get('Assets_std', 0.0)
        assets_p50_ke = final_month_stats.get('Assets_p50', 0.0)
        profit_mean_ke = final_month_stats.get('AccumulatedProfit_mean', 0.0)
        tx_costs_mean_ke = final_month_stats.get('AccumulatedTxCosts_mean', 0.0)
        hold_costs_mean_ke = final_month_stats.get('AccumulatedHoldCosts_mean', 0.0)

        # Convert to M€ for display
        assets_mean_me = assets_mean_ke / 1000.0
        assets_std_me = assets_std_ke / 1000.0 # Std Dev also scales
        assets_p50_me = assets_p50_ke / 1000.0
        profit_mean_me = profit_mean_ke / 1000.0
        tx_costs_mean_me = tx_costs_mean_ke / 1000.0
        hold_costs_mean_me = hold_costs_mean_ke / 1000.0

        summary_text = (
            f"After {total_simulation_months} months, estimated final assets: "
            f"{assets_mean_me:.2f} M€ (Std Dev: {assets_std_me:.2f} M€). "
            f"Median final assets: {assets_p50_me:.2f} M€. "
            f"Mean Accumulated Profit: {profit_mean_me:.2f} M€."
        )

        st.subheader("Summary")
        # Calculate and display rating using profit in M€
        rating = calculate_star_rating(profit_mean_me)
        display_star_rating(rating)
        st.write(summary_text)

        # Display additional cost metrics in M€
        st.metric(label="Mean Acc. Accumulated Profit", value=f"{profit_mean_me:.2f} M€")
        st.metric(label="Mean Acc. Transaction Costs", value=f"{tx_costs_mean_me:.2f} M€")
        st.metric(label="Mean Acc. Holding Costs (Interest + Hausgeld)", value=f"{hold_costs_mean_me:.2f} M€")

        st.subheader("Visualizations")

        # Regenerate plots (assuming visualization functions are updated)
        asset_growth_fig = plot_asset_growth(summary_stats) # Pass original k€ data
        st.plotly_chart(asset_growth_fig, use_container_width=True)

        accumulated_profit_fig = plot_accumulated_profit(summary_stats) # Pass original k€ data
        st.plotly_chart(accumulated_profit_fig, use_container_width=True)

        revenue_fig = plot_monthly_revenue(summary_stats) # Pass original k€ data
        st.plotly_chart(revenue_fig, use_container_width=True)

        # Optionally display summary stats table (still in k€)
        with st.expander("View Detailed Summary Statistics (Table in k€)"):
            st.dataframe(summary_stats)

    except Exception as e:
        st.error(f"An error occurred during simulation: {e}")
        # Optionally print traceback for debugging:
        # import traceback
        # st.exception(e)
else:
    st.info("Adjust parameters in the sidebar and click 'Run Simulation' to see the results.") 