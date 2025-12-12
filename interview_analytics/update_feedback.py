#!/usr/bin/env python
"""Update only the feedback table with corrected parsing."""

import os
import sys
import duckdb

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from etl import AshbyAPI, ASHBY_API_KEY, transform_feedback

def main():
    if not ASHBY_API_KEY:
        print("❌ Error: ASHBY_API_KEY environment variable not set")
        sys.exit(1)
    
    api = AshbyAPI(ASHBY_API_KEY)
    
    # Fetch feedback 
    print("📥 Fetching feedback from API...")
    raw_feedback = api.get_application_feedback()
    print(f"   Found {len(raw_feedback)} feedback entries")
    
    if not raw_feedback:
        print("❌ No feedback data returned. Check your ASHBY_API_KEY.")
        sys.exit(1)
    
    # Transform with corrected parsing
    print("🔄 Transforming feedback with corrected parsing...")
    feedback_df = transform_feedback(raw_feedback, [])
    
    # Show sample of parsed data
    print("\n📊 Sample of parsed feedback:")
    sample_cols = ['overall_rating', 'vote', 'interviewer_name']
    print(feedback_df[sample_cols].head(5).to_string())
    
    print(f"\n✅ Non-null counts:")
    print(f"   overall_rating: {feedback_df['overall_rating'].notna().sum()}/{len(feedback_df)}")
    print(f"   vote: {feedback_df['vote'].notna().sum()}/{len(feedback_df)}")
    print(f"   feedback_text: {(feedback_df['feedback_text'] != '').sum()}/{len(feedback_df)}")
    
    # Save to database
    print("\n💾 Saving to DuckDB...")
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'interview_analytics.duckdb')
    conn = duckdb.connect(db_path)
    
    # Drop and recreate feedback table
    conn.execute("DROP TABLE IF EXISTS feedback")
    conn.execute("CREATE TABLE feedback AS SELECT * FROM feedback_df")
    
    # Verify
    result = conn.execute("SELECT COUNT(*), COUNT(overall_rating), COUNT(vote) FROM feedback").fetchone()
    print(f"   Saved {result[0]} rows, {result[1]} with ratings, {result[2]} with votes")
    
    conn.close()
    print("✅ Feedback table updated successfully!")

if __name__ == '__main__':
    main()

