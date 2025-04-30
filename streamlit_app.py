"""
File: streamlit_app.py
Description: Streamlit application for the FlipFinity Business Simulator.
Provides a web interface to input parameters, run simulations, and view results.
German: Stellt eine Weboberfläche zur Eingabe von Parametern, zur Durchführung von Simulationen und zur Anzeige von Ergebnissen bereit.
"""

import streamlit as st
import pandas as pd
import numpy as np # Needed for linear interpolation

# Import core logic
from simulation import run_monte_carlo_simulations
from visualization import plot_active_projects, plot_accumulated_profit, plot_monthly_revenue

st.set_page_config(layout="wide", initial_sidebar_state="expanded") # Use wide layout & expanded sidebar

st.title("FlipFinity Unternehmenssimulator") # Translated title

st.sidebar.header("Simulationsparameter") # Translated header

# --- Run Button (Top) ---
run_button = st.sidebar.button("Simulation starten", key='run_sim_button_top') # Translated button

# --- Initialize Session State for Calculation Inputs (if not already set) ---
def initialize_state_if_missing(key, default_value):
    if key not in st.session_state:
        st.session_state[key] = default_value

initialize_state_if_missing('disp_buy_val', 2.25)
initialize_state_if_missing('disp_sell_val', 4.0)
initialize_state_if_missing('disp_sqm_val', 84.0) # Use user's last default
initialize_state_if_missing('disp_reno_val', 600.0) # Use user's last default
initialize_state_if_missing('disp_land_tax', 6.5)
initialize_state_if_missing('disp_notary', 1.5)
initialize_state_if_missing('disp_agent_buy', 3.57)
initialize_state_if_missing('disp_agent_sell', 0)
initialize_state_if_missing('disp_duration', 9)
initialize_state_if_missing('disp_finance_ratio', 90.0)
initialize_state_if_missing('disp_interest', 5.0)
initialize_state_if_missing('disp_hausgeld_monthly', 400.0) # Add Hausgeld
# Add keys for other inputs needed for simulation
initialize_state_if_missing('disp_start_capital', 60.0)
initialize_state_if_missing('disp_dur_jitter', 20.0)
initialize_state_if_missing('disp_sell_jitter', 10.0)
initialize_state_if_missing('disp_sim_months', 60)
initialize_state_if_missing('disp_num_sim', 200)

# Initialize state for simulation results
initialize_state_if_missing('latest_summary_stats', None)
initialize_state_if_missing('is_full_simulation', False)

# --- Display Calculated Values (Below Button - Reads from initialized state) ---
st.sidebar.subheader("Berechnete Summen pro Projekt") # Translated subheader
# Now directly access state, it's guaranteed to exist
sqm_buy_value_ke_disp = st.session_state['disp_buy_val']
sqm_sell_value_ke_disp = st.session_state['disp_sell_val']
total_sqm_disp = st.session_state['disp_sqm_val']
renovation_cost_per_sqm_eur_disp = st.session_state['disp_reno_val']
land_transfer_tax_percent_disp = st.session_state['disp_land_tax']
notary_fee_percent_disp = st.session_state['disp_notary']
agent_fee_purchase_percent_disp = st.session_state['disp_agent_buy']
agent_fee_sale_percent_disp = st.session_state['disp_agent_sell']
project_duration_months_disp = st.session_state['disp_duration']
hausgeld_eur_per_month_disp = st.session_state['disp_hausgeld_monthly']
financing_ratio_disp = st.session_state['disp_finance_ratio'] / 100.0
interest_rate_percent_disp = st.session_state['disp_interest']
TAX_RATE_FIXED = 29.0

# Check validity - simplified check now state is initialized
all_vars_valid = True
if not all([
    isinstance(st.session_state[key], (int, float))
    for key in ['disp_buy_val', 'disp_sell_val', 'disp_sqm_val', 'disp_reno_val',
                'disp_land_tax', 'disp_notary', 'disp_agent_buy', 'disp_agent_sell',
                'disp_duration', 'disp_hausgeld_monthly', 'disp_finance_ratio', 'disp_interest']
]):
    all_vars_valid = False

if all_vars_valid and (st.session_state['disp_sqm_val'] <= 0 or st.session_state['disp_buy_val'] <= 0):
    all_vars_valid = False

if all_vars_valid:
    # 1. Base Values
    buy_value_ke = st.session_state['disp_buy_val'] * st.session_state['disp_sqm_val']
    sell_value_ke = st.session_state['disp_sell_val'] * st.session_state['disp_sqm_val']
    reno_cost_ke = (st.session_state['disp_reno_val'] / 1000.0) * st.session_state['disp_sqm_val']

    # 2. Transaction Fees
    purchase_tx_costs_ke = buy_value_ke * (
        (st.session_state['disp_land_tax'] + st.session_state['disp_notary'] + st.session_state['disp_agent_buy']) / 100.0
    )
    sale_tx_costs_ke = sell_value_ke * (st.session_state['disp_agent_sell'] / 100.0)

    # 3. Estimate Financing and Interest
    financing_ratio_disp = st.session_state['disp_finance_ratio'] / 100.0
    interest_rate_percent_disp = st.session_state['disp_interest']
    project_duration_months_disp = st.session_state['disp_duration']
    # Base for financing calculation (as before)
    cost_basis_for_financing = buy_value_ke + reno_cost_ke + purchase_tx_costs_ke
    financed_amount_ke = cost_basis_for_financing * financing_ratio_disp
    monthly_interest_rate = (interest_rate_percent_disp / 100.0) / 12.0
    estimated_interest_ke = financed_amount_ke * monthly_interest_rate * project_duration_months_disp

    # 4. Calculate Total Hausgeld
    hausgeld_eur_per_month_disp = st.session_state['disp_hausgeld_monthly']
    total_hausgeld_ke = (hausgeld_eur_per_month_disp / 1000.0) * project_duration_months_disp

    # 5. Calculate Total Additional Costs (as per user definition)
    total_additional_costs_ke = purchase_tx_costs_ke + sale_tx_costs_ke + estimated_interest_ke + total_hausgeld_ke

    # 6. Calculate Total Project Cost (as per user definition)
    total_project_cost_ke = buy_value_ke + reno_cost_ke + total_additional_costs_ke

    # 7. Calculate Est. Capital Invest
    # Equity needed is based on the *new* Total Project Cost
    equity_needed_ke = total_project_cost_ke * (1 - financing_ratio_disp) # Re-calculate equity base
    total_capital_invest_ke = equity_needed_ke + estimated_interest_ke + total_hausgeld_ke

    # 8. Calculate Profit Before Tax
    profit_before_tax_ke = sell_value_ke - total_project_cost_ke

    # 9. Calculate Profit After Tax
    TAX_RATE_FIXED = 29.0
    profit_after_tax_ke = profit_before_tax_ke * (1 - (TAX_RATE_FIXED / 100.0))

    # 10. Calculate Margins (based on new Total Project Cost)
    margin_percent_before_tax = (profit_before_tax_ke / total_project_cost_ke) * 100 if total_project_cost_ke > 0 else 0
    margin_percent_after_tax = (profit_after_tax_ke / total_project_cost_ke) * 100 if total_project_cost_ke > 0 else 0

    # --- Display Rows --- (Using the newly calculated values)
    # Row 1: Project Cost | Capital Invest
    colA, colB = st.sidebar.columns(2)
    colA.metric(label="Gesamtprojektkosten", value=f"{total_project_cost_ke:.1f} T€") # Step 6, Translated label, T€
    colB.metric(label="Gesch. Kapitaleinsatz", value=f"{total_capital_invest_ke:.1f} T€") # Step 7, Translated label, T€

    # Row 2: Buy Value | Sell Value
    col1, col2 = st.sidebar.columns(2)
    col1.metric(label="Gesamtkaufwert", value=f"{buy_value_ke:.0f} T€") # Step 1, Translated label, T€
    col2.metric(label="Gesamtverkaufswert", value=f"{sell_value_ke:.0f} T€") # Step 1, Translated label, T€

    # Row 3: Reno Cost | Add. Costs
    col3, col4 = st.sidebar.columns(2)
    col3.metric(label="Gesamtrenovierungskosten", value=f"{reno_cost_ke:.1f} T€") # Step 1, Translated label, T€
    col4.metric(label="Gesamtnebenkosten", value=f"{total_additional_costs_ke:.1f} T€") # Step 5, Translated label, T€

    # Row 4: Margins
    col5, col6 = st.sidebar.columns(2)
    col5.metric(label="Marge vor Steuern", value=f"{margin_percent_before_tax:.1f} %") # Step 10, Translated label
    col6.metric(label="Marge nach Steuern", value=f"{margin_percent_after_tax:.1f} %") # Step 10, Translated label

    # Row 5: Profits
    col7, col8 = st.sidebar.columns(2)
    col7.metric(label="Gewinn vor Steuern", value=f"{profit_before_tax_ke:.1f} T€") # Step 8, Translated label, T€
    col8.metric(label="Gewinn nach Steuern", value=f"{profit_after_tax_ke:.1f} T€") # Step 9, Translated label, T€

else:
    # Placeholder display
    colA, colB = st.sidebar.columns(2)
    colA.metric(label="Gesamtprojektkosten", value="...") # Translated label
    colB.metric(label="Gesch. Kapitaleinsatz", value="...") # Translated label

    col1, col2 = st.sidebar.columns(2)
    col1.metric(label="Gesamtkaufwert", value="...") # Translated label
    col2.metric(label="Gesamtverkaufswert", value="...") # Translated label

    col3, col4 = st.sidebar.columns(2)
    col3.metric(label="Gesamtrenovierungskosten", value="...") # Translated label
    col4.metric(label="Gesamtnebenkosten", value="...") # Translated label

    # Placeholder Row 4: Margins
    col5, col6 = st.sidebar.columns(2)
    col5.metric(label="Marge vor Steuern", value="...") # Translated label
    col6.metric(label="Marge nach Steuern", value="...") # Translated label

    # Placeholder Row 5: Profits
    col7, col8 = st.sidebar.columns(2)
    col7.metric(label="Gewinn vor Steuern", value="...") # Translated label
    col8.metric(label="Gewinn nach Steuern", value="...") # Translated label

st.sidebar.markdown("---") # Separator

# --- Input Widgets (All grouped below separator) ---
# Define widgets with keys used above for state initialization/access
st.sidebar.subheader("Projektgrundwerte") # Translated subheader
# Reverted: Rely on key for value, keep original units (k€/sqm) in label
sqm_buy_value_ke = st.sidebar.number_input("Kaufwert (T€/m²)", step=0.05, min_value=0.01, key='disp_buy_val') # Corrected label, removed value=
sqm_sell_value_ke = st.sidebar.number_input("Verkaufswert (T€/m²)", step=0.05, min_value=0.01, key='disp_sell_val') # Corrected label, removed value=
total_sqm = st.sidebar.number_input("Wohnfläche (m²)", step=10.0, min_value=1.0, key='disp_sqm_val') # Keep existing key and value source logic
renovation_cost_per_sqm_eur = st.sidebar.number_input("Renovierungskosten (€/m²)", step=50.0, min_value=0.0, key='disp_reno_val') # Keep existing key and value source logic
land_transfer_tax_percent = st.sidebar.number_input("Grunderwerbsteuer (% vom Kauf)", step=0.1, min_value=0.0, key='disp_land_tax') # Keep existing key and value source logic
notary_fee_percent = st.sidebar.number_input("Notargebühr (% vom Kauf)", step=0.1, min_value=0.0, key='disp_notary') # Keep existing key and value source logic
agent_fee_purchase_percent = st.sidebar.number_input("Maklergebühr - Kauf (% vom Kauf)", step=0.1, min_value=0.0, key='disp_agent_buy') # Keep existing key and value source logic
agent_fee_sale_percent = st.sidebar.number_input("Maklergebühr - Verkauf (% vom Verkauf)", step=0.1, min_value=0.0, key='disp_agent_sell') # Keep existing key and value source logic

st.sidebar.subheader("Projektzeit & Finanzen") # Translated subheader
project_duration_months = st.sidebar.number_input("Projektdauer (Monate)", step=1, min_value=1, key='disp_duration') # Keep existing key and value source logic
# Use key for starting capital
starting_capital_ke = st.sidebar.number_input("Startkapital (T€)", step=1.0, min_value=0.0, key='disp_start_capital') # Use key
financing_ratio_percent = st.sidebar.slider("Finanzierungsquote (%)", 0, 100, 90, 1, key='disp_finance_ratio') # Keep existing key and value source logic
interest_rate_percent = st.sidebar.number_input("Zinssatz (% p.a.)", step=0.1, min_value=0.0, key='disp_interest') # Keep existing key and value source logic
haugeld_eur_per_month = st.sidebar.number_input("Hausgeld (€ pro Projekt/Monat)", step=10.0, min_value=0.0, key='disp_hausgeld_monthly') # Keep existing key and value source logic
st.sidebar.metric(label="Steuersatz (%)", value=f"{TAX_RATE_FIXED:.1f}") # Translated label

st.sidebar.subheader("Simulationseinstellungen") # Translated subheader
# Use keys for simulation settings
duration_jitter_percent = st.sidebar.number_input("Dauerschwankung (% +/-)", step=1.0, min_value=0.0, key='disp_dur_jitter') # Use key
sell_price_jitter_percent = st.sidebar.number_input("Verkaufspreisschwankung (% +/-)", step=1.0, min_value=0.0, key='disp_sell_jitter') # Use key
total_simulation_months = st.sidebar.number_input("Gesamtsimulationsmonate", step=1, min_value=1, key='disp_sim_months') # Use key
num_simulations = st.sidebar.number_input("Anzahl der Simulationen", step=50, min_value=10, key='disp_num_sim') # Use key
# Removed starting capital input from here as it's now under Finance section

# --- Helper Functions for Star Rating ---
def calculate_star_rating(profit_me: float) -> float:
    """Maps final accumulated profit (in M€) to a star rating (1.0 to 5.0)."""
    min_profit_me = 1.0  # 1 M€ => 1 star
    max_profit_me = 50.0  # 50 M€ => 5 stars

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

# --- Simulation Execution Helper ---
def execute_simulation(params: dict):
    """Runs the simulation with given parameters and handles errors."""
    try:
        simulation_results = run_monte_carlo_simulations(**params)
        return simulation_results['summary_stats'] # Return the DataFrame
    except Exception as e:
        st.error(f"Während der Simulation ist ein Fehler aufgetreten: {e}")
        # Optionally print traceback for debugging:
        # import traceback
        # st.exception(e)
        return None

# --- Automatic Deterministic Simulation Run ---
# This runs on every script execution (initial load, widget change)

def get_current_params(use_full_settings: bool):
    """Gathers parameters from session state for simulation."""
    # Use session state values directly via their keys
    params = {
        "starting_capital_ke": st.session_state.disp_start_capital,
        "sqm_buy_value_ke": st.session_state.disp_buy_val,
        "sqm_sell_value_ke": st.session_state.disp_sell_val,
        "total_sqm": st.session_state.disp_sqm_val,
        "renovation_cost_per_sqm_ke": st.session_state.disp_reno_val / 1000.0,
        "project_duration_months": st.session_state.disp_duration,
        "financing_ratio_percent": float(st.session_state.disp_finance_ratio),
        "interest_rate_percent": st.session_state.disp_interest,
        "tax_rate_percent": TAX_RATE_FIXED,
        "hausgeld_total_per_project_ke": (st.session_state.disp_hausgeld_monthly / 1000.0) * st.session_state.disp_duration,
        "land_transfer_tax_percent": st.session_state.disp_land_tax,
        "notary_fee_percent": st.session_state.disp_notary,
        "agent_fee_purchase_percent": st.session_state.disp_agent_buy,
        "agent_fee_sale_percent": st.session_state.disp_agent_sell,
        "total_simulation_months": st.session_state.disp_sim_months,
        # Deterministic or Full settings:
        "duration_jitter_percent": 0.0 if not use_full_settings else st.session_state.disp_dur_jitter,
        "sell_price_jitter_percent": 0.0 if not use_full_settings else st.session_state.disp_sell_jitter,
        "num_simulations": 1 if not use_full_settings else st.session_state.disp_num_sim
    }
    return params

# Check if we need to run the *initial* deterministic simulation
# We run it if no results exist OR if the button wasn't just pressed (to avoid double run)
if st.session_state.latest_summary_stats is None or not run_button:
    try:
        current_params = get_current_params(use_full_settings=False)
        # Only run if params are valid (basic check)
        if current_params["total_sqm"] > 0 and current_params["sqm_buy_value_ke"] > 0:
            with st.spinner("Berechne Vorschau..."): # Spinner for preview
                deterministic_results = execute_simulation(current_params)
                if deterministic_results is not None:
                    st.session_state.latest_summary_stats = deterministic_results
                    st.session_state.is_full_simulation = False
        # else: Handle invalid param case if needed, maybe clear results?
        #    st.session_state.latest_summary_stats = None
    except Exception as e:
        # Catch potential errors during parameter gathering itself
        st.warning(f"Fehler bei der Vorbereitung der Vorschau: {e}")
        st.session_state.latest_summary_stats = None

# --- Manual Full Simulation Trigger ---
if run_button:
    # st.header("Simulationsergebnisse") # Header moved to display section
    try:
        full_params = get_current_params(use_full_settings=True)
        if full_params["total_sqm"] > 0 and full_params["sqm_buy_value_ke"] > 0:
            with st.spinner(f"Führe {full_params['num_simulations']} Simulationen für {full_params['total_simulation_months']} Monate durch..."): # Use params in spinner
                full_results = execute_simulation(full_params)
                if full_results is not None:
                    st.session_state.latest_summary_stats = full_results
                    st.session_state.is_full_simulation = True
                # else: Error handled within execute_simulation
        # else: Handle invalid param case? Maybe show warning?
        #    st.warning("Ungültige Parameter für die vollständige Simulation.")
    except Exception as e:
        st.error(f"Fehler beim Starten der vollständigen Simulation: {e}")
        # Optionally reset state?
        # st.session_state.latest_summary_stats = None

# --- Results Display ---
# Always attempt to display results from session state
if st.session_state.latest_summary_stats is not None:
    summary_stats = st.session_state.latest_summary_stats
    is_full_sim = st.session_state.is_full_simulation

    # Display appropriate header
    if is_full_sim:
        st.header("Simulationsergebnisse (Monte Carlo)")
        num_sim = st.session_state.disp_num_sim # Get actual number used
        sim_months = st.session_state.disp_sim_months
        spinner_text_base = f"Führe {num_sim} Simulationen für {sim_months} Monate durch..."
    else:
        st.header("Vorschau (Deterministisch)")
        sim_months = st.session_state.disp_sim_months
        spinner_text_base = f"Berechne Vorschau für {sim_months} Monate..."

    # Extract final summary stats from the DataFrame in state
    final_month_stats = summary_stats.iloc[-1]

    # Get values in k€ first
    assets_mean_ke = final_month_stats.get('Assets_mean', 0.0)
    assets_std_ke = final_month_stats.get('Assets_std', 0.0)
    assets_p50_ke = final_month_stats.get('Assets_p50', 0.0)
    profit_mean_ke = final_month_stats.get('AccumulatedProfit_mean', 0.0)
    tx_costs_mean_ke = final_month_stats.get('AccumulatedTxCosts_mean', 0.0)
    # hold_costs_mean_ke = final_month_stats.get('AccumulatedHoldCosts_mean', 0.0) # Old name
    interest_costs_mean_ke = final_month_stats.get('AccumulatedInterestCosts_mean', 0.0) # New name
    active_projects_mean = final_month_stats.get('ActiveProjects_mean', 0.0) # Get new value

    # Convert to M€ for display
    assets_mean_me = assets_mean_ke / 1000.0
    assets_std_me = assets_std_ke / 1000.0 # Std Dev also scales
    assets_p50_me = assets_p50_ke / 1000.0
    profit_mean_me = profit_mean_ke / 1000.0
    tx_costs_mean_me = tx_costs_mean_ke / 1000.0
    # hold_costs_mean_me = hold_costs_mean_ke / 1000.0 # Old name
    interest_costs_mean_me = interest_costs_mean_ke / 1000.0 # New name

    # Simplified summary text for now
    # summary_text = f"Ergebnisse nach {sim_months} Monaten."

    st.subheader("Zusammenfassung") # Translated subheader
    # Calculate and display rating using profit in M€
    rating = calculate_star_rating(profit_mean_me)
    display_star_rating(rating)
    # st.write(summary_text) # Can remove or keep this simple text

    # Display additional cost metrics in M€
    st.metric(label=f"Kumulierter Gewinn über {sim_months} Monate", value=f"{profit_mean_me:.2f} Mio. €") # Use sim_months
    # Add Active Projects Metric
    st.metric(label=f"Mittlere aktive Projekte im Monat {sim_months}", value=f"{active_projects_mean:.1f}") # Use sim_months

    st.metric(label="Mittl. kum. Transaktionskosten", value=f"{tx_costs_mean_me:.2f} Mio. €") # Translated label, Mio. €
    # st.metric(label="Mean Acc. Holding Costs (Interest + Hausgeld)", value=f"{hold_costs_mean_me:.3f} M€") # Old label
    st.metric(label="Mittl. kum. Zinskosten", value=f"{interest_costs_mean_me:.2f} Mio. €") # New label, Mio. €

    st.subheader("Visualisierungen") # Translated subheader

    # Regenerate plots using data from state
    # Replace asset growth with active projects
    active_projects_fig = plot_active_projects(summary_stats)
    st.plotly_chart(active_projects_fig, use_container_width=True)

    accumulated_profit_fig = plot_accumulated_profit(summary_stats)
    st.plotly_chart(accumulated_profit_fig, use_container_width=True)

    revenue_fig = plot_monthly_revenue(summary_stats)
    st.plotly_chart(revenue_fig, use_container_width=True)

    # Optionally display summary stats table (still in k€)
    with st.expander("Detaillierte Zusammenfassungsstatistiken anzeigen (Tabelle in T€)"): # Translated expander label, T€
        st.dataframe(summary_stats) # Display the data from state

else: # Display info message if no results are available in state
    st.info("Passen Sie die Parameter in der Seitenleiste an. Eine Vorschau wird automatisch berechnet. Klicken Sie auf 'Simulation starten' für die vollständige Monte-Carlo-Simulation.") # Updated info message 