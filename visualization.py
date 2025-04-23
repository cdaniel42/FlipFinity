"""
File: visualization.py
Description: This module provides functions to generate visualizations (plots)
for the FlipFinity Business Simulator results using the Plotly library.
"""

import plotly.graph_objects as go
import pandas as pd
import numpy as np

def plot_asset_growth(summary_stats: pd.DataFrame) -> go.Figure:
    """
    Generates a Plotly figure showing the mean asset growth over time
    with a shaded region representing +/- 1 standard deviation.

    Args:
        summary_stats: DataFrame containing aggregated simulation results,
                       including 'Assets_mean' and 'Assets_std' columns,
                       indexed by month.

    Returns:
        A Plotly graph object (go.Figure).
    """
    fig = go.Figure()

    # Ensure standard deviation is non-negative
    summary_stats['Assets_std_non_negative'] = summary_stats['Assets_std'].fillna(0).clip(lower=0)

    # Calculate upper and lower bounds for the shaded area (+/- 1 std dev)
    upper_bound = summary_stats['Assets_mean'] + summary_stats['Assets_std_non_negative']
    lower_bound = summary_stats['Assets_mean'] - summary_stats['Assets_std_non_negative']

    # Add the shaded area for standard deviation
    # Need x values (months) for both lower and upper bounds
    x_months = summary_stats.index.tolist()
    fig.add_trace(go.Scatter(
        x=x_months + x_months[::-1], # x, then x reversed
        y=upper_bound.tolist() + lower_bound[::-1].tolist(), # upper, then lower reversed
        fill='toself',
        fillcolor='rgba(0,100,80,0.2)', # Example color, adjust as needed
        line=dict(color='rgba(255,255,255,0)'), # No border line for the fill
        hoverinfo="skip",
        showlegend=False,
        name='Std Dev Range'
    ))

    # Add the mean asset growth line
    fig.add_trace(go.Scatter(
        x=x_months,
        y=summary_stats['Assets_mean'],
        mode='lines',
        line=dict(color='rgb(0,100,80)'), # Example color
        name='Mean Assets'
    ))

    fig.update_layout(
        title='Simulated Asset Growth Over Time',
        xaxis_title='Month',
        yaxis_title='Total Assets (k€)',
        hovermode="x unified"
    )

    return fig

def plot_accumulated_profit(summary_stats: pd.DataFrame) -> go.Figure:
    """
    Generates a Plotly figure showing the mean accumulated profit after tax over time
    with a shaded region representing +/- 1 standard deviation.

    Args:
        summary_stats: DataFrame containing aggregated simulation results,
                       including 'AccumulatedProfit_mean' and 'AccumulatedProfit_std' columns,
                       indexed by month.

    Returns:
        A Plotly graph object (go.Figure).
    """
    fig = go.Figure()

    # Ensure standard deviation is non-negative
    summary_stats['AccumulatedProfit_std_non_negative'] = summary_stats['AccumulatedProfit_std'].fillna(0).clip(lower=0)

    # Calculate upper and lower bounds
    upper_bound = summary_stats['AccumulatedProfit_mean'] + summary_stats['AccumulatedProfit_std_non_negative']
    lower_bound = summary_stats['AccumulatedProfit_mean'] - summary_stats['AccumulatedProfit_std_non_negative']

    # Add shaded area
    x_months = summary_stats.index.tolist()
    fig.add_trace(go.Scatter(
        x=x_months + x_months[::-1],
        y=upper_bound.tolist() + lower_bound[::-1].tolist(),
        fill='toself',
        fillcolor='rgba(0, 176, 246, 0.2)', # Blue color
        line=dict(color='rgba(255,255,255,0)'),
        hoverinfo="skip",
        showlegend=False,
        name='Std Dev Range'
    ))

    # Add mean line
    fig.add_trace(go.Scatter(
        x=x_months,
        y=summary_stats['AccumulatedProfit_mean'],
        mode='lines',
        line=dict(color='rgb(0, 176, 246)'), # Blue color
        name='Mean Accumulated Profit'
    ))

    fig.update_layout(
        title='Simulated Accumulated Profit After Tax Over Time',
        xaxis_title='Month',
        yaxis_title='Accumulated Profit After Tax (k€)',
        hovermode="x unified"
    )

    return fig

def plot_monthly_revenue(summary_stats: pd.DataFrame) -> go.Figure:
    """
    Generates a Plotly figure showing the mean monthly revenue over time
    with a shaded region representing +/- 1 standard deviation.

    Args:
        summary_stats: DataFrame containing aggregated simulation results,
                       including 'Revenue_mean' and 'Revenue_std' columns,
                       indexed by month.

    Returns:
        A Plotly graph object (go.Figure).
    """
    fig = go.Figure()

    # Ensure standard deviation is non-negative
    summary_stats['Revenue_std_non_negative'] = summary_stats['Revenue_std'].fillna(0).clip(lower=0)

    # Calculate upper and lower bounds
    upper_bound = summary_stats['Revenue_mean'] + summary_stats['Revenue_std_non_negative']
    lower_bound = summary_stats['Revenue_mean'] - summary_stats['Revenue_std_non_negative']

    # Add shaded area
    x_months = summary_stats.index.tolist()
    fig.add_trace(go.Scatter(
        x=x_months + x_months[::-1],
        y=upper_bound.tolist() + lower_bound[::-1].tolist(),
        fill='toself',
        fillcolor='rgba(255, 165, 0, 0.2)', # Example color (orange)
        line=dict(color='rgba(255,255,255,0)'),
        hoverinfo="skip",
        showlegend=False,
        name='Std Dev Range'
    ))

    # Add mean line
    fig.add_trace(go.Scatter(
        x=x_months,
        y=summary_stats['Revenue_mean'],
        mode='lines',
        line=dict(color='rgb(255, 165, 0)'), # Example color (orange)
        name='Mean Monthly Revenue'
    ))

    fig.update_layout(
        title='Simulated Monthly Revenue Over Time',
        xaxis_title='Month',
        yaxis_title='Monthly Revenue (k€)',
        hovermode="x unified"
    )

    return fig

# Example Usage (for testing with dummy data)
if __name__ == '__main__':
    # Create dummy summary_stats data similar to what simulation.py produces
    months = range(1, 61)
    assets_mean = [60 + i * 1.5 + np.random.randn() * i * 0.1 for i in months]
    accumulated_profit_mean = np.cumsum([0.8 + np.random.randn() * 0.4 for i in months]) # Dummy profit accumulation
    dummy_data = {
        'Assets_mean': assets_mean,
        'Assets_std': [max(0, 5 + i * 0.5 + np.random.randn() * i * 0.05) for i in months],
        'AccumulatedProfit_mean': accumulated_profit_mean,
        'AccumulatedProfit_std': [max(0, 1 + i*0.1 + np.random.randn() * i*0.02) for i in range(len(months))],
        'Revenue_mean': [10 + i*0.2 + np.random.randn() * 2 for i in months],
        'Revenue_std': [max(0, 2 + np.random.randn() * 0.5) for i in months]
    }
    # Manually add percentile columns if needed for testing other functions that might rely on them
    # For simplicity, just creating the core mean/std columns here
    dummy_summary_stats = pd.DataFrame(dummy_data, index=pd.Index(months, name='Month'))

    print("Generating example plots...")

    # Generate and show Asset Growth plot
    asset_fig = plot_asset_growth(dummy_summary_stats)
    print("Asset Growth Plot JSON (first 500 chars):")
    print(asset_fig.to_json()[:500] + "...")
    # asset_fig.show()

    # Generate and show Accumulated Profit plot
    accumulated_profit_fig = plot_accumulated_profit(dummy_summary_stats)
    print("\nAccumulated Profit Plot JSON (first 500 chars):")
    print(accumulated_profit_fig.to_json()[:500] + "...")
    # accumulated_profit_fig.show()

    # Generate and show Monthly Revenue plot
    revenue_fig = plot_monthly_revenue(dummy_summary_stats)
    print("\nMonthly Revenue Plot JSON (first 500 chars):")
    print(revenue_fig.to_json()[:500] + "...")
    # revenue_fig.show() 