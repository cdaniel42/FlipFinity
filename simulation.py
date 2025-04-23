"""
File: simulation.py
Description: This module contains the core logic for the FlipFinity Business Simulator.
It simulates the financial performance of a project-based business (like real estate flipping)
over a specified period using Monte Carlo methods to account for uncertainties.
"""

import numpy as np
import pandas as pd
import math

def run_single_simulation(
    starting_capital_ke: float,
    sqm_buy_value_ke: float,
    sqm_sell_value_ke: float,
    total_sqm: float,
    project_duration_months: int,
    financing_ratio_percent: float,
    interest_rate_percent: float, # Annual interest rate
    tax_rate_percent: float,
    duration_jitter_percent: float,
    sell_price_jitter_percent: float,
    total_simulation_months: int
) -> pd.DataFrame:
    """
    Runs a single simulation of the business lifecycle month by month.

    Args:
        starting_capital_ke: Initial capital available in thousands of euros.
        sqm_buy_value_ke: Cost per square meter for acquisition in k€.
        sqm_sell_value_ke: Expected selling price per square meter in k€.
        total_sqm: Total square meters per project.
        project_duration_months: Expected duration of a single project in months.
        financing_ratio_percent: The percentage of the project cost financed by loans.
        interest_rate_percent: Annual interest rate for loans.
        tax_rate_percent: Tax rate applied to profits.
        duration_jitter_percent: Max % variation applied to project duration (e.g., 10 for +/- 10%).
        sell_price_jitter_percent: Max % variation applied to sell price (e.g., 5 for +/- 5%).
        total_simulation_months: The total number of months to simulate.

    Returns:
        A pandas DataFrame containing the simulation results for each month,
        tracking key metrics like liquid capital, assets, loans, and gains.
    """
    # --- Input Validation and Parameter Calculation ---
    if not (0 <= financing_ratio_percent <= 100):
        raise ValueError("Financing ratio must be between 0 and 100.")
    if not (0 <= tax_rate_percent <= 100):
        raise ValueError("Tax rate must be between 0 and 100.")
    if interest_rate_percent < 0:
        raise ValueError("Interest rate cannot be negative.")

    financing_ratio = financing_ratio_percent / 100.0
    tax_rate = tax_rate_percent / 100.0
    monthly_interest_rate = (interest_rate_percent / 100.0) / 12.0
    duration_jitter_ratio = duration_jitter_percent / 100.0
    sell_price_jitter_ratio = sell_price_jitter_percent / 100.0

    project_cost_ke = sqm_buy_value_ke * total_sqm
    if project_cost_ke <= 0:
        raise ValueError("Project cost must be positive.")

    financed_per_project_ke = project_cost_ke * financing_ratio
    equity_per_project_ke = project_cost_ke - financed_per_project_ke

    # --- Simulation State Initialization ---
    liquid_capital = starting_capital_ke
    total_loan_balance = 0.0
    active_projects = [] # List of dicts: {'remaining_duration', 'equity_invested', 'loan_taken', 'potential_revenue_ke'}
    monthly_results = []
    current_total_assets = starting_capital_ke # Initial assets are just the starting capital

    # --- Simulation Loop ---
    for month in range(1, total_simulation_months + 1):
        previous_total_assets = current_total_assets

        # 1. Pay Monthly Interest
        interest_payment = total_loan_balance * monthly_interest_rate
        liquid_capital -= interest_payment
        # Ensure capital doesn't drop unreasonably low due to interest alone before projects resolve
        # In a real scenario, you might need lines of credit or handle bankruptcy
        # For simplicity, we assume interest can be paid, potentially going negative temporarily

        # 2. Process Completed Projects
        completed_this_month = [p for p in active_projects if p['remaining_duration'] <= 0]
        active_projects = [p for p in active_projects if p['remaining_duration'] > 0]

        for project in completed_this_month:
            # Apply jitter to sell price for this specific project
            sell_price_jitter = np.random.uniform(-sell_price_jitter_ratio, sell_price_jitter_ratio)
            actual_sell_value_ke = sqm_sell_value_ke * (1 + sell_price_jitter)
            actual_revenue_ke = actual_sell_value_ke * total_sqm

            profit_ke = actual_revenue_ke - project_cost_ke
            tax_on_profit = max(0, profit_ke * tax_rate) # Tax only positive profit
            profit_after_tax = profit_ke - tax_on_profit

            # Return capital and profits, pay off loan principal
            liquid_capital += project['equity_invested'] + profit_after_tax
            total_loan_balance -= project['loan_taken']

        # 3. Start New Projects
        projects_started_this_month = 0
        while liquid_capital >= equity_per_project_ke and equity_per_project_ke > 0:
            # Apply jitter to duration for this specific project
            duration_jitter = np.random.uniform(-duration_jitter_ratio, duration_jitter_ratio)
            actual_duration = max(1, round(project_duration_months * (1 + duration_jitter))) # Ensure duration is at least 1 month

            liquid_capital -= equity_per_project_ke
            total_loan_balance += financed_per_project_ke

            # Store potential revenue based on base sell price; jitter applied at completion
            potential_revenue_ke = sqm_sell_value_ke * total_sqm

            active_projects.append({
                'remaining_duration': actual_duration,
                'equity_invested': equity_per_project_ke,
                'loan_taken': financed_per_project_ke,
                'potential_revenue_ke': potential_revenue_ke # We use the expected revenue here for consistency
            })
            projects_started_this_month += 1

        # 4. Decrement Remaining Durations
        for project in active_projects:
            project['remaining_duration'] -= 1

        # 5. Record Monthly State
        total_equity_in_projects = sum(p['equity_invested'] for p in active_projects)
        current_total_assets = liquid_capital + total_equity_in_projects
        monthly_net_gain = current_total_assets - previous_total_assets

        monthly_results.append({
            'Month': month,
            'Liquid_Capital_kE': liquid_capital,
            'Total_Equity_in_Projects_kE': total_equity_in_projects,
            'Total_Assets_kE': current_total_assets,
            'Total_Loan_Balance_kE': total_loan_balance,
            'Monthly_Net_Gain_kE': monthly_net_gain,
            'Projects_Started': projects_started_this_month,
            'Projects_Completed': len(completed_this_month)
        })

    return pd.DataFrame(monthly_results)


def run_monte_carlo_simulations(
    num_simulations: int,
    starting_capital_ke: float,
    sqm_buy_value_ke: float,
    sqm_sell_value_ke: float,
    total_sqm: float,
    project_duration_months: int,
    financing_ratio_percent: float,
    interest_rate_percent: float,
    tax_rate_percent: float,
    duration_jitter_percent: float,
    sell_price_jitter_percent: float,
    total_simulation_months: int
) -> dict:
    """
    Runs multiple simulations and aggregates the results.

    Args:
        num_simulations: The number of individual simulations to run.
        All other args are passed directly to run_single_simulation.

    Returns:
        A dictionary containing aggregated results:
        - 'summary_stats': DataFrame with mean, std, min, 25%, 50%, 75%, max
                         for Total_Assets_kE and Monthly_Net_Gain_kE per month.
        - 'all_results': List containing the full DataFrame result from each simulation.
                         (Optional, can be large).
    """
    all_results_list = []
    for i in range(num_simulations):
        # Add a print statement for progress tracking, especially for large numbers of simulations
        if (i + 1) % 100 == 0 or num_simulations < 100 and (i + 1) % 10 == 0:
             print(f"Running simulation {i+1}/{num_simulations}...")
        sim_result = run_single_simulation(
            starting_capital_ke=starting_capital_ke,
            sqm_buy_value_ke=sqm_buy_value_ke,
            sqm_sell_value_ke=sqm_sell_value_ke,
            total_sqm=total_sqm,
            project_duration_months=project_duration_months,
            financing_ratio_percent=financing_ratio_percent,
            interest_rate_percent=interest_rate_percent,
            tax_rate_percent=tax_rate_percent,
            duration_jitter_percent=duration_jitter_percent,
            sell_price_jitter_percent=sell_price_jitter_percent,
            total_simulation_months=total_simulation_months
        )
        all_results_list.append(sim_result)
    print("Simulations complete.")

    # Aggregate results - Combine all simulations into one large DataFrame
    # Need a common key to join/align data across simulations by month
    # We can concatenate and then group by month

    # Focus on key metrics for aggregation: Assets and Gains
    all_assets = pd.concat([df.set_index('Month')['Total_Assets_kE'] for df in all_results_list], axis=1)
    all_gains = pd.concat([df.set_index('Month')['Monthly_Net_Gain_kE'] for df in all_results_list], axis=1)

    # Calculate summary statistics
    asset_stats = all_assets.agg(['mean', 'std', 'min', 'max'], axis=1)
    gain_stats = all_gains.agg(['mean', 'std', 'min', 'max'], axis=1)

    # Calculate percentiles separately as agg doesn't handle them easily with specific names
    asset_stats['p25'] = all_assets.quantile(0.25, axis=1)
    asset_stats['p50'] = all_assets.quantile(0.50, axis=1) # Median
    asset_stats['p75'] = all_assets.quantile(0.75, axis=1)

    gain_stats['p25'] = all_gains.quantile(0.25, axis=1)
    gain_stats['p50'] = all_gains.quantile(0.50, axis=1) # Median
    gain_stats['p75'] = all_gains.quantile(0.75, axis=1)

    # Combine stats for assets and gains into one summary DataFrame
    summary_stats = pd.concat(
        [asset_stats.add_prefix('Assets_'), gain_stats.add_prefix('Gains_')],
        axis=1
    )

    # Reorder columns for clarity
    asset_cols = ['Assets_mean', 'Assets_std', 'Assets_min', 'Assets_p25', 'Assets_p50', 'Assets_p75', 'Assets_max']
    gain_cols = ['Gains_mean', 'Gains_std', 'Gains_min', 'Gains_p25', 'Gains_p50', 'Gains_p75', 'Gains_max']
    summary_stats = summary_stats[asset_cols + gain_cols]

    return {
        "summary_stats": summary_stats,
        # "all_results": all_results_list # Optionally return all raw data
    }

# Example Usage (for testing)
if __name__ == '__main__':
    print("Running example simulation...")
    results = run_monte_carlo_simulations(
        num_simulations=50, # Keep low for quick testing
        starting_capital_ke=60.0,
        sqm_buy_value_ke=1.5, # Example value
        sqm_sell_value_ke=2.0, # Example value
        total_sqm=100.0, # Example value
        project_duration_months=9,
        financing_ratio_percent=90.0,
        interest_rate_percent=5.0,
        tax_rate_percent=29.125, # Example value from sheet
        duration_jitter_percent=10.0, # +/- 10%
        sell_price_jitter_percent=5.0, # +/- 5%
        total_simulation_months=60
    )

    print("\n--- Summary Statistics ---")
    print(results['summary_stats'].to_string())

    print(f"\nExample: Final Month ({results['summary_stats'].index[-1]}) Average Assets: "
          f"{results['summary_stats']['Assets_mean'].iloc[-1]:.2f} k€")
    print(f"\nExample: Final Month ({results['summary_stats'].index[-1]}) Std Dev Assets: "
          f"{results['summary_stats']['Assets_std'].iloc[-1]:.2f} k€") 