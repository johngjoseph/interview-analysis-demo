import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

# --- EXISTING FUNCTIONS ---
def run_monte_carlo_simulation(grant_value, simulations=10000):
    results = []
    for _ in range(simulations):
        scenario_roll = np.random.random()
        if scenario_roll < 0.10: multiplier = np.random.uniform(0, 0.5)
        elif scenario_roll < 0.60: multiplier = np.random.uniform(1.5, 3.5)
        elif scenario_roll < 0.90: multiplier = np.random.uniform(4.0, 6.0)
        else: multiplier = np.random.uniform(8.0, 15.0)
        results.append(grant_value * multiplier)
    return results

def calculate_win_probability(df, offer_amount):
    # Heuristic Fallback for Demo
    market_mid = 400000 
    k = 0.00002 
    probability = 1 / (1 + np.exp(-k * (offer_amount - market_mid)))
    return probability

def calculate_retention_risk(employees_df, market_df):
    """
    Identifies 'Vest in Peace' vs 'Flight Risk' employees.
    Risk Logic: Unvested Value / Market Replacement Grant
    """
    # Join employees with market data
    merged = pd.merge(employees_df, market_df, on='role', how='left')
    
    # Calculate Ratio
    # If Ratio > 2.0: They have 2x market value unvested. They won't leave (Vest in Peace).
    # If Ratio < 0.8: They have less unvested than a new hire gets. Flight Risk.
    merged['retention_ratio'] = merged['unvested_value'] / merged['market_new_hire_grant']
    
    merged['risk_category'] = merged.apply(
        lambda x: '🔒 Golden Handcuffs (Safe)' if x['retention_ratio'] > 1.5
        else ('⚠️ Flight Risk (Underwater)' if x['retention_ratio'] < 0.8 else 'Neutral'),
        axis=1
    )
    return merged

def predict_burnout(interview_df, hiring_target=800):
    """
    Project future engineering hours needed based on target.
    """
    avg_hours_per_hire = 40 # Heuristic: 2 days onsite + screens + debriefs
    total_hours_needed = hiring_target * avg_hours_per_hire
    
    # If we have 200 engineers, and they work 2000 hours a year
    total_capacity = 200 * 2000 
    burnout_impact = total_hours_needed / total_capacity
    return total_hours_needed, burnout_impact

