"""
Streamlit page for interactive SQL queries with schema navigator
Run: streamlit run sql_query.py
"""
import streamlit as st
import pandas as pd
import duckdb
from pathlib import Path

# Setup paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / 'data'
DB_PATH = DATA_DIR / 'compensation_data.duckdb'

st.set_page_config(page_title="SQL Query Tool", layout="wide")
st.title("🔍 SQL Query Tool")
st.markdown("Run custom SQL queries against your compensation data")

# Load database connection
@st.cache_resource
def get_db_connection():
    """Get cached database connection"""
    if not DB_PATH.exists():
        st.error(f"❌ Database not found at {DB_PATH}")
        st.info("Run `python etl.py` first to generate the data.")
        st.stop()
    return duckdb.connect(str(DB_PATH))

conn = get_db_connection()

# Sidebar with schema navigator
with st.sidebar:
    st.header("📊 Schema Navigator")
    
    # Get table list
    tables_result = conn.execute("SHOW TABLES").df()
    tables = tables_result['name'].tolist() if len(tables_result) > 0 else []
    
    selected_table = st.selectbox("Select a table:", [""] + tables)
    
    if selected_table:
        st.markdown(f"### Table: `{selected_table}`")
        
        # Get column info
        try:
            # Get sample data to infer columns
            sample = conn.execute(f"SELECT * FROM {selected_table} LIMIT 1").df()
            if len(sample) > 0:
                st.markdown("**Columns:**")
                for col in sample.columns:
                    col_type = str(sample[col].dtype)
                    st.code(f"{col} ({col_type})", language=None)
                
                # Show row count
                count = conn.execute(f"SELECT COUNT(*) as cnt FROM {selected_table}").df()['cnt'].iloc[0]
                st.markdown(f"**Rows:** {count:,}")
                
                # Show sample data
                st.markdown("**Sample Data:**")
                sample_data = conn.execute(f"SELECT * FROM {selected_table} LIMIT 5").df()
                st.dataframe(sample_data, use_container_width=True)
        except Exception as e:
            st.error(f"Error loading table info: {e}")
    
    st.markdown("---")
    st.markdown("### 📝 Quick Actions")
    
    if st.button("📋 Copy Table Name"):
        if selected_table:
            st.code(selected_table, language=None)
    
    st.markdown("---")
    st.markdown("### 💡 Example Queries")
    
    example_queries = {
        "Top Departments": """
SELECT department, 
       COUNT(*) as offers,
       AVG(offer_base) as avg_base,
       SUM(CASE WHEN status = 'Accepted' THEN 1 ELSE 0 END) as accepted
FROM ats_data
GROUP BY department
ORDER BY offers DESC
        """,
        "Compression Analysis": """
SELECT level,
       AVG(CASE WHEN years_tenure < 1 THEN base_salary END) as new_hires,
       AVG(CASE WHEN years_tenure >= 2 THEN base_salary END) as veterans,
       AVG(base_salary) as overall_avg
FROM employee_data
GROUP BY level
ORDER BY level
        """,
        "Win Rate by Source": """
SELECT source,
       COUNT(*) as total_offers,
       SUM(CASE WHEN status = 'Accepted' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as win_rate_pct
FROM ats_data
GROUP BY source
ORDER BY win_rate_pct DESC
        """,
        "Market Gaps": """
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
        """,
        "Decline Reasons": """
SELECT decline_reason,
       level,
       COUNT(*) as count,
       AVG(offer_base) as avg_offer_base
FROM ats_data
WHERE status = 'Rejected'
GROUP BY decline_reason, level
ORDER BY count DESC
        """
    }
    
    for name, query in example_queries.items():
        if st.button(f"📌 {name}", key=f"example_{name}"):
            st.session_state['sql_query'] = query.strip()

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.header("SQL Query")
    
    # Query input
    default_query = st.session_state.get('sql_query', '')
    query = st.text_area(
        "Enter your SQL query:",
        value=default_query,
        height=200,
        help="Write SQL queries against the available tables. Use the schema navigator on the left to explore tables."
    )
    
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        run_query = st.button("▶️ Run Query", type="primary", use_container_width=True)
    
    with col_btn2:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state['sql_query'] = ''
            st.rerun()
    
    with col_btn3:
        if st.button("💾 Save Query", use_container_width=True):
            if query:
                st.session_state['sql_query'] = query
                st.success("Query saved!")

with col2:
    st.header("📊 Available Tables")
    
    for table in tables:
        with st.expander(f"📋 {table}"):
            try:
                count = conn.execute(f"SELECT COUNT(*) as cnt FROM {table}").df()['cnt'].iloc[0]
                st.markdown(f"**Rows:** {count:,}")
                
                # Get column names
                sample = conn.execute(f"SELECT * FROM {table} LIMIT 0").df()
                st.markdown("**Columns:**")
                for col in sample.columns:
                    st.text(f"  • {col}")
            except:
                st.text("Click to explore")

# Execute query
if run_query and query:
    try:
        with st.spinner("Executing query..."):
            result_df = conn.execute(query).df()
        
        st.success(f"✅ Query executed successfully! Returned {len(result_df)} rows.")
        
        # Display results
        st.header("Query Results")
        
        # Show download button
        csv = result_df.to_csv(index=False)
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name="query_results.csv",
            mime="text/csv"
        )
        
        # Display dataframe
        st.dataframe(result_df, use_container_width=True, height=400)
        
        # Show summary stats for numeric columns
        numeric_cols = result_df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            with st.expander("📈 Summary Statistics"):
                st.dataframe(result_df[numeric_cols].describe(), use_container_width=True)
        
    except Exception as e:
        st.error(f"❌ SQL Error: {str(e)}")
        st.info("💡 Tip: Check the schema navigator on the left to see available tables and columns.")

# Footer
st.markdown("---")
st.markdown("💡 **Tip:** Use the schema navigator on the left to explore tables and columns. Click example queries to load them into the editor.")

