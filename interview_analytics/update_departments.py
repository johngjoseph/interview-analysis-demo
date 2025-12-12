"""
Partial ETL - Fetch departments and jobs to enable department filtering
Run this to add department data without re-running the full ETL.
"""
import duckdb
import pandas as pd
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from etl import AshbyAPI, ASHBY_API_KEY, DB_PATH

def run_department_update():
    print("=" * 60)
    print("Partial ETL - Fetching DEPARTMENTS + JOBS")
    print("=" * 60)
    
    if not ASHBY_API_KEY:
        print("❌ No ASHBY_API_KEY set")
        return
    
    api = AshbyAPI(ASHBY_API_KEY)
    
    # Fetch departments
    print("\n📥 Fetching departments...")
    depts = api.get_departments()
    
    if not depts:
        print("❌ No departments returned")
        return
    
    print(f"   ✅ Fetched {len(depts)} departments")
    
    # Transform departments
    depts_df = pd.DataFrame([{
        'id': d.get('id'),
        'name': d.get('name', 'Unknown'),
        'parent_id': d.get('parentId')
    } for d in depts])
    
    print("   Departments:")
    for _, row in depts_df.iterrows():
        print(f"      - {row['name']}")
    
    # Fetch jobs
    print("\n📥 Fetching jobs...")
    jobs = api.get_jobs()
    
    if not jobs:
        print("❌ No jobs returned")
        return
    
    print(f"   ✅ Fetched {len(jobs)} jobs")
    
    # Transform jobs
    jobs_df = pd.DataFrame([{
        'id': j.get('id'),
        'title': j.get('title', 'Unknown'),
        'department_id': j.get('departmentId'),
        'status': j.get('status', 'Unknown'),
        'location': j.get('location', {}).get('name') if isinstance(j.get('location'), dict) else None
    } for j in jobs])
    
    # Join jobs with departments
    jobs_with_dept = jobs_df.merge(
        depts_df[['id', 'name']].rename(columns={'id': 'department_id', 'name': 'department_name'}),
        on='department_id',
        how='left'
    )
    jobs_with_dept['department_name'] = jobs_with_dept['department_name'].fillna('Unknown')
    
    print("\n📊 Jobs by department:")
    print(jobs_with_dept['department_name'].value_counts().to_string())
    
    # Save to DuckDB
    print(f"\n💾 Saving to DuckDB: {DB_PATH}")
    
    conn = duckdb.connect(str(DB_PATH))
    
    # Save departments table
    conn.register('temp_depts', depts_df)
    conn.execute("CREATE OR REPLACE TABLE departments AS SELECT * FROM temp_depts")
    
    # Save jobs table
    conn.register('temp_jobs', jobs_with_dept)
    conn.execute("CREATE OR REPLACE TABLE jobs AS SELECT * FROM temp_jobs")
    
    # Update applications with department info
    # Join applications → jobs → departments
    print("\n🔗 Updating applications with department info...")
    
    # First, ensure job_id column types match by casting
    conn.execute("""
        CREATE OR REPLACE TABLE applications AS
        SELECT 
            a.*,
            COALESCE(j.department_name, 'Unknown') as department_resolved,
            j.title as job_title_resolved
        FROM applications a
        LEFT JOIN jobs j ON CAST(a.job_id AS VARCHAR) = CAST(j.id AS VARCHAR)
    """)
    
    # Verify
    depts_count = conn.execute("SELECT COUNT(*) FROM departments").fetchone()[0]
    jobs_count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    print(f"   ✅ departments: {depts_count} rows saved")
    print(f"   ✅ jobs: {jobs_count} rows saved")
    
    # Show department distribution in applications
    print("\n📊 Applications by department (after update):")
    dept_dist = conn.execute("""
        SELECT department_resolved, COUNT(*) as count 
        FROM applications 
        GROUP BY department_resolved 
        ORDER BY count DESC
    """).df()
    print(dept_dist.to_string(index=False))
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ Department and Job data updated successfully!")
    print("=" * 60)
    print("\nNew columns added to applications:")
    print("  - department_resolved (from jobs → departments)")
    print("  - job_title_resolved (from jobs)")
    print("\nNew tables created:")
    print("  - departments (id, name, parent_id)")
    print("  - jobs (id, title, department_id, department_name, status, location)")

if __name__ == "__main__":
    run_department_update()

