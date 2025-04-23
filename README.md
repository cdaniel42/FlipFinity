# FlipFinity Business Simulator

A Flask API for simulating a capital-intensive, project-based business (like real estate flipping) using Monte Carlo methods.

## Overview

This application allows users to model their business by providing key financial parameters. It runs multiple simulations to account for uncertainty in project duration and margins, providing insights into potential long-term capital growth.

## Features

*   Monte Carlo simulation of business operations.
*   User-defined input parameters (capital, project details, financing, taxes).
*   Random variation in project duration and margin.
*   Calculation of average asset growth, standard deviation, and monthly gains.
*   Visualization of results using Plotly.

## API Endpoint

*   `POST /simulate`: Runs the simulation based on JSON input and returns results including Plotly graph JSON.

## How to Run

1.  Install dependencies: `pip install -r requirements.txt`
2.  Run the Flask app: `python app.py` 