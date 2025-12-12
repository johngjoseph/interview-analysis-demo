#!/usr/bin/env python
"""
Fetch application history from Ashby API.
This gives us the complete stage transition history for accurate funnel analysis.
"""

import os
import sys
import duckdb

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from etl import AshbyAPI, ASHBY_API_KEY, transform_application_history

def main():
    if not ASHBY_API_KEY:
        print("❌ Error: ASHBY_API_KEY environment variable not set")
        sys.exit(1)
    
    api = AshbyAPI(ASHBY_API_KEY)
    
    # Get application IDs from existing database (faster than re-fetching)
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'interview_analytics.duckdb')
    conn = duckdb.connect(db_path)
    
    print("📥 Getting application IDs from database...")
    app_ids = conn.execute("SELECT id FROM applications").fetchall()
    app_ids = [a[0] for a in app_ids]
    print(f"   Found {len(app_ids)} applications")
    
    # Limit for testing - remove this for full fetch
    # app_ids = app_ids[:100]  # Uncomment to test with first 100
    
    # Fetch history for all applications
    print("\n📥 Fetching application history from Ashby API...")
    print("   (This may take a while for large datasets...)")
    
    all_history = []
    batch_size = 50
    
    for i in range(0, len(app_ids), batch_size):
        batch = app_ids[i:i+batch_size]
        print(f"   Processing applications {i+1}-{min(i+batch_size, len(app_ids))} of {len(app_ids)}...")
        
        for app_id in batch:
            result = api._post('application.listHistory', {'applicationId': app_id})
            if result and result.get('results'):
                for entry in result.get('results', []):
                    entry['applicationId'] = app_id
                all_history.extend(result.get('results', []))
    
    print(f"\n✅ Fetched {len(all_history)} history entries")
    
    if not all_history:
        print("❌ No history data returned")
        sys.exit(1)
    
    # Show sample
    print("\n📊 Sample history entry:")
    import json
    print(json.dumps(all_history[0], indent=2, default=str))
    
    # Transform
    print("\n🔄 Transforming history data...")
    history_df = transform_application_history(all_history)
    
    print(f"\n📊 History DataFrame shape: {history_df.shape}")
    print("Sample rows:")
    print(history_df[['application_id', 'stage_name', 'entered_at']].head(10).to_string())
    
    # Save to database
    print("\n💾 Saving to DuckDB...")
    conn.execute("DROP TABLE IF EXISTS application_history")
    conn.execute("CREATE TABLE application_history AS SELECT * FROM history_df")
    
    # Show stage transition stats
    print("\n📊 Stage transition counts:")
    print(conn.execute("""
        SELECT stage_name, COUNT(*) as transitions
        FROM application_history
        GROUP BY stage_name
        ORDER BY transitions DESC
        LIMIT 15
    """).df().to_string())
    
    conn.close()
    print("\n✅ Application history table created successfully!")
    print("\nYou can now query stage transitions with:")
    print("  SELECT * FROM application_history WHERE application_id = 'xxx'")

if __name__ == '__main__':
    main()

