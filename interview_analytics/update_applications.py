#!/usr/bin/env python
"""Update applications table with corrected job/department parsing."""

import os
import sys
import json
import duckdb

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from etl import AshbyAPI, ASHBY_API_KEY, transform_applications

def main():
    if not ASHBY_API_KEY:
        print("❌ Error: ASHBY_API_KEY environment variable not set")
        sys.exit(1)
    
    api = AshbyAPI(ASHBY_API_KEY)
    
    # First, let's see the raw structure
    print("📥 Fetching sample application to check structure...")
    apps_sample = api.get_applications()[:3]
    
    if apps_sample:
        print("\n=== RAW APPLICATION STRUCTURE ===")
        for i, app in enumerate(apps_sample[:2]):
            print(f"\n--- App {i+1} ---")
            print(f"  id: {app.get('id')}")
            print(f"  job: {json.dumps(app.get('job'), indent=4) if app.get('job') else None}")
            print(f"  jobId: {app.get('jobId')}")
            print(f"  currentInterviewStage: {app.get('currentInterviewStage')}")
    
    # Fetch all data needed
    print("\n📥 Fetching all applications...")
    raw_applications = api.get_applications()
    print(f"   Found {len(raw_applications)} applications")
    
    if not raw_applications:
        print("❌ No applications returned. Check API key.")
        sys.exit(1)
    
    # Get departments and jobs for lookup
    print("📥 Fetching departments...")
    raw_departments = api.get_departments()
    print(f"   Found {len(raw_departments)} departments")
    
    print("📥 Fetching jobs...")
    raw_jobs = api.get_jobs()
    print(f"   Found {len(raw_jobs)} jobs")
    
    # Transform
    print("\n🔄 Transforming applications...")
    apps_df = transform_applications(raw_applications, [], raw_departments, raw_jobs)
    
    # Show sample
    print("\n📊 Sample of parsed applications:")
    print(apps_df[['job_id', 'job_title', 'department']].head(10).to_string())
    
    # Check department distribution
    print("\n📊 Department distribution:")
    print(apps_df['department'].value_counts().head(10).to_string())
    
    # Save to database
    print("\n💾 Saving to DuckDB...")
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'interview_analytics.duckdb')
    conn = duckdb.connect(db_path)
    
    # Drop and recreate applications table
    conn.execute("DROP TABLE IF EXISTS applications")
    conn.execute("CREATE TABLE applications AS SELECT * FROM apps_df")
    
    # Verify
    result = conn.execute("SELECT COUNT(*), COUNT(DISTINCT department) FROM applications").fetchone()
    print(f"   Saved {result[0]} rows with {result[1]} distinct departments")
    
    conn.close()
    print("✅ Applications table updated successfully!")

if __name__ == '__main__':
    main()

