"""
File: app.py
Description: This file contains the main Flask application for the FlipFinity Business Simulator.
It defines the API endpoint to receive simulation parameters, run the simulation,
and return the results including visualizations.
"""

from flask import Flask, request, jsonify, render_template
import pandas as pd
import plotly.io as pio

# Import simulation and visualization functions from other modules
from simulation import run_monte_carlo_simulations
from visualization import plot_asset_growth, plot_monthly_gains

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@app.route('/simulate', methods=['POST'])
def simulate():
    """
    API endpoint to run the business simulation.
    Expects a JSON payload with simulation parameters.
    Returns a JSON response with summary statistics and plot JSON.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()

    # --- Input Parameter Validation ---
    required_params = [
        'starting_capital_ke', 'sqm_buy_value_ke', 'sqm_sell_value_ke', 'total_sqm',
        'project_duration_months', 'financing_ratio_percent', 'interest_rate_percent',
        'tax_rate_percent', 'duration_jitter_percent', 'sell_price_jitter_percent',
        'total_simulation_months', 'num_simulations'
    ]

    missing_params = [param for param in required_params if param not in data]
    if missing_params:
        return jsonify({"error": f"Missing required parameters: {', '.join(missing_params)}"}), 400

    # Basic type/value checks (can be expanded)
    try:
        params = {
            "starting_capital_ke": float(data['starting_capital_ke']),
            "sqm_buy_value_ke": float(data['sqm_buy_value_ke']),
            "sqm_sell_value_ke": float(data['sqm_sell_value_ke']),
            "total_sqm": float(data['total_sqm']),
            "project_duration_months": int(data['project_duration_months']),
            "financing_ratio_percent": float(data['financing_ratio_percent']),
            "interest_rate_percent": float(data['interest_rate_percent']),
            "tax_rate_percent": float(data['tax_rate_percent']),
            "duration_jitter_percent": float(data['duration_jitter_percent']),
            "sell_price_jitter_percent": float(data['sell_price_jitter_percent']),
            "total_simulation_months": int(data['total_simulation_months']),
            "num_simulations": int(data['num_simulations'])
        }

        # Add more specific validation if needed (e.g., non-negative values)
        if params['project_duration_months'] <= 0 or params['total_simulation_months'] <= 0 or params['num_simulations'] <= 0:
             raise ValueError("Durations and simulation count must be positive integers.")
        if params['total_sqm'] <= 0 or params['sqm_buy_value_ke'] <= 0:
             raise ValueError("Square meters and buy value must be positive.")

    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid parameter type or value: {e}"}), 400

    # --- Run Simulation ---
    try:
        print(f"Running simulation with params: {params}")
        simulation_results = run_monte_carlo_simulations(**params)
        summary_stats = simulation_results['summary_stats'] # This is a DataFrame
        print("Simulation complete.")
    except Exception as e:
        # Log the exception for debugging
        print(f"Error during simulation: {e}")
        # Consider logging traceback: import traceback; traceback.print_exc()
        return jsonify({"error": f"An error occurred during simulation: {e}"}), 500

    # --- Generate Visualizations ---
    try:
        print("Generating plots...")
        asset_growth_fig = plot_asset_growth(summary_stats)
        monthly_gains_fig = plot_monthly_gains(summary_stats)

        # Convert plots to JSON
        asset_plot_json = pio.to_json(asset_growth_fig)
        gains_plot_json = pio.to_json(monthly_gains_fig)
        print("Plots generated.")
    except Exception as e:
        print(f"Error during plot generation: {e}")
        return jsonify({"error": f"An error occurred during plot generation: {e}"}), 500

    # --- Prepare Response --- 
    # Extract final summary text
    final_month_stats = summary_stats.iloc[-1]
    summary_text = (
        f"After {params['total_simulation_months']} months, estimated final assets: "
        f"{final_month_stats['Assets_mean']:.2f} k€ (Std Dev: {final_month_stats['Assets_std']:.2f} k€). "
        f"Median final assets: {final_month_stats['Assets_p50']:.2f} k€."
    )

    response_data = {
        "summary_text": summary_text,
        "asset_growth_plot_json": asset_plot_json,
        "monthly_gains_plot_json": gains_plot_json,
        # Optionally include summary_stats DataFrame as JSON/dict
        # "summary_stats_json": summary_stats.reset_index().to_json(orient="records")
    }

    return jsonify(response_data)

if __name__ == '__main__':
    # Note: debug=True is helpful for development but should be False in production
    app.run(debug=True, host='0.0.0.0', port=5005) # Host 0.0.0.0 makes it accessible on Replit 