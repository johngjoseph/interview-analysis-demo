"""
Partial ETL - Fetch and save stages + interview plans data
Run this to update stages and interview_plans tables without re-running the full ETL.
"""
import duckdb
import pandas as pd
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from etl import AshbyAPI, ASHBY_API_KEY, DB_PATH, transform_stages

def run_stages_only():
    print("=" * 60)
    print("Partial ETL - Fetching STAGES + INTERVIEW PLANS")
    print("=" * 60)
    
    if not ASHBY_API_KEY:
        print("❌ No ASHBY_API_KEY set")
        return
    
    api = AshbyAPI(ASHBY_API_KEY)
    
    # First fetch interview plans (needed for stages AND useful as a table)
    print("\n📥 Fetching interview plans...")
    plans = api.get_interview_plans()
    
    if not plans:
        print("❌ No interview plans returned")
        return
    
    print(f"   ✅ Fetched {len(plans)} interview plans")
    
    # Transform plans to DataFrame
    plans_data = []
    for plan in plans:
        # Try to extract department from plan title
        title = plan.get('title', 'Unknown')
        
        # Common patterns: "Engineering - Backend", "Sales Leader (SF/NY)"
        department = 'Unknown'
        if 'Engineering' in title or 'Engineer' in title:
            department = 'Engineering'
        elif 'Sales' in title:
            department = 'Sales'
        elif 'Product' in title:
            department = 'Product'
        elif 'Design' in title:
            department = 'Design'
        elif 'Marketing' in title:
            department = 'Marketing'
        elif 'People' in title or 'HR' in title or 'Recruiting' in title:
            department = 'People'
        elif 'Finance' in title or 'Legal' in title or 'G&A' in title:
            department = 'G&A'
        elif 'Data' in title:
            department = 'Data'
        elif 'Research' in title:
            department = 'Research'
        
        plans_data.append({
            'id': plan.get('id'),
            'title': title,
            'department_inferred': department,
            'is_active': plan.get('isActive', True)
        })
    
    plans_df = pd.DataFrame(plans_data)
    print(f"   Interview plans by inferred department:")
    print(plans_df['department_inferred'].value_counts().to_string())
    
    # Fetch stages using the fixed method (which uses plans internally)
    print("\n📥 Fetching interview stages...")
    stages = api.get_interview_stages()
    
    if not stages:
        print("❌ No stages returned")
        return
    
    print(f"   ✅ Fetched {len(stages)} stages")
    
    # Transform to DataFrame
    stages_df = transform_stages(stages)
    
    # Save to DuckDB
    print(f"\n💾 Saving to DuckDB: {DB_PATH}")
    
    conn = duckdb.connect(str(DB_PATH))
    
    # Save interview_plans table
    conn.register('temp_plans', plans_df)
    conn.execute("CREATE OR REPLACE TABLE interview_plans AS SELECT * FROM temp_plans")
    
    # Save stages table  
    conn.register('temp_stages', stages_df)
    conn.execute("CREATE OR REPLACE TABLE stages AS SELECT * FROM temp_stages")
    
    # Verify
    plans_count = conn.execute("SELECT COUNT(*) FROM interview_plans").fetchone()[0]
    stages_count = conn.execute("SELECT COUNT(*) FROM stages").fetchone()[0]
    print(f"   ✅ interview_plans: {plans_count} rows saved")
    print(f"   ✅ stages: {stages_count} rows saved")
    
    # Show sample
    print("\n📋 Sample interview plans:")
    sample = conn.execute("SELECT id, title, department_inferred FROM interview_plans LIMIT 5").df()
    print(sample.to_string(index=False))
    
    print("\n📋 Sample stages with plan title:")
    sample2 = conn.execute("SELECT id, title, interview_plan_title FROM stages LIMIT 5").df()
    print(sample2.to_string(index=False))
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ Stages and Interview Plans data updated successfully!")
    print("=" * 60)
    print("\nYou can now join applications to stages to get department info:")
    print("  SELECT a.*, s.interview_plan_title, p.department_inferred")
    print("  FROM applications a")
    print("  JOIN stages s ON a.current_stage_id = s.id")
    print("  JOIN interview_plans p ON s.interview_plan_id = p.id")

if __name__ == "__main__":
    run_stages_only()

