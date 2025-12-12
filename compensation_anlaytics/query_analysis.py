"""
Interactive script for running analyses and executing SQL queries against compensation data.
Run: python query_analysis.py
"""
import duckdb
import pandas as pd
import numpy as np
from pathlib import Path
import science

# Setup paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / 'data'
DB_PATH = DATA_DIR / 'compensation_data.duckdb'

def load_data():
    """Load data from DuckDB"""
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}")
        print("   Run 'python etl.py' first to generate data.")
        return None
    
    conn = duckdb.connect(str(DB_PATH))
    return conn

def run_all_analyses(conn):
    """Run all predefined analyses"""
    print("\n" + "="*80)
    print("RUNNING ALL ANALYSES")
    print("="*80)
    
    # Load dataframes for analysis functions
    ats_df = conn.execute("SELECT * FROM ats_data").df()
    emp_df = conn.execute("SELECT * FROM employee_data").df()
    interview_df = conn.execute("SELECT * FROM interview_load").df()
    
    print("\n1️⃣ RECRUITING PIPELINE HEALTH")
    print("-" * 80)
    accepted = len(ats_df[ats_df['status'] == 'Accepted'])
    total = len(ats_df)
    win_rate = accepted / total if total > 0 else 0
    avg_base = ats_df['offer_base'].mean()
    
    print(f"   Offers Accepted: {accepted:,} / {total:,}")
    print(f"   Win Rate: {win_rate:.1%}")
    print(f"   Avg Base Salary: ${avg_base:,.0f}")
    
    # Decline reasons breakdown
    rejected = ats_df[ats_df['status'] == 'Rejected']
    if len(rejected) > 0:
        decline_reasons = rejected['decline_reason'].value_counts()
        print(f"\n   Top Decline Reasons:")
        for reason, count in decline_reasons.head(5).items():
            print(f"      {reason}: {count} ({count/len(rejected):.1%})")
    
    print("\n2️⃣ PRICE ELASTICITY ANALYSIS")
    print("-" * 80)
    sample_offers = [300000, 400000, 500000, 600000]
    print("   Win Probability by Offer Amount:")
    for offer in sample_offers:
        prob = science.calculate_win_probability(ats_df, offer)
        print(f"      ${offer:,}: {prob:.1%}")
    
    print("\n3️⃣ INTERNAL EQUITY - COMPRESSION CHECK")
    print("-" * 80)
    # Check for compression: compare new hires vs veterans
    new_hires = emp_df[emp_df['years_tenure'] < 1]
    veterans = emp_df[emp_df['years_tenure'] >= 2]
    
    if len(new_hires) > 0 and len(veterans) > 0:
        new_hire_avg = new_hires['base_salary'].mean()
        veteran_avg = veterans['base_salary'].mean()
        compression_ratio = new_hire_avg / veteran_avg if veteran_avg > 0 else 1
        
        print(f"   New Hires (<1 year) Avg Salary: ${new_hire_avg:,.0f}")
        print(f"   Veterans (≥2 years) Avg Salary: ${veteran_avg:,.0f}")
        print(f"   Compression Ratio: {compression_ratio:.2f}")
        if compression_ratio > 1.05:
            print("   ⚠️  WARNING: New hires paid significantly more than veterans (compression risk)")
    
    # Level distribution
    print("\n   Headcount by Level:")
    level_dist = emp_df['level'].value_counts().sort_index()
    for level, count in level_dist.items():
        pct = count / len(emp_df) * 100
        print(f"      {level}: {count} ({pct:.1f}%)")
    
    print("\n4️⃣ MARKET COMPETITIVENESS")
    print("-" * 80)
    # Compa-ratio analysis
    low_compa = emp_df[emp_df['compa_ratio'] < 0.9]
    high_compa = emp_df[emp_df['compa_ratio'] > 1.1]
    
    print(f"   Employees Below Market (<0.9): {len(low_compa)} ({len(low_compa)/len(emp_df):.1%})")
    print(f"   Employees Above Market (>1.1): {len(high_compa)} ({len(high_compa)/len(emp_df):.1%})")
    print(f"   Average Compa-Ratio: {emp_df['compa_ratio'].mean():.2f}")
    
    # By department
    print("\n   Avg Compa-Ratio by Department:")
    dept_compa = emp_df.groupby('department')['compa_ratio'].mean().sort_values(ascending=False)
    for dept, ratio in dept_compa.items():
        print(f"      {dept}: {ratio:.2f}")
    
    print("\n5️⃣ EQUITY BURN FORECAST")
    print("-" * 80)
    pool_result = conn.execute("SELECT * FROM equity_pool WHERE metric = 'Remaining'").df()
    remaining_pool = pool_result['shares'].iloc[0] if len(pool_result) > 0 else 20000000
    
    # Forecast
    months = 24
    hires_per_month = 800 / 24
    shares_per_hire = 15000
    months_to_exhaustion = remaining_pool / (hires_per_month * shares_per_hire)
    
    print(f"   Remaining Pool: {remaining_pool:,} shares")
    print(f"   Projected Hires/Month: {hires_per_month:.1f}")
    print(f"   Avg Shares per Hire: {shares_per_hire:,}")
    print(f"   Months Until Exhaustion: {months_to_exhaustion:.1f}")
    if months_to_exhaustion < 24:
        print(f"   ⚠️  WARNING: Pool will be exhausted before 24 months!")
    
    print("\n6️⃣ INTERVIEWER CAPACITY MODEL")
    print("-" * 80)
    total_hours, impact = science.predict_burnout(interview_df, hiring_target=800)
    print(f"   Projected Engineering Hours Needed: {total_hours:,.0f}")
    print(f"   Capacity Impact: {impact:.1%}")
    print(f"   Current Weekly Avg: {interview_df['total_eng_hours'].mean():.0f} hours")
    
    if impact > 1.0:
        print(f"   ⚠️  WARNING: Capacity exceeded by {(impact-1)*100:.0f}%")
    
    print("\n" + "="*80)

def execute_sql_query(conn, query):
    """Execute a SQL query and return results"""
    try:
        result = conn.execute(query).df()
        return result
    except Exception as e:
        print(f"❌ SQL Error: {e}")
        return None

def interactive_mode(conn):
    """Interactive SQL query mode"""
    print("\n" + "="*80)
    print("INTERACTIVE SQL QUERY MODE")
    print("="*80)
    print("\nAvailable tables:")
    print("  - ats_data (offers, candidates, decline reasons)")
    print("  - employee_data (current employees, compa-ratios)")
    print("  - market_benchmarks (market salary data)")
    print("  - equity_pool (equity pool metrics)")
    print("  - interview_load (weekly interview data)")
    print("\nType SQL queries (or 'exit' to quit, 'help' for example queries)")
    print("-" * 80)
    
    example_queries = {
        "top_depts": """
            SELECT department, 
                   COUNT(*) as offers,
                   AVG(offer_base) as avg_base,
                   SUM(CASE WHEN status = 'Accepted' THEN 1 ELSE 0 END) as accepted
            FROM ats_data
            GROUP BY department
            ORDER BY offers DESC
        """,
        "compression_by_level": """
            SELECT level,
                   AVG(CASE WHEN years_tenure < 1 THEN base_salary END) as new_hires,
                   AVG(CASE WHEN years_tenure >= 2 THEN base_salary END) as veterans,
                   AVG(base_salary) as overall_avg
            FROM employee_data
            GROUP BY level
            ORDER BY level
        """,
        "win_rate_by_source": """
            SELECT source,
                   COUNT(*) as total_offers,
               SUM(CASE WHEN status = 'Accepted' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as win_rate_pct
            FROM ats_data
            GROUP BY source
            ORDER BY win_rate_pct DESC
        """,
        "market_gaps": """
            SELECT e.department, e.level,
                   AVG(e.base_salary) as avg_salary,
                   AVG(m.market_p50_cash) as market_p50,
                   AVG(e.compa_ratio) as avg_compa_ratio,
                   COUNT(*) as headcount
            FROM employee_data e
            JOIN market_benchmarks m ON e.department = m.department AND e.level = m.level
            GROUP BY e.department, e.level
            HAVING AVG(e.compa_ratio) < 0.95
            ORDER BY avg_compa_ratio ASC
        """
    }
    
    while True:
        try:
            query = input("\nSQL> ").strip()
            
            if query.lower() == 'exit':
                break
            elif query.lower() == 'help':
                print("\nExample queries:")
                for name, example in example_queries.items():
                    print(f"\n{name}:")
                    print(example)
                continue
            elif query.lower().startswith('example '):
                example_name = query.split(' ', 1)[1].strip()
                if example_name in example_queries:
                    query = example_queries[example_name]
                else:
                    print(f"Unknown example: {example_name}")
                    print(f"Available: {', '.join(example_queries.keys())}")
                    continue
            
            if not query:
                continue
            
            result = execute_sql_query(conn, query)
            if result is not None:
                print(f"\n{len(result)} rows returned:")
                print(result.to_string())
                
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except EOFError:
            break

def main():
    """Main entry point"""
    conn = load_data()
    if conn is None:
        return
    
    print("\n🎯 Compensation Analysis & SQL Query Tool")
    print("="*80)
    
    # Run all analyses
    run_all_analyses(conn)
    
    # Ask if user wants to run custom queries
    print("\nWould you like to run custom SQL queries? (y/n): ", end='')
    try:
        response = input().strip().lower()
        if response == 'y':
            interactive_mode(conn)
    except (KeyboardInterrupt, EOFError):
        pass
    
    conn.close()
    print("\n✅ Done!")

if __name__ == "__main__":
    main()

