# Compensation Analytics Tool

A standalone analysis tool for compensation strategy analysis with SQL query capabilities.

## Setup

1. Install dependencies:
```bash
cd compensation_anlaytics
pip install -r requirements.txt
```

2. **If you have API keys**, set them as environment variables:
```bash
export ASHBY_API_KEY="your-api-key-here"
```

See `API_INTEGRATION.md` for detailed API integration instructions.

## Generate Fake Data

Since you're waiting on an API key, generate mock data:

```bash
python etl.py
```

This creates:
- Parquet files in `data/` directory (for Streamlit app)
- DuckDB database `data/compensation_data.duckdb` (for SQL queries)

run app
    cd compensation_anlaytics
    streamlit run app.py
    Opens in your browser at http://localhost:8501 with interactive charts and metrics.

How to use
Launch the dashboard:
cd compensation_anlayticsstreamlit run app.py
Click the "SQL Query" tab (7th tab)
Explore schema:
Use the sidebar dropdown to select a table
View columns, types, and sample data
Run queries:
Type SQL in the text area
Or click example query buttons
Click "Run Query"
View results below
Share with your colleague:
Share the URL (usually http://localhost:8501)
They can explore tables and run queries in their browser
## Run Analyses & SQL Queries

Run the interactive analysis and query tool:

```bash
python query_analysis.py
```

This will:
1. **Run all predefined analyses** automatically:
   - Recruiting pipeline health
   - Price elasticity analysis
   - Internal equity compression check
   - Market competitiveness
   - Equity burn forecast
   - Interviewer capacity model

2. **Interactive SQL mode** - Enter custom SQL queries against the data

### Available Tables

- `ats_data` - Offers, candidates, decline reasons
- `employee_data` - Current employees with compa-ratios
- `market_benchmarks` - Market salary benchmarks by dept/level
- `equity_pool` - Equity pool metrics
- `interview_load` - Weekly interview capacity data

### Example SQL Queries

In interactive mode, type `help` to see example queries, or try:

```sql
-- Top departments by offer volume
SELECT department, COUNT(*) as offers, AVG(offer_base) as avg_base
FROM ats_data
GROUP BY department
ORDER BY offers DESC;

-- Compression analysis by level
SELECT level,
       AVG(CASE WHEN years_tenure < 1 THEN base_salary END) as new_hires,
       AVG(CASE WHEN years_tenure >= 2 THEN base_salary END) as veterans
FROM employee_data
GROUP BY level;

-- Win rate by source
SELECT source,
       COUNT(*) as total,
       SUM(CASE WHEN status = 'Accepted' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as win_rate_pct
FROM ats_data
GROUP BY source;

-- Market gaps (underpaid employees)
SELECT e.department, e.level,
       AVG(e.base_salary) as avg_salary,
       AVG(m.market_p50_cash) as market_p50,
       AVG(e.compa_ratio) as avg_compa_ratio
FROM employee_data e
JOIN market_benchmarks m ON e.department = m.department AND e.level = m.level
GROUP BY e.department, e.level
HAVING AVG(e.compa_ratio) < 0.95;
```

## Launch Streamlit Dashboard

```bash
streamlit run app.py
```

The dashboard includes 7 tabs:
- **Talent Health** - Recruiting pipeline metrics and win/loss analysis
- **Efficiency** - Price elasticity and offer simulator
- **Internal Equity** - Compression and leveling audit
- **Market Heatmap** - Compa-ratio visualization
- **Equity Burn** - Equity pool forecast
- **Ops Capacity** - Interviewer capacity model
- **SQL Query** - Interactive SQL query tool with schema navigator ⭐ NEW!

### SQL Query Tab Features

- **Schema Navigator** (sidebar):
  - Browse all tables
  - View column names and types
  - See row counts
  - Preview sample data
  
- **Query Editor**:
  - Write and execute SQL queries
  - Example queries available
  - Results displayed in interactive table
  - Download results as CSV
  - Summary statistics for numeric columns

Perfect for exploring data and sharing insights with your team!

## Files

- `etl.py` - Data generation pipeline (generates mock data)
- `science.py` - Analysis functions (Monte Carlo, win probability, burnout)
- `app.py` - Streamlit dashboard
- `query_analysis.py` - Interactive analysis and SQL query tool
- `requirements.txt` - Python dependencies

