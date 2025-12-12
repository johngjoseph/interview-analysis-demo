#!/usr/bin/env python3
"""
Quick script to update candidate names by re-fetching applications.
Uses application.list with proper candidate parsing.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from etl import AshbyAPI
import duckdb
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "interview_analytics.duckdb"


def main():
    api_key = os.getenv('ASHBY_API_KEY')
    if not api_key:
        print("❌ ASHBY_API_KEY not set. Run: export ASHBY_API_KEY='your-key'")
        return
    
    api = AshbyAPI(api_key)
    
    # Fetch a small batch of applications to check structure
    print("Fetching applications to extract candidate names...")
    
    # Use pagination to get applications
    all_apps = api.get_applications()
    
    print(f"Fetched {len(all_apps)} applications")
    
    # Check first app structure
    if all_apps:
        first_app = all_apps[0]
        print(f"\nApplication keys: {list(first_app.keys())}")
        
        # Check if candidate is embedded
        if 'candidate' in first_app:
            candidate = first_app['candidate']
            print(f"Candidate embedded: {candidate}")
            print(f"Candidate name: {candidate.get('name', 'NOT FOUND')}")
        else:
            print("No 'candidate' key in application")
            print(f"candidateId: {first_app.get('candidateId')}")
    
    # Build update data
    updates = []
    for app in all_apps:
        app_id = app.get('id')
        
        # Try embedded candidate first
        candidate = app.get('candidate', {})
        if candidate:
            name = candidate.get('name')
            cand_id = candidate.get('id')
            if name:
                updates.append((name, cand_id, app_id))
    
    print(f"\nFound {len(updates)} applications with candidate names")
    
    if updates:
        print("Updating database...")
        conn = duckdb.connect(str(DB_PATH))
        
        for name, cand_id, app_id in updates:
            conn.execute("""
                UPDATE applications 
                SET candidate_name = ?, candidate_id = ?
                WHERE id = ?
            """, [name, cand_id, app_id])
        
        conn.commit()
        conn.close()
        print(f"✅ Updated {len(updates)} candidate names")
    else:
        print("No updates to apply - candidate data not found in API response")
        print("The application.list API may not include candidate details.")
        print("You may need to use application.info for each app (slow).")


if __name__ == "__main__":
    main()
