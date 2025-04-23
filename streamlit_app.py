"""
File: streamlit_app.py
Description: Streamlit application for the FlipFinity Business Simulator.
Provides a web interface to input parameters, run simulations, and view results.
"""

import streamlit as st
import pandas as pd

# Import core logic
from simulation import run_monte_carlo_simulations
from visualization import plot_asset_growth, plot_monthly_gains, plot_monthly_revenue

st.set_page_config(layout="wide") # Use wide layout for better plot display

st.title("FlipFinity Business Simulator")

st.sidebar.header("Simulation Parameters")

# --- Input Widgets ---
with st.sidebar.form(key='simulation_params'):
    st.subheader("Project Setup")
    sqm_buy_value_ke = st.number_input("SqM Buy Value (k€/sqm)", value=1.5, step=0.05, min_value=0.01)
    sqm_sell_value_ke = st.number_input("SqM Sell Value (k€/sqm)", value=2.0, step=0.05, min_value=0.01)
    total_sqm = st.number_input("Total SqM per Project", value=100.0, step=10.0, min_value=1.0)
    project_duration_months = st.number_input("Project Duration (months)", value=9, step=1, min_value=1)

    st.subheader("Financials")
    starting_capital_ke = st.number_input("Starting Capital (k€)", value=60.0, step=1.0, min_value=0.0)
    financing_ratio_percent = st.slider("Financing Ratio (%)", min_value=0, max_value=100, value=90, step=1)
    interest_rate_percent = st.number_input("Interest Rate (% annual)", value=5.0, step=0.1, min_value=0.0)
    tax_rate_percent = st.slider("Tax Rate (%)", min_value=0, max_value=100, value=29, step=1)

    st.subheader("Simulation Settings")
    duration_jitter_percent = st.number_input("Duration Jitter (% +/-)", value=10.0, step=1.0, min_value=0.0)
    sell_price_jitter_percent = st.number_input("Sell Price Jitter (% +/-)", value=10.0, step=1.0, min_value=0.0)
    total_simulation_months = st.number_input("Total Simulation Months", value=60, step=1, min_value=1)
    num_simulations = st.number_input("Number of Simulations", value=500, step=50, min_value=10)

    # Submit button for the form
    run_button = st.form_submit_button(label='Run Simulation')

# --- Display Calculated Values (outside the form, updates instantly) ---
st.sidebar.subheader("Calculated per Project")
if sqm_buy_value_ke > 0 and total_sqm > 0:
    total_buy = sqm_buy_value_ke * total_sqm
    total_sell = sqm_sell_value_ke * total_sqm
    margin = ((total_sell - total_buy) / total_buy) * 100 if total_buy > 0 else 0
    st.sidebar.metric(label="Total Buy Value", value=f"{total_buy:.2f} k€")
    st.sidebar.metric(label="Total Sell Value", value=f"{total_sell:.2f} k€")
    st.sidebar.metric(label="Margin", value=f"{margin:.2f} %")
else:
    st.sidebar.text("Enter valid buy value and sqm.")

# --- Simulation Execution and Results Display ---
if run_button:
    st.header("Simulation Results")
    # Prepare parameters dictionary
    params = {
        "starting_capital_ke": starting_capital_ke,
        "sqm_buy_value_ke": sqm_buy_value_ke,
        "sqm_sell_value_ke": sqm_sell_value_ke,
        "total_sqm": total_sqm,
        "project_duration_months": project_duration_months,
        "financing_ratio_percent": float(financing_ratio_percent), # Ensure slider value is float if needed
        "interest_rate_percent": interest_rate_percent,
        "tax_rate_percent": float(tax_rate_percent), # Ensure slider value is float if needed
        "duration_jitter_percent": duration_jitter_percent,
        "sell_price_jitter_percent": sell_price_jitter_percent,
        "total_simulation_months": total_simulation_months,
        "num_simulations": num_simulations
    }

    try:
        with st.spinner(f"Running {num_simulations} simulations for {total_simulation_months} months..."):
            simulation_results = run_monte_carlo_simulations(**params)
            summary_stats = simulation_results['summary_stats'] # This is a DataFrame

        # Extract final summary text
        final_month_stats = summary_stats.iloc[-1]
        summary_text = (
            f"After {total_simulation_months} months, estimated final assets: "
            f"{final_month_stats['Assets_mean']:.2f} k€ (Std Dev: {final_month_stats['Assets_std']:.2f} k€). "
            f"Median final assets: {final_month_stats['Assets_p50']:.2f} k€."
        )

        st.subheader("Summary")
        st.write(summary_text)

        st.subheader("Visualizations")

        # Generate and display plots
        asset_growth_fig = plot_asset_growth(summary_stats)
        st.plotly_chart(asset_growth_fig, use_container_width=True)

        monthly_gains_fig = plot_monthly_gains(summary_stats)
        st.plotly_chart(monthly_gains_fig, use_container_width=True)

        revenue_fig = plot_monthly_revenue(summary_stats)
        st.plotly_chart(revenue_fig, use_container_width=True)

        # Optionally display summary stats table
        with st.expander("View Detailed Summary Statistics (Table)"):
            st.dataframe(summary_stats)

    except Exception as e:
        st.error(f"An error occurred during simulation: {e}")
        # Optionally print traceback for debugging:
        # import traceback
        # st.exception(e)
else:
    st.info("Adjust parameters in the sidebar and click 'Run Simulation' to see the results.") 