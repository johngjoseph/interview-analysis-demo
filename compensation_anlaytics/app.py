import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import science
import os
import numpy as np
import duckdb
from pathlib import Path
from insights_manager import load_insights, save_insights

# Get script directory for data paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / 'data'

st.set_page_config(page_title="Cursor Talent Intelligence", layout="wide")
st.title("Cursor | Compensation Analysis")

# Load insights on startup
if 'insights' not in st.session_state:
    st.session_state.insights = load_insights()

def render_insights_section(tab_name, tab_display_name):
    """Render insights/narratives section for a tab"""
    st.markdown("---")
    st.markdown(f"### 💭 Insights & Notes: {tab_display_name}")
    
    # Get current insight
    current_insight = st.session_state.insights.get(tab_name, "")
    
    # Text area for input (supports markdown)
    insight_text = st.text_area(
        "Enter your insights, observations, or narrative (Markdown supported):",
        value=current_insight,
        height=150,
        help="You can use Markdown formatting:\n- **bold** for emphasis\n- *italic* for notes\n- ### Headers\n- - Bullet points\n- 1. Numbered lists",
        key=f"insight_{tab_name}"
    )
    
    # Display formatted markdown preview
    if insight_text.strip():
        st.markdown("**Preview:**")
        st.markdown(insight_text)
    
    # Save button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("💾 Save", key=f"save_{tab_name}"):
            st.session_state.insights[tab_name] = insight_text
            if save_insights(st.session_state.insights):
                st.success("✅ Saved!")
            else:
                st.error("❌ Failed to save")
    
    with col2:
        if st.button("🗑️ Clear", key=f"clear_{tab_name}"):
            st.session_state.insights[tab_name] = ""
            if save_insights(st.session_state.insights):
                st.rerun()

# --- DATA LOADING ---
ats_data_path = DATA_DIR / 'ats_data.parquet'
if not ats_data_path.exists():
    st.error("Data missing. Run 'python etl.py'")
    st.stop()

ats_df = pd.read_parquet(ats_data_path)
emp_df = pd.read_parquet(DATA_DIR / 'employee_data.parquet')
pool_df = pd.read_parquet(DATA_DIR / 'equity_pool.parquet')
interview_df = pd.read_parquet(DATA_DIR / 'interview_data.parquet')

# --- TABS ---
tab_health, tab_eff, tab_internal, tab_market, tab_finance, tab_ops, tab_sql = st.tabs([
    "📊 Talent Health", 
    "📉 Efficiency", 
    "⚖️ Internal Equity", 
    "🌍 Market Heatmap", 
    "💰 Equity Burn",
    "🔥 Ops Capacity",
    "🔍 SQL Query"
])

# --- TAB 1: HEALTH (New Win/Loss Chart) ---
with tab_health:
    st.markdown("### Recruiting Pipeline Health")
    
    # Department filter
    all_departments = sorted(ats_df['department'].unique().tolist())
    selected_departments = st.multiselect(
        "Filter by Department:",
        options=all_departments,
        default=all_departments,
        help="Select one or more departments to filter the data"
    )
    
    # Filter data based on selected departments
    filtered_df = ats_df[ats_df['department'].isin(selected_departments)] if selected_departments else ats_df
    
    k1, k2, k3 = st.columns(3)
    accepted_count = len(filtered_df[filtered_df['status']=='Accepted'])
    total_count = len(filtered_df)
    k1.metric("Offers Accepted", accepted_count)
    k2.metric("Win Rate", f"{accepted_count / total_count:.1%}" if total_count > 0 else "0%")
    k3.metric("Avg Base Salary", f"${filtered_df['offer_base'].mean():,.0f}" if len(filtered_df) > 0 else "$0")
    
    st.markdown("---")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**❌ Why do we lose candidates? (Win/Loss Analysis)**")
        # Filter for Rejections only
        loss_df = filtered_df[filtered_df['status'] == 'Rejected']
        if len(loss_df) > 0:
            fig_loss = px.histogram(loss_df, x='decline_reason', color='level', title="Rejection Reasons by Level",
                                   category_orders={"decline_reason": ["Equity Value", "Base Salary", "Remote Policy", "Competitor Brand", "Title"]})
            st.plotly_chart(fig_loss, use_container_width=True)
        else:
            st.info("No rejected offers in the selected departments.")
    with c2:
        st.markdown("**Hires by Source**")
        accepted_df = filtered_df[filtered_df['status']=='Accepted']
        if len(accepted_df) > 0:
            st.plotly_chart(px.histogram(accepted_df, x='source', color='department'), use_container_width=True)
        else:
            st.info("No accepted offers in the selected departments.")
    
    st.markdown("---")
    
    # Company Lost To Graph
    st.markdown("**🏢 Companies We Lost Candidates To**")
    loss_df = filtered_df[filtered_df['status'] == 'Rejected']
    if len(loss_df) > 0 and 'company_lost_to' in loss_df.columns:
        company_loss_counts = loss_df['company_lost_to'].value_counts().head(10)
        if len(company_loss_counts) > 0:
            fig_companies = px.bar(
                x=company_loss_counts.values,
                y=company_loss_counts.index,
                orientation='h',
                title="Top Companies We Lost Candidates To",
                labels={'x': 'Number of Lost Candidates', 'y': 'Company'},
                color=company_loss_counts.values,
                color_continuous_scale='Reds'
            )
            fig_companies.update_layout(showlegend=False, yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_companies, use_container_width=True)
            
            # Summary stats
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Lost to Competitors", len(loss_df[loss_df['company_lost_to'].notna()]))
            col2.metric("Unique Companies", loss_df['company_lost_to'].nunique())
            col3.metric("Top Competitor", company_loss_counts.index[0] if len(company_loss_counts) > 0 else "N/A")
        else:
            st.info("No company lost to data available for rejected offers.")
    else:
        st.info("No rejected offers in the selected departments or company_lost_to data not available.")
    
    st.markdown("---")
    
    # Accepted Offers Table
    st.markdown("**✅ Accepted Offers**")
    accepted_df = filtered_df[filtered_df['status'] == 'Accepted'].copy()
    
    if len(accepted_df) > 0:
        # Prepare table data
        if 'candidate_name' in accepted_df.columns:
            # Format date if it's a datetime
            if pd.api.types.is_datetime64_any_dtype(accepted_df['application_date']):
                accepted_df['date'] = accepted_df['application_date'].dt.strftime('%Y-%m-%d')
            else:
                accepted_df['date'] = accepted_df['application_date'].astype(str)
            
            # Select and rename columns
            table_df = accepted_df[['candidate_name', 'date', 'source']].copy()
            table_df.columns = ['Name', 'Date', 'Source']
            
            # Sort by date (most recent first)
            table_df = table_df.sort_values('Date', ascending=False)
            
            st.dataframe(
                table_df,
                use_container_width=True,
                height=400,
                hide_index=True
            )
            
            # Download button
            csv = table_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Accepted Offers as CSV",
                data=csv,
                file_name="accepted_offers.csv",
                mime="text/csv"
            )
        else:
            st.warning("Candidate name column not found in data. Please regenerate data with `python etl.py`")
    else:
        st.info("No accepted offers in the selected departments.")
    
    # Insights section
    render_insights_section("talent_health", "Talent Health")

# --- TAB 2: EFFICIENCY (Frontier) ---
with tab_eff:
    st.markdown("### Price Elasticity Analysis")
    
    # Department filter
    all_departments = sorted(ats_df['department'].unique().tolist())
    selected_departments = st.multiselect(
        "Filter by Department:",
        options=all_departments,
        default=all_departments,
        help="Select one or more departments to filter the data",
        key="eff_dept_filter"  # Unique key to avoid conflicts with other filters
    )
    
    # Filter data based on selected departments
    filtered_df_eff = ats_df[ats_df['department'].isin(selected_departments)] if selected_departments else ats_df
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### Offer Simulator")
        sim_val = st.slider("Total Offer Value ($)", 200000, 800000, 450000)
        prob = science.calculate_win_probability(filtered_df_eff, sim_val)
        st.metric("Predicted Win Probability", f"{prob:.1%}")
        st.info("💡 Insight: Reducing offer by $20k only drops win rate by 0.5%.")
    with col2:
        if len(filtered_df_eff) > 0:
            fig = px.scatter(filtered_df_eff, x="total_comp", y="status", color="status", title="Win/Loss Frontier", color_discrete_map={"Accepted": "green", "Rejected": "red"})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available for selected departments.")
    
    # Insights section
    render_insights_section("price_elasticity", "Price Elasticity")

# --- TAB 3: INTERNAL EQUITY (New Compression & Leveling) ---
with tab_internal:
    st.markdown("### ⚖️ Compression & Leveling Audit")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**1. Compression Check: Tenure vs. Cash**")
        st.caption("Look for 'Inversion' (dots sloping down). Are new hires (Left) paid more than veterans (Right)?")
        
        fig_comp = px.scatter(
            emp_df, 
            x="years_tenure", 
            y="base_salary", 
            color="level", 
            trendline="ols",
            title="Tenure vs. Base Salary (By Level)",
            labels={"years_tenure": "Years at Company", "base_salary": "Base Salary ($)"}
        )
        st.plotly_chart(fig_comp, use_container_width=True)
        
    with col2:
        st.markdown("**2. The 'Wild West' Leveling Audit**")
        st.caption("Do we have a 'Top Heavy' problem?")
        
        # Order levels
        level_order = ['L3', 'L4', 'L5', 'L6', 'L7']
        fig_lvl = px.histogram(
            emp_df, 
            x="level", 
            color="department", 
            category_orders={"level": level_order},
            title="Headcount Distribution by Level"
        )
        st.plotly_chart(fig_lvl, use_container_width=True)
    
    # Insights section
    render_insights_section("internal_equity", "Internal Equity")

# --- TAB 4: MARKET HEATMAP (New) ---
with tab_market:
    st.markdown("### 🌍 Market Competitiveness Heatmap")
    st.caption("Color = Avg Compa-Ratio (Salary / Market P50). Red (<0.9) = At Risk. Blue (>1.1) = Overpaying.")
    
    # Department filter
    all_departments_market = sorted(emp_df['department'].unique().tolist())
    selected_departments_market = st.multiselect(
        "Filter by Department:",
        options=all_departments_market,
        default=all_departments_market,
        help="Select one or more departments to filter the data",
        key="market_dept_filter"  # Unique key to avoid conflicts with other filters
    )
    
    # Filter employee data based on selected departments
    filtered_emp_df = emp_df[emp_df['department'].isin(selected_departments_market)] if selected_departments_market else emp_df
    
    # Aggregate data for heatmap
    if len(filtered_emp_df) > 0:
        heatmap_data = filtered_emp_df.groupby(['department', 'level'])['compa_ratio'].mean().reset_index()
        
        fig_heat = px.density_heatmap(
            heatmap_data, 
            x="department", 
            y="level", 
            z="compa_ratio", 
            text_auto=".2f",
            color_continuous_scale="RdBu",
            range_color=[0.8, 1.2], # Centered at 1.0
            title="Avg Compa-Ratio by Dept & Level"
        )
        st.plotly_chart(fig_heat, use_container_width=True)
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        avg_compa = filtered_emp_df['compa_ratio'].mean()
        below_market = len(filtered_emp_df[filtered_emp_df['compa_ratio'] < 0.9])
        above_market = len(filtered_emp_df[filtered_emp_df['compa_ratio'] > 1.1])
        
        col1.metric("Avg Compa-Ratio", f"{avg_compa:.2f}")
        col2.metric("Below Market (<0.9)", f"{below_market} ({below_market/len(filtered_emp_df)*100:.1f}%)" if len(filtered_emp_df) > 0 else "0")
        col3.metric("Above Market (>1.1)", f"{above_market} ({above_market/len(filtered_emp_df)*100:.1f}%)" if len(filtered_emp_df) > 0 else "0")
    else:
        st.info("No data available for selected departments.")
    
    # Insights section
    render_insights_section("market_heatmap", "Market Heatmap")

# --- TAB 5: EQUITY BURN (New) ---
with tab_finance:
    st.markdown("### 💰 Equity Cliff Forecast")
    
    # Department filter
    all_departments_finance = sorted(ats_df['department'].unique().tolist())
    selected_departments_finance = st.multiselect(
        "Filter by Department:",
        options=all_departments_finance,
        default=all_departments_finance,
        help="Select one or more departments to filter the forecast",
        key="finance_dept_filter"  # Unique key to avoid conflicts with other filters
    )
    
    # Filter offers data to calculate department-specific hiring rates
    filtered_ats_finance = ats_df[ats_df['department'].isin(selected_departments_finance)] if selected_departments_finance else ats_df
    
    # Calculate hiring rate based on filtered data (if we have historical data)
    # For now, we'll use a proportional approach based on department distribution
    if len(filtered_ats_finance) > 0:
        # Estimate hiring rate based on accepted offers in selected departments
        # This is a simplified approach - in real scenario, you'd use actual hiring targets
        total_accepted = len(ats_df[ats_df['status'] == 'Accepted'])
        filtered_accepted = len(filtered_ats_finance[filtered_ats_finance['status'] == 'Accepted'])
        department_ratio = filtered_accepted / total_accepted if total_accepted > 0 else 1.0
        
        # 1. Burn Chart
        # Forecast: Hiring 800 people total, adjusted for selected departments
        months = np.arange(1, 25)
        total_hiring_target = 800
        adjusted_hiring_target = total_hiring_target * department_ratio
        hires_per_month = adjusted_hiring_target / 24 # ~33 hires/mo (adjusted)
        shares_per_hire = 15000 # Avg grant size assumption
        
        burn_forecast = pd.DataFrame({
            'Month': months,
            'Cumulative Hires': months * hires_per_month,
            'Cumulative Shares Used': months * hires_per_month * shares_per_hire
        })
        
        # Total Pool Limit
        pool_limit = 20000000 # Remaining pool from ETL
        
        dept_label = ', '.join(selected_departments_finance) if selected_departments_finance else 'All Departments'
        fig_burn = px.line(burn_forecast, x='Month', y='Cumulative Shares Used', title=f"Projected Option Pool Usage (24 Months) - {dept_label}")
        fig_burn.add_hline(y=pool_limit, line_dash="dash", line_color="red", annotation_text="POOL EXHAUSTED")
        st.plotly_chart(fig_burn, use_container_width=True)
        
        # Calculate months until exhaustion
        months_to_exhaustion = pool_limit / (hires_per_month * shares_per_hire) if hires_per_month > 0 else float('inf')
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Projected Hires (24mo)", f"{adjusted_hiring_target:.0f}")
        col2.metric("Hires per Month", f"{hires_per_month:.1f}")
        col3.metric("Months Until Exhaustion", f"{int(months_to_exhaustion)}" if months_to_exhaustion < 1000 else "∞")
        
        if months_to_exhaustion < 24:
            st.error(f"🚨 At current grant rates, we run out of equity in Month {int(months_to_exhaustion)}. We need to resize grants or request a reload.")
        else:
            st.success(f"✅ Equity pool sufficient for {int(months_to_exhaustion)} months at current hiring rate.")
    else:
        st.info("No data available for selected departments.")
    
    # Insights section
    render_insights_section("equity_burn", "Equity Burn")

# --- TAB 6: OPS (Burnout) ---
with tab_ops:
    st.markdown("### ⚠️ Interviewer Capacity Model")
    total_hours, impact = science.predict_burnout(interview_df, hiring_target=800)
    st.error(f"🚨 PROJECTED LOAD: {total_hours:,.0f} Engineering Hours required.")
    st.progress(min(impact * 5, 1.0), text="Capacity Strain (Critical)")
    fig_int = px.bar(interview_df, x='week', y='total_eng_hours', title="Weekly Engineering Hours Spent Interviewing")
    st.plotly_chart(fig_int, use_container_width=True)
    
    # Insights section
    render_insights_section("ops_capacity", "Ops Capacity")

# --- TAB 7: SQL QUERY ---
with tab_sql:
    st.markdown("### 🔍 SQL Query Tool")
    st.markdown("Run custom SQL queries against your compensation data")
    
    # Load database connection
    db_path = DATA_DIR / 'compensation_data.duckdb'
    if not db_path.exists():
        st.error(f"❌ Database not found. Run `python etl.py` first to generate the data.")
        st.stop()
    
    conn = duckdb.connect(str(db_path))
    
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
                sample = conn.execute(f"SELECT * FROM {selected_table} LIMIT 1").df()
                if len(sample) > 0:
                    st.markdown("**Columns:**")
                    for col in sample.columns:
                        col_type = str(sample[col].dtype)
                        st.code(f"{col} ({col_type})", language=None)
                    
                    count = conn.execute(f"SELECT COUNT(*) as cnt FROM {selected_table}").df()['cnt'].iloc[0]
                    st.markdown(f"**Rows:** {count:,}")
                    
                    st.markdown("**Sample Data:**")
                    sample_data = conn.execute(f"SELECT * FROM {selected_table} LIMIT 5").df()
                    st.dataframe(sample_data, use_container_width=True)
            except Exception as e:
                st.error(f"Error loading table info: {e}")
        
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
       AVG(CASE WHEN years_tenure >= 2 THEN base_salary END) as veterans
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
            """
        }
        
        for name, query in example_queries.items():
            if st.button(f"📌 {name}", key=f"example_{name}"):
                st.session_state['sql_query'] = query.strip()
    
    # Main query interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        default_query = st.session_state.get('sql_query', '')
        query = st.text_area(
            "Enter your SQL query:",
            value=default_query,
            height=200,
            help="Write SQL queries against the available tables."
        )
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            run_query = st.button("▶️ Run Query", type="primary", use_container_width=True)
        with col_btn2:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state['sql_query'] = ''
                st.rerun()
    
    with col2:
        st.header("📊 Available Tables")
        for table in tables:
            with st.expander(f"📋 {table}"):
                try:
                    count = conn.execute(f"SELECT COUNT(*) as cnt FROM {table}").df()['cnt'].iloc[0]
                    st.markdown(f"**Rows:** {count:,}")
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
            
            # Download button
            csv = result_df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name="query_results.csv",
                mime="text/csv"
            )
            
            # Display results
            st.dataframe(result_df, use_container_width=True, height=400)
            
            # Summary stats
            numeric_cols = result_df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                with st.expander("📈 Summary Statistics"):
                    st.dataframe(result_df[numeric_cols].describe(), use_container_width=True)
        
        except Exception as e:
            st.error(f"❌ SQL Error: {str(e)}")
            st.info("💡 Tip: Check the schema navigator on the left to see available tables and columns.")
    
    conn.close()
    
    # Insights section
    render_insights_section("sql_query", "SQL Query")

