import duckdb
import pandas as pd
import numpy as np
import os
import sys
import requests
import base64
from datetime import datetime, timedelta
from pathlib import Path

# --- CONFIGURATION ---
REAL_DATA_MODE = True
ASHBY_API_KEY = os.getenv("ASHBY_API_KEY", "")
print(ASHBY_API_KEY)

# Create data directory relative to script location
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / 'data'
DATA_DIR.mkdir(exist_ok=True)

def fetch_ashby_data():
    """
    Fetches real data from Ashby API.
    
    Returns:
        dict: Dictionary with keys 'ats_data', 'employees', 'market_df', 
              'equity_pool', 'interview_load' containing DataFrames, or None if API unavailable.
    """
    if not ASHBY_API_KEY:
        print("⚠️  No ASHBY_API_KEY found. Using mock data.")
        return None
    
    try:
        # TODO: Implement actual Ashby API calls here
        # Example structure:
        headers = {
            "Authorization": f"Basic {base64.b64encode(f'{ASHBY_API_KEY}:'.encode()).decode()}",
            "Content-Type": "application/json"
        }
        base_url = "https://api.ashbyhq.com"
        
        # Fetch interviews (Ashby API uses POST for all endpoints)
        interviews_response = requests.post(f"{base_url}/interview.list", headers=headers, json={})
        
        if interviews_response.status_code != 200:
            print(f"❌ API request failed with status {interviews_response.status_code}: {interviews_response.text}")
            return None
        
        interviews_data = interviews_response.json()
        
        # Check for API-level errors (Ashby returns 200 with success: False for some errors)
        if not interviews_data.get('success', False):
            print(f"❌ Ashby API error: {interviews_data}")
            print("💡 Make sure your API key has the 'interviewsRead' permission in Ashby settings")
            return None
            
        # Transform to DataFrame matching ats_data structure
        print("✅ Interviews fetched successfully:")
        print(interviews_data)
        sys.exit()
        # Fetch employees
        employees_response = requests.get(f"{base_url}/employees", headers=headers)
        # Transform to DataFrame matching employees structure
        
        return {
            'ats_data': ats_df,
            'employees': emp_df,
            'market_df': market_df,  # May need separate source
            'equity_pool': pool_df,  # May need separate source
            'interview_load': interview_df  # May need separate source
        }
        
        print("⚠️  API integration not yet implemented. Using mock data.")
        print("    See API_INTEGRATION.md for implementation guide.")
        return None
        
    except Exception as e:
        print(f"❌ Error fetching API data: {e}")
        print("⚠️  Falling back to mock data.")
        return None 

def generate_mock_data():
    """
    Generates rich mock data for ALL 10+ ANALYSES.
    """
    np.random.seed(42)
    n_offers = 1200
    n_employees = 350

    print("⚠️ Generating rich MOCK data for full suite...")

    # --- 1. ATS / RECRUITING DATA ---
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)
    dates = [start_date + timedelta(days=np.random.randint(0, 730)) for _ in range(n_offers)]
    
    # Define Departments & Roles
    depts = ['Engineering', 'Product', 'Sales', 'G&A', 'Design']
    levels = ['L3', 'L4', 'L5', 'L6', 'L7']
    
    # Generate candidate names
    first_names = ['Alex', 'Jordan', 'Taylor', 'Morgan', 'Casey', 'Riley', 'Avery', 'Quinn', 'Sage', 'River',
                   'Sam', 'Jamie', 'Dakota', 'Blake', 'Cameron', 'Drew', 'Emery', 'Finley', 'Hayden', 'Logan']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez',
                  'Hernandez', 'Lopez', 'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee']
    candidate_names = [f"{np.random.choice(first_names)} {np.random.choice(last_names)}" for _ in range(n_offers)]
    
    # Companies candidates went to (for rejected offers)
    competitor_companies = ['Google', 'Meta', 'Amazon', 'Microsoft', 'Apple', 'Netflix', 'Uber', 'Airbnb', 
                           'Stripe', 'Palantir', 'Databricks', 'Snowflake', 'OpenAI', 'Anthropic', 'Cohere']
    
    ats_data = pd.DataFrame({
        'candidate_id': range(n_offers),
        'candidate_name': candidate_names,
        'department': np.random.choice(depts, n_offers, p=[0.5, 0.15, 0.2, 0.1, 0.05]),
        'level': np.random.choice(levels, n_offers, p=[0.1, 0.3, 0.4, 0.15, 0.05]),
        'location': np.random.choice(['SF', 'London', 'Remote'], n_offers, p=[0.6, 0.2, 0.2]),
        'source': np.random.choice(['Referral', 'Inbound', 'Agency', 'Sourcing'], n_offers),
        'application_date': dates,
        'status': np.random.choice(['Accepted', 'Rejected'], n_offers, p=[0.88, 0.12]), 
    })
    
    # Assign Roles based on Dept
    ats_data['role'] = ats_data['department'] + " " + ats_data['level']
    
    # Generate Offers with Variance
    ats_data['offer_base'] = ats_data['level'].map({'L3': 140000, 'L4': 180000, 'L5': 240000, 'L6': 320000, 'L7': 400000}) * np.random.uniform(0.9, 1.2, n_offers)
    ats_data['offer_equity_4yr'] = ats_data['level'].map({'L3': 200000, 'L4': 400000, 'L5': 1000000, 'L6': 2500000, 'L7': 4000000}) * np.random.uniform(0.8, 1.5, n_offers)
    
    # Decline Reasons
    ats_data['decline_reason'] = ats_data.apply(
        lambda x: np.random.choice(['Base Salary', 'Equity Value', 'Remote Policy', 'Competitor Brand', 'Title']) if x['status'] == 'Rejected' else None, axis=1
    )
    
    # Companies candidates went to (for rejected offers)
    competitor_companies = ['Google', 'Meta', 'Amazon', 'Microsoft', 'Apple', 'Netflix', 'Uber', 'Airbnb', 
                           'Stripe', 'Palantir', 'Databricks', 'Snowflake', 'OpenAI', 'Anthropic', 'Cohere']
    ats_data['company_lost_to'] = ats_data.apply(
        lambda x: np.random.choice(competitor_companies) if x['status'] == 'Rejected' else None, axis=1
    )
    
    ats_data['total_comp'] = ats_data['offer_base'] + (ats_data['offer_equity_4yr'] / 4)
    ats_data['comp_quartile'] = pd.qcut(ats_data['total_comp'], 4, labels=['Q1', 'Q2', 'Q3', 'Q4'])

    # --- 2. EMPLOYEE DATA (Internal Equity) ---
    emp_dates = [end_date - timedelta(days=np.random.randint(30, 1500)) for _ in range(n_employees)]
    
    employees = pd.DataFrame({
        'employee_id': range(n_employees),
        'department': np.random.choice(depts, n_employees, p=[0.5, 0.15, 0.2, 0.1, 0.05]),
        'level': np.random.choice(levels, n_employees, p=[0.1, 0.3, 0.4, 0.15, 0.05]),
        'start_date': emp_dates,
        # Salary logic: Older employees might have lower base (Compression risk)
        'base_salary': 0, 
        'performance_rating': np.random.choice([1, 2, 3, 4, 5], n_employees)
    })
    
    # Simulate Salary Compression: Base salary grows 2% a year, but market grows 5%
    # So older employees (high tenure) have lower relative salary than new hires
    employees['years_tenure'] = (datetime.now() - employees['start_date']).dt.days / 365
    employees['market_base'] = employees['level'].map({'L3': 140000, 'L4': 180000, 'L5': 240000, 'L6': 320000, 'L7': 400000})
    
    # Apply tenure penalty (Mocking the compression issue)
    employees['base_salary'] = employees['market_base'] * (1 - (employees['years_tenure'] * 0.02)) * np.random.uniform(0.95, 1.05, n_employees)
    employees['total_cash'] = employees['base_salary'] # + Bonus if needed

    # --- 3. MARKET BENCHMARKS (External Equity) ---
    # Create benchmarks for every Level/Dept combo
    market_rows = []
    for d in depts:
        for l in levels:
            base_p50 = {'L3': 140000, 'L4': 180000, 'L5': 240000, 'L6': 320000, 'L7': 400000}[l]
            # Eng gets premium
            if d == 'Engineering': base_p50 *= 1.15
            
            market_rows.append({
                'department': d,
                'level': l,
                'market_p50_cash': base_p50,
                'market_p75_cash': base_p50 * 1.15
            })
    market_df = pd.DataFrame(market_rows)

    # --- 4. EQUITY POOL (Burn Forecast) ---
    # Total Pool: 50M shares. Used: 30M. Remaining: 20M.
    # We need to forecast usage.
    equity_pool = pd.DataFrame({
        'metric': ['Total Pool', 'Used', 'Remaining'],
        'shares': [50000000, 30000000, 20000000]
    })
    
    # --- 5. INTERVIEW LOAD ---
    weeks = pd.date_range(end=datetime.now(), periods=52, freq='W')
    interview_load = pd.DataFrame({
        'week': weeks,
        'onsite_interviews': np.random.randint(10, 50, 52),
        'hours_per_interview': 16 
    })
    interview_load['total_eng_hours'] = interview_load['onsite_interviews'] * interview_load['hours_per_interview']

    return ats_data, employees, market_df, equity_pool, interview_load

def run_pipeline():
    # Try to fetch real data first
    real_data = fetch_ashby_data()
    
    if real_data and REAL_DATA_MODE:
        print("✅ Using real API data")
        ats_df = real_data['ats_data']
        emp_df = real_data['employees']
        market_df = real_data['market_df']
        pool_df = real_data['equity_pool']
        interview_df = real_data['interview_load']
    else:
        print("⚠️  Using mock data")
        ats_df, emp_df, market_df, pool_df, interview_df = generate_mock_data()
    
    # Calculate Compa-Ratios for Heatmap
    # Join Employees with Market
    emp_merged = pd.merge(emp_df, market_df, on=['department', 'level'], how='left')
    emp_merged['compa_ratio'] = emp_merged['base_salary'] / emp_merged['market_p50_cash']
    
    # Save as parquet files
    ats_df.to_parquet(DATA_DIR / 'ats_data.parquet')
    emp_merged.to_parquet(DATA_DIR / 'employee_data.parquet') # Now includes market data + compa_ratio
    pool_df.to_parquet(DATA_DIR / 'equity_pool.parquet')
    interview_df.to_parquet(DATA_DIR / 'interview_data.parquet')
    
    # Also save to DuckDB for SQL queries
    db_path = DATA_DIR / 'compensation_data.duckdb'
    conn = duckdb.connect(str(db_path))
    
    # Register DataFrames as tables
    conn.register('ats_data', ats_df)
    conn.register('employee_data', emp_merged)
    conn.register('market_benchmarks', market_df)
    conn.register('equity_pool', pool_df)
    conn.register('interview_load', interview_df)
    
    # Create persistent tables
    conn.execute("CREATE OR REPLACE TABLE ats_data AS SELECT * FROM ats_data")
    conn.execute("CREATE OR REPLACE TABLE employee_data AS SELECT * FROM employee_data")
    conn.execute("CREATE OR REPLACE TABLE market_benchmarks AS SELECT * FROM market_benchmarks")
    conn.execute("CREATE OR REPLACE TABLE equity_pool AS SELECT * FROM equity_pool")
    conn.execute("CREATE OR REPLACE TABLE interview_load AS SELECT * FROM interview_load")
    
    conn.close()
    
    print("✅ Pipeline complete. All datasets generated.")
    print(f"📊 Data saved to DuckDB: {db_path}")
    print("   Tables: ats_data, employee_data, market_benchmarks, equity_pool, interview_load")

if __name__ == "__main__":
    run_pipeline()

