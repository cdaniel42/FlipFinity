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
    renovation_cost_per_sqm_ke: float,
    project_duration_months: int,
    financing_ratio_percent: float,
    interest_rate_percent: float, # Annual interest rate
    tax_rate_percent: float,
    hausgeld_total_per_project_ke: float,
    land_transfer_tax_percent: float,
    notary_fee_percent: float,
    agent_fee_purchase_percent: float,
    agent_fee_sale_percent: float,
    duration_jitter_percent: float,
    sell_price_jitter_percent: float,
    total_simulation_months: int
) -> pd.DataFrame:
    """
    Runs a single simulation of the business lifecycle month by month.

    Includes transaction costs (tax, notary, agent) and total Hausgeld cost per project duration.

    Args:
        starting_capital_ke: Initial capital available in thousands of euros.
        sqm_buy_value_ke: Cost per square meter for acquisition in k€.
        sqm_sell_value_ke: Expected selling price per square meter in k€.
        total_sqm: Total square meters per project.
        renovation_cost_per_sqm_ke: Cost per square meter for renovation in k€.
        project_duration_months: Expected duration of a single project in months.
        financing_ratio_percent: The percentage of the project cost financed by loans.
        interest_rate_percent: Annual interest rate for loans.
        tax_rate_percent: Tax rate applied to profits.
        hausgeld_total_per_project_ke: Total Hausgeld cost for the project duration in k€.
        land_transfer_tax_percent: Land transfer tax percentage.
        notary_fee_percent: Notary fee percentage.
        agent_fee_purchase_percent: Agent fee percentage for purchase.
        agent_fee_sale_percent: Agent fee percentage for sale.
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
    if renovation_cost_per_sqm_ke < 0:
        raise ValueError("Renovation cost cannot be negative.")
    if hausgeld_total_per_project_ke < 0: raise ValueError("Total Hausgeld cannot be negative.")
    if land_transfer_tax_percent < 0: raise ValueError("Land transfer tax % cannot be negative.")
    if notary_fee_percent < 0: raise ValueError("Notary fee % cannot be negative.")
    if agent_fee_purchase_percent < 0: raise ValueError("Agent purchase fee % cannot be negative.")
    if agent_fee_sale_percent < 0: raise ValueError("Agent sale fee % cannot be negative.")

    financing_ratio = financing_ratio_percent / 100.0
    tax_rate = tax_rate_percent / 100.0
    monthly_interest_rate = (interest_rate_percent / 100.0) / 12.0
    duration_jitter_ratio = duration_jitter_percent / 100.0
    sell_price_jitter_ratio = sell_price_jitter_percent / 100.0
    land_transfer_tax_rate = land_transfer_tax_percent / 100.0
    notary_fee_rate = notary_fee_percent / 100.0
    agent_fee_purchase_rate = agent_fee_purchase_percent / 100.0
    agent_fee_sale_rate = agent_fee_sale_percent / 100.0

    # --- Simulation State Initialization ---
    liquid_capital = starting_capital_ke
    total_loan_balance = 0.0
    active_projects = [] # List of dicts: {'remaining_duration', 'equity_invested', 'loan_taken', 'potential_revenue_ke'}
    monthly_results = []
    current_total_assets = starting_capital_ke # Initial assets are just the starting capital
    monthly_revenue_accumulator = 0.0
    accumulated_profit_after_tax_ke = 0.0 # Track sum of profits
    accumulated_transaction_costs_ke = 0.0 # New accumulator
    accumulated_interest_costs_ke = 0.0 # Track only interest

    # --- Simulation Loop ---
    for month in range(1, total_simulation_months + 1):
        previous_total_assets = current_total_assets
        monthly_revenue_accumulator = 0.0 # Reset for the current month

        # 1. Pay Monthly Holding Costs (Interest ONLY)
        interest_payment_ke = total_loan_balance * monthly_interest_rate
        liquid_capital -= interest_payment_ke
        accumulated_interest_costs_ke += interest_payment_ke # Accumulate only interest

        # 2. Process Completed Projects
        completed_this_month = [p for p in active_projects if p['remaining_duration'] <= 0]
        active_projects = [p for p in active_projects if p['remaining_duration'] > 0]

        for project in completed_this_month:
            # Apply jitter to sell price for this specific project
            sell_price_jitter = np.random.uniform(-sell_price_jitter_ratio, sell_price_jitter_ratio)
            actual_sell_value_ke = sqm_sell_value_ke * (1 + sell_price_jitter)
            actual_revenue_ke = actual_sell_value_ke * total_sqm

            # Calculate sale transaction cost
            sale_agent_fee_ke = actual_revenue_ke * agent_fee_sale_rate
            accumulated_transaction_costs_ke += sale_agent_fee_ke # Accumulate

            # Calculate profit before tax (Revenue - PropertyCost - RenoCost - PurchaseTxCosts - SaleTxCosts - TotalHausgeld)
            profit_before_tax_ke = (actual_revenue_ke
                                   - project['property_buy_value_ke']
                                   - project['renovation_total_cost_ke']
                                   - project['purchase_transaction_costs_ke']
                                   - sale_agent_fee_ke
                                   - project['hausgeld_total_ke'])

            tax_on_profit_ke = max(0, profit_before_tax_ke * tax_rate)
            profit_after_tax_ke = profit_before_tax_ke - tax_on_profit_ke
            accumulated_profit_after_tax_ke += profit_after_tax_ke

            # Accumulate revenue for the month
            monthly_revenue_accumulator += actual_revenue_ke
            # Accumulate Profit After Tax
            accumulated_profit_after_tax_ke += profit_after_tax_ke

            # Return capital and profits, pay off loan principal
            liquid_capital += project['equity_invested'] + profit_after_tax_ke
            total_loan_balance -= project['loan_taken']

        # 3. Start New Projects
        projects_started_this_month = 0
        while True: # Loop indefinitely until broken
            # Calculate ALL upfront costs including total Hausgeld
            property_buy_value_ke = sqm_buy_value_ke * total_sqm
            renovation_total_cost_ke = renovation_cost_per_sqm_ke * total_sqm
            purchase_transaction_costs_ke = (property_buy_value_ke * land_transfer_tax_rate +
                                           property_buy_value_ke * notary_fee_rate +
                                           property_buy_value_ke * agent_fee_purchase_rate)
            # Total Hausgeld is now passed as a parameter
            total_upfront_investment_ke = property_buy_value_ke + renovation_total_cost_ke + purchase_transaction_costs_ke + hausgeld_total_per_project_ke

            # Exit conditions for the loop
            if total_upfront_investment_ke <= 0:
                break # Cannot start a project with zero/negative cost

            financed_per_project_ke = total_upfront_investment_ke * financing_ratio
            equity_per_project_ke = total_upfront_investment_ke - financed_per_project_ke

            if liquid_capital < equity_per_project_ke:
                break # Cannot afford the equity for this project

            # If we reach here, we can start the project
            # Apply jitter to duration
            duration_jitter = np.random.uniform(-duration_jitter_ratio, duration_jitter_ratio)
            actual_duration = max(1, round(project_duration_months * (1 + duration_jitter)))

            # Deduct equity, increase loan, accumulate costs
            liquid_capital -= equity_per_project_ke
            total_loan_balance += financed_per_project_ke
            accumulated_transaction_costs_ke += purchase_transaction_costs_ke

            # Add project to active list
            active_projects.append({
                'remaining_duration': actual_duration,
                'equity_invested': equity_per_project_ke,
                'loan_taken': financed_per_project_ke,
                'property_buy_value_ke': property_buy_value_ke,
                'renovation_total_cost_ke': renovation_total_cost_ke,
                'purchase_transaction_costs_ke': purchase_transaction_costs_ke,
                'base_sell_value_ke': sqm_sell_value_ke,
                'hausgeld_total_ke': hausgeld_total_per_project_ke
            })
            projects_started_this_month += 1
            # Loop continues to see if another project can be started

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
            'Accumulated_Profit_After_Tax_kE': accumulated_profit_after_tax_ke,
            'Accumulated_Transaction_Costs_kE': accumulated_transaction_costs_ke,
            'Accumulated_Interest_Costs_kE': accumulated_interest_costs_ke,
            'Monthly_Revenue_kE': monthly_revenue_accumulator,
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
    renovation_cost_per_sqm_ke: float,
    project_duration_months: int,
    financing_ratio_percent: float,
    interest_rate_percent: float,
    tax_rate_percent: float,
    hausgeld_total_per_project_ke: float,
    land_transfer_tax_percent: float,
    notary_fee_percent: float,
    agent_fee_purchase_percent: float,
    agent_fee_sale_percent: float,
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
            renovation_cost_per_sqm_ke=renovation_cost_per_sqm_ke,
            project_duration_months=project_duration_months,
            financing_ratio_percent=financing_ratio_percent,
            interest_rate_percent=interest_rate_percent,
            tax_rate_percent=tax_rate_percent,
            hausgeld_total_per_project_ke=hausgeld_total_per_project_ke,
            land_transfer_tax_percent=land_transfer_tax_percent,
            notary_fee_percent=notary_fee_percent,
            agent_fee_purchase_percent=agent_fee_purchase_percent,
            agent_fee_sale_percent=agent_fee_sale_percent,
            duration_jitter_percent=duration_jitter_percent,
            sell_price_jitter_percent=sell_price_jitter_percent,
            total_simulation_months=total_simulation_months
        )
        all_results_list.append(sim_result)
    print("Simulations complete.")

    # Aggregate results - Combine all simulations into one large DataFrame
    # Need a common key to join/align data across simulations by month
    # We can concatenate and then group by month

    # Focus on key metrics for aggregation: Assets, Accumulated Profit After Tax, and Monthly Revenue
    all_assets = pd.concat([df.set_index('Month')['Total_Assets_kE'] for df in all_results_list], axis=1)
    all_accumulated_profit = pd.concat([df.set_index('Month')['Accumulated_Profit_After_Tax_kE'] for df in all_results_list], axis=1)
    all_revenue = pd.concat([df.set_index('Month')['Monthly_Revenue_kE'] for df in all_results_list], axis=1)
    all_tx_costs = pd.concat([df.set_index('Month')['Accumulated_Transaction_Costs_kE'] for df in all_results_list], axis=1)
    all_interest_costs = pd.concat([df.set_index('Month')['Accumulated_Interest_Costs_kE'] for df in all_results_list], axis=1)

    # Calculate summary statistics
    asset_stats = all_assets.agg(['mean', 'std', 'min', 'max'], axis=1)
    accumulated_profit_stats = all_accumulated_profit.agg(['mean', 'std', 'min', 'max'], axis=1)
    revenue_stats = all_revenue.agg(['mean', 'std', 'min', 'max'], axis=1)
    tx_cost_stats = all_tx_costs.agg(['mean', 'std', 'min', 'max'], axis=1)
    interest_cost_stats = all_interest_costs.agg(['mean', 'std', 'min', 'max'], axis=1)

    # Calculate percentiles separately
    asset_stats['p25'] = all_assets.quantile(0.25, axis=1)
    asset_stats['p50'] = all_assets.quantile(0.50, axis=1) # Median
    asset_stats['p75'] = all_assets.quantile(0.75, axis=1)

    accumulated_profit_stats['p25'] = all_accumulated_profit.quantile(0.25, axis=1)
    accumulated_profit_stats['p50'] = all_accumulated_profit.quantile(0.50, axis=1)
    accumulated_profit_stats['p75'] = all_accumulated_profit.quantile(0.75, axis=1)

    # ... revenue percentiles ...
    revenue_stats['p25'] = all_revenue.quantile(0.25, axis=1)
    revenue_stats['p50'] = all_revenue.quantile(0.50, axis=1) # Median
    revenue_stats['p75'] = all_revenue.quantile(0.75, axis=1)

    tx_cost_stats['p25'] = all_tx_costs.quantile(0.25, axis=1)
    tx_cost_stats['p50'] = all_tx_costs.quantile(0.50, axis=1)
    tx_cost_stats['p75'] = all_tx_costs.quantile(0.75, axis=1)

    interest_cost_stats['p25'] = all_interest_costs.quantile(0.25, axis=1)
    interest_cost_stats['p50'] = all_interest_costs.quantile(0.50, axis=1)
    interest_cost_stats['p75'] = all_interest_costs.quantile(0.75, axis=1)

    # Combine stats
    summary_stats = pd.concat([
        asset_stats.add_prefix('Assets_'),
        accumulated_profit_stats.add_prefix('AccumulatedProfit_'),
        revenue_stats.add_prefix('Revenue_'),
        tx_cost_stats.add_prefix('AccumulatedTxCosts_'),
        interest_cost_stats.add_prefix('AccumulatedInterestCosts_')
    ], axis=1)

    # Reorder columns
    asset_cols = ['Assets_mean', 'Assets_std', 'Assets_min', 'Assets_p25', 'Assets_p50', 'Assets_p75', 'Assets_max']
    accumulated_profit_cols = ['AccumulatedProfit_mean', 'AccumulatedProfit_std', 'AccumulatedProfit_min', 'AccumulatedProfit_p25', 'AccumulatedProfit_p50', 'AccumulatedProfit_p75', 'AccumulatedProfit_max']
    revenue_cols = ['Revenue_mean', 'Revenue_std', 'Revenue_min', 'Revenue_p25', 'Revenue_p50', 'Revenue_p75', 'Revenue_max']
    tx_cost_cols = ['AccumulatedTxCosts_mean', 'AccumulatedTxCosts_std', 'AccumulatedTxCosts_min', 'AccumulatedTxCosts_p25', 'AccumulatedTxCosts_p50', 'AccumulatedTxCosts_p75', 'AccumulatedTxCosts_max']
    interest_cost_cols = ['AccumulatedInterestCosts_mean', 'AccumulatedInterestCosts_std', 'AccumulatedInterestCosts_min', 'AccumulatedInterestCosts_p25', 'AccumulatedInterestCosts_p50', 'AccumulatedInterestCosts_p75', 'AccumulatedInterestCosts_max']
    summary_stats = summary_stats[asset_cols + accumulated_profit_cols + revenue_cols + tx_cost_cols + interest_cost_cols]

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
        renovation_cost_per_sqm_ke=0.5, # Example value
        project_duration_months=9,
        financing_ratio_percent=90.0,
        interest_rate_percent=5.0,
        tax_rate_percent=29.125, # Example value from sheet
        hausgeld_total_per_project_ke=0.0, # Example value
        land_transfer_tax_percent=0.0, # Example value
        notary_fee_percent=0.0, # Example value
        agent_fee_purchase_percent=0.0, # Example value
        agent_fee_sale_percent=0.0, # Example value
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