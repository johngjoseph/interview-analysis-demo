# API Integration Guide

Once you receive your API keys, follow these steps to integrate real data.

## Step 1: Set Your API Key

### Option A: Environment Variable (Recommended)
```bash
# macOS/Linux
export ASHBY_API_KEY="07ac2cc0a95a0cc022285ce6e4b7f360be6ea4f8a67ffd745f27de6d568abf55"

```

### Option B: Create a `.env` file
Create `compensation_anlaytics/.env`:
```
ASHBY_API_KEY=your-api-key-here
```

Then install python-dotenv (if not already installed):
```bash
pip install python-dotenv
```

And update `etl.py` to load it:
```python
from dotenv import load_dotenv
load_dotenv()
```

## Step 2: Implement `fetch_ashby_data()` Function

Update the `fetch_ashby_data()` function in `etl.py` to fetch real data from Ashby API.

### Example Implementation Structure

```python
def fetch_ashby_data():
    """
    Fetches real data from Ashby API.
    Returns a tuple of DataFrames matching the mock data structure.
    """
    if not ASHBY_API_KEY:
        print("⚠️  No API key found. Using mock data.")
        return None
    
    headers = {
        "Authorization": f"Basic {base64.b64encode(f'{ASHBY_API_KEY}:'.encode()).decode()}",
        "Content-Type": "application/json"
    }
    
    base_url = "https://api.ashbyhq.com"
    
    # Fetch offers/candidates data
    offers_data = []
    # Example: GET /offers endpoint
    # response = requests.get(f"{base_url}/offers", headers=headers)
    # Process response into DataFrame format
    
    # Fetch employee data
    employees_data = []
    # Example: GET /employees endpoint
    # response = requests.get(f"{base_url}/employees", headers=headers)
    
    # Fetch market benchmarks (may need separate API or keep as static)
    market_data = []
    
    # Fetch equity pool data
    equity_data = []
    
    # Fetch interview data
    interview_data = []
    
    # Return DataFrames matching the structure expected by run_pipeline()
    return {
        'ats_data': pd.DataFrame(offers_data),
        'employees': pd.DataFrame(employees_data),
        'market_df': pd.DataFrame(market_data),
        'equity_pool': pd.DataFrame(equity_data),
        'interview_load': pd.DataFrame(interview_data)
    }
```

### Required Data Structure

Your API data should map to these DataFrames:

#### 1. `ats_data` (Offers/Candidates)
Required columns:
- `candidate_id` - Unique candidate identifier
- `department` - Department name (Engineering, Product, Sales, etc.)
- `level` - Level (L3, L4, L5, L6, L7)
- `location` - Location (SF, London, Remote, etc.)
- `source` - Source (Referral, Inbound, Agency, Sourcing)
- `application_date` - Date of application
- `status` - Status ('Accepted' or 'Rejected')
- `role` - Role name (department + level)
- `offer_base` - Base salary offer
- `offer_equity_4yr` - 4-year equity value
- `decline_reason` - Reason for rejection (if rejected)
- `total_comp` - Total compensation
- `comp_quartile` - Compensation quartile (Q1-Q4)

#### 2. `employees` (Current Employees)
Required columns:
- `employee_id` - Unique employee identifier
- `department` - Department name
- `level` - Level
- `start_date` - Start date
- `base_salary` - Current base salary
- `years_tenure` - Years at company
- `performance_rating` - Performance rating (1-5)
- `total_cash` - Total cash compensation

#### 3. `market_benchmarks`
Required columns:
- `department` - Department name
- `level` - Level
- `market_p50_cash` - Market 50th percentile cash
- `market_p75_cash` - Market 75th percentile cash

#### 4. `equity_pool`
Required columns:
- `metric` - Metric name ('Total Pool', 'Used', 'Remaining')
- `shares` - Number of shares

#### 5. `interview_load`
Required columns:
- `week` - Week date
- `onsite_interviews` - Number of onsite interviews
- `hours_per_interview` - Hours per interview
- `total_eng_hours` - Total engineering hours

## Step 3: Update `run_pipeline()` Function

Modify `run_pipeline()` to use real data when available:

```python
def run_pipeline():
    # Try to fetch real data
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
    
    # Rest of the pipeline remains the same...
    # Calculate Compa-Ratios, save to parquet and DuckDB
```

## Step 4: Test the Integration

1. **Set your API key:**
   ```bash
   export ASHBY_API_KEY="your-key"
   ```

2. **Run the pipeline:**
   ```bash
   python etl.py
   ```

3. **Check the output:**
   - Look for "✅ Using real API data" message
   - Verify data files are created in `data/` directory
   - Check data quality in the Streamlit dashboard

## Step 5: Handle API Rate Limits & Errors

Add error handling to your `fetch_ashby_data()` function:

```python
def fetch_ashby_data():
    try:
        # Your API calls here
        pass
    except requests.exceptions.RequestException as e:
        print(f"❌ API Error: {e}")
        print("⚠️  Falling back to mock data")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None
```

## Step 6: Data Transformation

You may need to transform API responses to match the expected format:

```python
def transform_ashby_offer(api_response):
    """Transform Ashby API response to our format"""
    return pd.DataFrame({
        'candidate_id': api_response['id'],
        'department': api_response['department']['name'],
        'level': api_response['level'],
        # ... map other fields
    })
```

## Troubleshooting

### API Key Not Found
- Check environment variable: `echo $ASHBY_API_KEY`
- Verify `.env` file is in the correct location
- Restart your terminal/IDE after setting environment variables

### Data Format Mismatch
- Check column names match exactly (case-sensitive)
- Verify data types (dates, numbers, strings)
- Use `print(df.columns)` and `print(df.dtypes)` to debug

### Missing Data
- Some fields may be optional - handle None/null values
- Consider using mock data as fallback for missing fields

## Next Steps

1. Review Ashby API documentation for exact endpoint structure
2. Implement `fetch_ashby_data()` with your specific API calls
3. Test with small datasets first
4. Gradually expand to full data pipeline
5. Add data validation and error handling

## Need Help?

- Check Ashby API docs: https://developers.ashbyhq.com
- Review the mock data structure in `generate_mock_data()` as a reference
- Test queries in the SQL Query tab to verify data quality

