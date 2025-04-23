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

st.set_page_config(layout="wide") # Use wide layout for better plot display

st.title("FlipFinity Business Simulator")

st.sidebar.header("Simulation Parameters")

# --- Run Button (Moved to very top) ---
run_button = st.sidebar.button("Run Simulation", key='run_sim_button_top')

# --- Display Calculated Values (Below Button) ---
st.sidebar.subheader("Calculated per Project")
# Need to get widget values - define widgets later, access state here if possible
# This section will now depend on the widgets defined *below* it.
# We use st.session_state.get to safely access values that might not exist on the first run.
sqm_buy_value_ke_disp = st.session_state.get('disp_buy_val', 2.0)
sqm_sell_value_ke_disp = st.session_state.get('disp_sell_val', 3.0)
total_sqm_disp = st.session_state.get('disp_sqm_val', 100.0)
renovation_cost_per_sqm_eur_disp = st.session_state.get('disp_reno_val', 500.0)

if (
    isinstance(sqm_buy_value_ke_disp, (int, float)) and sqm_buy_value_ke_disp > 0 and
    isinstance(total_sqm_disp, (int, float)) and total_sqm_disp > 0 and
    isinstance(sqm_sell_value_ke_disp, (int, float)) and
    isinstance(renovation_cost_per_sqm_eur_disp, (int, float))
):
    renovation_cost_per_sqm_ke_disp = renovation_cost_per_sqm_eur_disp / 1000.0
    total_buy_cost = sqm_buy_value_ke_disp * total_sqm_disp
    total_reno_cost = renovation_cost_per_sqm_ke_disp * total_sqm_disp
    total_project_cost = total_buy_cost + total_reno_cost
    total_sell_value = sqm_sell_value_ke_disp * total_sqm_disp
    margin = ((total_sell_value - total_project_cost) / total_project_cost) * 100 if total_project_cost > 0 else 0

    # Display metrics sequentially in a single column
    st.sidebar.metric(label="Total Buy Value", value=f"{total_buy_cost:.2f} k€")
    st.sidebar.metric(label="Total Renovation Cost", value=f"{total_reno_cost:.2f} k€")
    st.sidebar.metric(label="Total Sell Value", value=f"{total_sell_value:.2f} k€")
    st.sidebar.metric(label="Margin (on Total Cost)", value=f"{margin:.2f} %")
else:
    # Placeholder display in single column
    st.sidebar.metric(label="Total Buy Value", value="...")
    st.sidebar.metric(label="Total Renovation Cost", value="...")
    st.sidebar.metric(label="Total Sell Value", value="...")
    st.sidebar.metric(label="Margin (on Total Cost)", value="...")

st.sidebar.markdown("---") # Separator

# --- All Input Widgets (Defined AFTER button and calculations) ---
st.sidebar.subheader("Project Setup")
sqm_buy_value_ke = st.sidebar.number_input("SqM Buy Value (k€/sqm)", value=2.0, step=0.05, min_value=0.01, key='disp_buy_val') # Use key for session state access
sqm_sell_value_ke = st.sidebar.number_input("SqM Sell Value (k€/sqm)", value=3.0, step=0.05, min_value=0.01, key='disp_sell_val')
total_sqm = st.sidebar.number_input("Total SqM per Project", value=100.0, step=10.0, min_value=1.0, key='disp_sqm_val')
renovation_cost_per_sqm_eur = st.sidebar.number_input("Renovation Cost (€/sqm)", value=500.0, step=50.0, min_value=0.0, key='disp_reno_val', help="Enter renovation cost in EURO per square meter.")
project_duration_months = st.sidebar.number_input("Project Duration (months)", value=9, step=1, min_value=1)

st.sidebar.subheader("Project Timing & Finance") # Renamed Subheader
starting_capital_ke = st.sidebar.number_input("Starting Capital (k€)", value=60.0, step=1.0, min_value=0.0)
financing_ratio_percent = st.sidebar.slider("Financing Ratio (%)", 0, 100, 90, 1)
interest_rate_percent = st.sidebar.number_input("Interest Rate (% annual)", value=5.0, step=0.1, min_value=0.0)
TAX_RATE_FIXED = 29.0
st.sidebar.metric(label="Tax Rate (%)", value=f"{TAX_RATE_FIXED:.1f}")
# Add Hausgeld input
hausgeld_eur_per_month = st.sidebar.number_input("Hausgeld (€ per Project/Month)", value=400.0, step=10.0, min_value=0.0, key='disp_hausgeld') # Default 400, Added key

st.sidebar.subheader("Transaction Costs (%)") # New Subheader
land_transfer_tax_percent = st.sidebar.number_input("Land Transfer Tax (% of Buy Value)", value=6.5, step=0.1, min_value=0.0, key='disp_land_tax') # Default 6.5, Added key
notary_fee_percent = st.sidebar.number_input("Notary Fee (% of Buy Value)", value=1.5, step=0.1, min_value=0.0)
agent_fee_purchase_percent = st.sidebar.number_input("Agent Fee - Purchase (% of Buy Value)", value=3.57, step=0.1, min_value=0.0)
agent_fee_sale_percent = st.sidebar.number_input("Agent Fee - Sale (% of Sell Value)", value=3.57, step=0.1, min_value=0.0)

st.sidebar.subheader("Simulation Settings")
duration_jitter_percent = st.sidebar.number_input("Duration Jitter (% +/-)", value=20.0, step=1.0, min_value=0.0)
sell_price_jitter_percent = st.sidebar.number_input("Sell Price Jitter (% +/-)", value=10.0, step=1.0, min_value=0.0)
total_simulation_months = st.sidebar.number_input("Total Simulation Months", value=60, step=1, min_value=1)
num_simulations = st.sidebar.number_input("Number of Simulations", value=50, step=50, min_value=10)

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
        "renovation_cost_per_sqm_ke": renovation_cost_per_sqm_eur / 1000.0, # Convert the value from the widget
        "project_duration_months": project_duration_months,
        "financing_ratio_percent": float(financing_ratio_percent),
        "interest_rate_percent": interest_rate_percent,
        "tax_rate_percent": TAX_RATE_FIXED,
        "duration_jitter_percent": duration_jitter_percent,
        "sell_price_jitter_percent": sell_price_jitter_percent,
        "total_simulation_months": total_simulation_months,
        "num_simulations": num_simulations,
        "hausgeld_eur_per_month": hausgeld_eur_per_month,
        "land_transfer_tax_percent": land_transfer_tax_percent,
        "notary_fee_percent": notary_fee_percent,
        "agent_fee_purchase_percent": agent_fee_purchase_percent,
        "agent_fee_sale_percent": agent_fee_sale_percent
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
        st.metric(label="Mean Acc. Transaction Costs", value=f"{tx_costs_mean_me:.3f} M€")
        st.metric(label="Mean Acc. Holding Costs (Interest + Hausgeld)", value=f"{hold_costs_mean_me:.3f} M€")

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