"""
Interview Analytics Dashboard
Streamlit application with 7 tabs for interview quality analysis.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import duckdb
import os
from pathlib import Path

# Import analysis functions
import science

# --- CONFIGURATION ---
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / 'data'
DB_PATH = DATA_DIR / 'interview_analytics.duckdb'

# Page config
st.set_page_config(
    page_title="Interview Analytics",
    page_icon="📊",
    layout="wide"
)

# --- CHECK DATA EXISTS ---
if not DB_PATH.exists():
    st.error("⚠️ Database not found. Please run the ETL pipeline first:")
    st.code("cd interview_analytics && python etl.py")
    st.stop()

# --- HEADER ---
st.title("📊 Interview Analytics Dashboard")

# Get summary stats
try:
    stats = science.get_summary_stats()
    
    # Key metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Applications", f"{stats['total_applications']:,}")
    col2.metric("Hired", f"{stats['total_hired']:,}")
    col3.metric("Hire Rate", f"{stats['overall_hire_rate']}%")
    col4.metric("Total Interviews", f"{stats['total_interviews']:,}")
    col5.metric("Interviewers", f"{stats['total_interviewers']:,}")
except Exception as e:
    st.warning(f"Could not load summary stats: {e}")

st.markdown("---")

# --- TABS ---
tab_summary, tab1, tab2, tab3, tab4, tab5, tab7 = st.tabs([
    "📋 Summary",
    "📈 Funnel Ratios",
    "🔍 Pre-Onsite Screening",
    "❓ False Negatives",
    "⚖️ Interviewer Calibration",
    "⚠️ False Positives",
    "🔎 SQL Query"
])

# =============================================================================
# SUMMARY TAB (First Tab)
# =============================================================================
with tab_summary:
    st.header("📋 Interview Analytics Summary")
    
    # Editable Approach Section
    st.subheader("📝 Approach")
    
    # Load approach from file
    approach_file = DATA_DIR / 'approach.md'
    
    # Toggle for edit mode
    edit_mode = st.toggle("✏️ Edit Approach", key="edit_approach")
    
    if approach_file.exists():
        current_approach = approach_file.read_text()
    else:
        current_approach = "# Approach\n\nDescribe your interview analytics approach here..."
    
    if edit_mode:
        new_approach = st.text_area(
            "Edit the approach document (Markdown supported):",
            value=current_approach,
            height=400,
            key="approach_editor"
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("💾 Save", key="save_approach"):
                approach_file.write_text(new_approach)
                st.success("Saved!")
                st.rerun()
        with col2:
            st.caption("Supports Markdown formatting")
    else:
        st.markdown(current_approach)
    
    st.markdown("---")
    
    # Key Metrics Summary
    st.subheader("📊 Key Metrics")
    
    try:
        conn = duckdb.connect(str(DB_PATH), read_only=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        total_apps = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        total_hired = conn.execute("SELECT COUNT(*) FROM applications WHERE status = 'Hired'").fetchone()[0]
        total_feedback = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
        
        # Check for history coverage
        has_history = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='application_history'").fetchone()[0] > 0
        if has_history:
            history_coverage = conn.execute("SELECT COUNT(DISTINCT application_id) FROM application_history").fetchone()[0]
        else:
            history_coverage = 0
        
        col1.metric("Total Applications", f"{total_apps:,}")
        col2.metric("Total Hired", f"{total_hired:,}")
        col3.metric("Feedback Entries", f"{total_feedback:,}")
        col4.metric("History Coverage", f"{history_coverage:,} / {total_apps:,}")
        
        conn.close()
        
    except Exception as e:
        st.error(f"Error loading metrics: {e}")
    
    st.markdown("---")
    
    # Recommendations Section
    st.subheader("💡 Key Recommendations")
    
    recommendations = [
        {
            "title": "🎯 Implement Additional Pre-Onsite Screens",
            "description": "Add culture fit assessment at the technical screen stage to be more discerning about who advances to onsite.",
            "priority": "High",
            "effort": "Medium"
        },
        {
            "title": "🔄 Refocus Onsite Interview Roles",
            "description": "At the onsite stage, everyone is currently assessing culture. Assign specific focus areas to each interviewer for better signal.",
            "priority": "High", 
            "effort": "Low"
        },
        {
            "title": "📊 Calibration Sessions for Hawks/Doves",
            "description": "Schedule regular calibration sessions for interviewers identified as statistical outliers.",
            "priority": "Medium",
            "effort": "Medium"
        },
        {
            "title": "🔍 Review False Negative Candidates",
            "description": "Have recruiters review archived candidates with high average ratings but single dissenting votes.",
            "priority": "Medium",
            "effort": "Low"
        }
    ]
    
    for rec in recommendations:
        with st.expander(f"{rec['title']} - Priority: {rec['priority']}"):
            st.markdown(rec['description'])
            col1, col2 = st.columns(2)
            col1.markdown(f"**Priority:** {rec['priority']}")
            col2.markdown(f"**Effort:** {rec['effort']}")
    
    st.markdown("---")
    
    # Notes Section
    st.subheader("📓 Your Notes")
    
    notes_file = DATA_DIR / 'notes.txt'
    current_notes = notes_file.read_text() if notes_file.exists() else ""
    
    notes = st.text_area(
        "Add your observations and action items:",
        value=current_notes,
        height=200,
        placeholder="Enter your notes here...",
        key="notes_area"
    )
    
    if st.button("💾 Save Notes", key="save_notes"):
        notes_file.write_text(notes)
        st.success("Notes saved!")

# =============================================================================
# TAB 1: FUNNEL RATIOS
# =============================================================================
with tab1:
    st.header("📈 Funnel Ratios")
    st.markdown("**Hypothesis:** For certain departments, there is a steep dropoff from Onsite to Offer stage.")
    
    # Department filter
    departments = ['All'] + science.get_departments()
    selected_dept = st.selectbox("Filter by Department:", departments, key="funnel_dept")
    
    dept_filter = None if selected_dept == 'All' else selected_dept
    
    try:
        funnel_data = science.calculate_funnel_ratios(dept_filter)
        
        # Metrics row
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Applications", f"{funnel_data['total_applications']:,}")
        col2.metric("Total Interview Hours", f"{funnel_data['total_interview_hours']:,.0f}")
        col3.metric("Avg Interview Duration", f"{funnel_data['avg_interview_duration']:.0f} min")
        col4.metric("Hours per Hire", f"{funnel_data['hours_per_hire']:.1f}")
        
        st.markdown("---")
        
        # Funnel visualization - Sankey Diagram
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📊 Interview Funnel")
            
            conn = duckdb.connect(str(DB_PATH), read_only=True)
            
            # Check if we have application_history table for accurate funnel
            has_history = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='application_history'").fetchone()[0] > 0
            
            if has_history:
                # Use accurate history-based funnel
                st.caption("*Using stage transition history*")
                
                dept_join = f"JOIN applications a ON h.application_id = a.id WHERE a.department = '{dept_filter}'" if dept_filter else ""
                
                # Count unique apps that reached each stage - consolidate onsite stages
                funnel_query = f"""
                SELECT 
                    CASE 
                        WHEN h.stage_name IN ('Onsite', 'All Around', 'Work Trial') THEN 'Onsite'
                        ELSE h.stage_name
                    END as stage_name,
                    COUNT(DISTINCT h.application_id) as reached
                FROM application_history h
                {dept_join}
                {'AND' if dept_filter else 'WHERE'} h.stage_name NOT IN ('Archived', 'Jordan 1:1')
                GROUP BY CASE 
                    WHEN h.stage_name IN ('Onsite', 'All Around', 'Work Trial') THEN 'Onsite'
                    ELSE h.stage_name
                END
                ORDER BY reached DESC
                """
                
                funnel_df = conn.execute(funnel_query).df()
                conn.close()
                
                if len(funnel_df) > 1:
                    # Define funnel order - ensures Onsite, Offer, Hired are included
                    stage_order = {
                        'New Lead': 0, 'Application Review': 1, 'Reached Out': 2, 
                        'Replied': 3, 'Intro Call': 4, 'Coding 1': 5, 
                        'Hiring Manager Screen': 6, 'Technical Interview 1': 7,
                        'Technical Interview 2': 8, 'Recruiter Screen': 9,
                        'Technical Deep Dive': 10, 'Coding 2': 11,
                        'Onsite': 12, 'All Around': 12, 'Work Trial': 12,
                        'Offer': 13, 'Hired': 14
                    }
                    funnel_df['order'] = funnel_df['stage_name'].map(lambda x: stage_order.get(x, 99))
                    
                    # Keep only stages in our defined order (drops misc stages)
                    funnel_df = funnel_df[funnel_df['order'] < 99]
                    funnel_df = funnel_df.sort_values('order')
                    
                    # Key funnel stages to always show (simplified view)
                    key_stages = ['New Lead', 'Application Review', 'Intro Call', 'Coding 1', 
                                   'Onsite', 'Offer', 'Hired']
                    
                    # Filter to key stages that exist in data
                    key_df = funnel_df[funnel_df['stage_name'].isin(key_stages)].copy()
                    key_df = key_df.sort_values('order')
                    
                    if len(key_df) > 0:
                        # Calculate metrics - use max as starting point for cumulative %
                        max_stage_count = key_df['reached'].max()
                        key_df['cumulative_pct'] = (key_df['reached'] / max_stage_count * 100).round(1)
                        
                        # Dropoff = how many dropped from previous stage
                        key_df['dropoff'] = key_df['reached'].shift(1) - key_df['reached']
                        key_df['dropoff'] = key_df['dropoff'].fillna(0).astype(int)
                        
                        # Stage Conv = % that made it TO the next stage (shift -1 to show next/current)
                        key_df['stage_conversion'] = (key_df['reached'].shift(-1) / key_df['reached'] * 100).round(1)
                        key_df['stage_conversion'] = key_df['stage_conversion'].fillna(0)  # Last row has no next
                        
                        # Create horizontal funnel bar chart
                        import plotly.graph_objects as go
                        
                        fig = go.Figure()
                        
                        # Add horizontal bars
                        fig.add_trace(go.Bar(
                            y=key_df['stage_name'],
                            x=key_df['reached'],
                            orientation='h',
                            marker=dict(
                                color='#3498db',
                                line=dict(color='#2980b9', width=1)
                            ),
                            text=[f"{c:,}" for c in key_df['reached']],
                            textposition='inside',
                            textfont=dict(color='white', size=14),
                            hovertemplate='%{y}<br>Candidates: %{x:,}<extra></extra>'
                        ))
                        
                        fig.update_layout(
                            title_text="Candidates Who Reached Each Stage",
                            xaxis_title="Number of Candidates",
                            yaxis=dict(autorange="reversed"),  # Top to bottom
                            height=400,
                            showlegend=False,
                            margin=dict(l=150, r=20, t=40, b=40)
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Show detailed table below
                        st.markdown("**Funnel Metrics:**")
                        display_df = key_df[['stage_name', 'reached', 'cumulative_pct', 'dropoff', 'stage_conversion']].copy()
                        display_df.columns = ['Stage', 'Candidates', 'Cumulative %', 'Dropoff', 'Stage Conv %']
                        st.dataframe(
                            display_df,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                'Candidates': st.column_config.NumberColumn(format="%d"),
                                'Cumulative %': st.column_config.NumberColumn(format="%.1f%%"),
                                'Dropoff': st.column_config.NumberColumn(format="▼ %d"),
                                'Stage Conv %': st.column_config.NumberColumn(format="%.1f%%")
                            }
                        )
                    else:
                        st.info("No funnel data available")
                else:
                    st.info("Not enough stage data for Sankey diagram")
            else:
                # Fallback to current_stage based view
                st.caption("*Based on current stage (run update_history.py for accurate funnel)*")
                dept_where = f"WHERE department = '{dept_filter}'" if dept_filter else ""
                
                stage_query = f"""
                SELECT current_stage_name as stage, COUNT(*) as count
                FROM applications
                {dept_where}
                GROUP BY current_stage_name
                ORDER BY count DESC
                LIMIT 10
                """
                stage_df = conn.execute(stage_query).df()
                conn.close()
                
                if len(stage_df) > 0:
                    fig = px.bar(stage_df, x='stage', y='count', title="Current Stage Distribution")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No stage data available")
        
        # Onsite → Offer Dropoff Analysis (using application_history for accuracy)
        st.markdown("---")
        st.subheader("🚨 Onsite → Offer Dropoff Analysis")
        
        conn = duckdb.connect(str(DB_PATH), read_only=True)
        
        # Check if we have application_history table
        has_history = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='application_history'").fetchone()[0] > 0
        
        if has_history:
            # Use accurate history-based calculation
            st.caption("📊 *Using stage transition history for accurate funnel*")
            
            # Join with applications for department filter
            dept_join = f"JOIN applications a ON h.application_id = a.id WHERE a.department = '{dept_filter}'" if dept_filter else ""
            
            try:
                # Count unique apps that reached each stage
                reached_onsite = conn.execute(f"""
                    SELECT COUNT(DISTINCT h.application_id) 
                    FROM application_history h
                    {dept_join}
                    {'AND' if dept_filter else 'WHERE'} (h.stage_name ILIKE '%onsite%' 
                        OR h.stage_name = 'All Around'
                        OR h.stage_name = 'Work Trial')
                """).fetchone()[0]
                
                reached_offer = conn.execute(f"""
                    SELECT COUNT(DISTINCT h.application_id) 
                    FROM application_history h
                    {dept_join}
                    {'AND' if dept_filter else 'WHERE'} h.stage_name = 'Offer'
                """).fetchone()[0]
                
                reached_hired = conn.execute(f"""
                    SELECT COUNT(DISTINCT h.application_id) 
                    FROM application_history h
                    {dept_join}
                    {'AND' if dept_filter else 'WHERE'} h.stage_name = 'Hired'
                """).fetchone()[0]
                
                conn.close()
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Reached Onsite", f"{reached_onsite:,}", 
                           help="Candidates who entered onsite stage at any point")
                col2.metric("Reached Offer", f"{reached_offer:,}",
                           help="Candidates who received an offer")
                col3.metric("Final Hires", f"{reached_hired:,}",
                           help="Successfully hired")
                
                if reached_onsite > 0:
                    onsite_to_offer = (reached_offer / reached_onsite) * 100
                    col4.metric("Onsite → Offer", f"{onsite_to_offer:.0f}%",
                               help="% of onsite candidates who got offer")
                    
                    # Show conversion breakdown
                    st.markdown("**Stage-by-Stage Conversion:**")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("Onsite → Offer", f"{onsite_to_offer:.0f}%",
                                 delta=f"{reached_offer} of {reached_onsite}")
                    
                    with col2:
                        if reached_offer > 0:
                            offer_to_hire = (reached_hired / reached_offer) * 100
                            st.metric("Offer → Hired", f"{offer_to_hire:.0f}%",
                                     delta=f"{reached_hired} of {reached_offer}")
                    
                    # Status message based on realistic expectations
                    if onsite_to_offer >= 50:
                        st.success(f"✅ Strong onsite pass rate of {onsite_to_offer:.0f}%")
                    elif onsite_to_offer >= 30:
                        st.info(f"📊 Typical onsite pass rate of {onsite_to_offer:.0f}% (industry norm: 30-50%)")
                    else:
                        st.warning(f"⚠️ Low onsite pass rate of {onsite_to_offer:.0f}%. Consider improving pre-onsite screening.")
                else:
                    col4.metric("Onsite → Offer", "N/A")
                    st.info("No onsite stage data available")
                    
            except Exception as e:
                st.error(f"Error calculating dropoff: {e}")
        else:
            # Fallback message
            st.warning("⏳ Application history not yet loaded. Run `python update_history.py` to fetch stage transition data for accurate funnel metrics.")
            conn.close()
        
        # Interview hours analysis
        st.markdown("---")
        st.subheader("📊 Interview Investment Analysis")
        st.info(f"💡 We invest an average of **{funnel_data['hours_per_hire']:.1f} hours** of interviewing per successful hire.")
        
        # Interviewers per stage stats
        st.markdown("#### 👥 Interviewers per Candidate by Stage")
        try:
            conn = duckdb.connect(str(DB_PATH), read_only=True)
            
            dept_filter_sql = f"AND a.department = '{dept_filter}'" if dept_filter else ""
            
            interviewer_stats_query = f"""
            WITH candidate_stage_interviewers AS (
                SELECT 
                    h.stage_name,
                    h.application_id,
                    COUNT(DISTINCT f.interviewer_id) as interviewer_count
                FROM application_history h
                JOIN feedback f ON h.application_id = f.application_id
                JOIN applications a ON h.application_id = a.id
                WHERE f.interviewer_id IS NOT NULL
                {dept_filter_sql}
                GROUP BY h.stage_name, h.application_id
            ),
            stage_stats AS (
                SELECT 
                    stage_name,
                    COUNT(DISTINCT application_id) as candidates,
                    SUM(interviewer_count) as total_interviews,
                    MIN(interviewer_count) as min_interviewers,
                    MAX(interviewer_count) as max_interviewers,
                    ROUND(AVG(interviewer_count), 1) as avg_interviewers,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY interviewer_count) as median_interviewers
                FROM candidate_stage_interviewers
                GROUP BY stage_name
                HAVING COUNT(DISTINCT application_id) >= 5
            )
            SELECT 
                stage_name as "Stage",
                candidates as "Candidates",
                total_interviews as "Total Interviews",
                min_interviewers as "Min",
                max_interviewers as "Max",
                avg_interviewers as "Avg",
                median_interviewers as "Median"
            FROM stage_stats
            where stage_name not in ('Jordan 1:1','Archived','Application Review', 'Reached Out', 'Intro Call', 'New Lead', 'Replied')
            ORDER BY candidates DESC
            """
            
            interviewer_stats = conn.execute(interviewer_stats_query).df()
            conn.close()
            
            if len(interviewer_stats) > 0:
                # Display as a nicely formatted table
                st.dataframe(
                    interviewer_stats,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Stage": st.column_config.TextColumn("Stage"),
                        "Candidates": st.column_config.NumberColumn("Candidates", format="%d"),
                        "Total Interviews": st.column_config.NumberColumn("Total Interviews", format="%d"),
                        "Min": st.column_config.NumberColumn("Min", format="%d"),
                        "Max": st.column_config.NumberColumn("Max", format="%d"),
                        "Avg": st.column_config.NumberColumn("Avg", format="%.1f"),
                        "Median": st.column_config.NumberColumn("Median", format="%.1f"),
                    }
                )
                
                # Bar chart showing average interviewers per stage
                fig = px.bar(
                    interviewer_stats.head(15),
                    x='Stage',
                    y='Avg',
                    color='Avg',
                    title="Average Interviewers per Candidate by Stage",
                    color_continuous_scale='Blues',
                    hover_data=['Candidates', 'Min', 'Max', 'Median']
                )
                fig.update_layout(yaxis_title="Avg Interviewers per Candidate")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No interviewer data available for this filter")
        except Exception as e:
            st.warning(f"Could not load interviewer stats: {e}")
        
    except Exception as e:
        st.error(f"Error loading funnel data: {e}")
        import traceback
        st.code(traceback.format_exc())

# =============================================================================
# TAB 2: PRE-ONSITE SCREENING (Rubric Heatmap)
# =============================================================================
with tab2:
    st.header("🔍 Pre-Onsite Screening Analysis")
    st.markdown("""
    **Question:** What could we screen for earlier to increase onsite pass rates?
    
    Analyzing rejection reasons and feedback to identify patterns we could screen for earlier.
    """)
    
    # Department filter for this tab
    screening_departments = ['All'] + science.get_departments()
    selected_screening_dept = st.selectbox("Filter by Department:", screening_departments, key="screening_dept")
    screening_dept_filter = None if selected_screening_dept == 'All' else selected_screening_dept
    
    # Rejection Reasons Chart - Only for candidates who reached Onsite
    st.subheader("📊 Onsite Rejection Reasons")
    st.caption("Showing rejection reasons only for candidates who reached the Onsite stage")
    
    conn = duckdb.connect(str(DB_PATH), read_only=True)
    
    # Check if we have application_history table
    has_history = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='application_history'").fetchone()[0] > 0
    
    try:
        dept_where = f"AND a.department = '{screening_dept_filter}'" if screening_dept_filter else ""
        
        if has_history:
            # Use application_history to find candidates who reached onsite
            rejection_query = f"""
            WITH onsite_candidates AS (
                SELECT DISTINCT h.application_id
                FROM application_history h
                WHERE h.stage_name ILIKE '%onsite%' 
                   OR h.stage_name = 'All Around'
                   OR h.stage_name = 'Work Trial'
            )
            SELECT 
                CASE WHEN a.archive_reason IS NULL OR a.archive_reason = '' 
                     THEN 'Not Specified' 
                     ELSE a.archive_reason 
                END as reason,
                COUNT(*) as count
            FROM applications a
            JOIN onsite_candidates oc ON a.id = oc.application_id
            WHERE a.current_stage_name = 'Archived'
            {dept_where}
            GROUP BY reason
            ORDER BY count DESC
            LIMIT 15
            """
        else:
            # Fallback: just show all archived
            st.warning("⚠️ Run history fetch for accurate onsite filtering")
            rejection_query = f"""
            SELECT 
                CASE WHEN archive_reason IS NULL OR archive_reason = '' 
                     THEN 'Not Specified' 
                     ELSE archive_reason 
                END as reason,
                COUNT(*) as count
            FROM applications
            WHERE current_stage_name = 'Archived'
            {dept_where.replace('a.', '')}
            GROUP BY reason
            ORDER BY count DESC
            LIMIT 15
            """
        
        rejection_df = conn.execute(rejection_query).df()
        
        if len(rejection_df) > 0 and rejection_df['reason'].iloc[0] != 'Not Specified':
            col1, col2 = st.columns([2, 1])
            
            with col1:
                dept_label = f" - {screening_dept_filter}" if screening_dept_filter else ""
                title = f"Rejection Reasons at Onsite Stage{dept_label}"
                fig = px.bar(
                    rejection_df,
                    x='count',
                    y='reason',
                    orientation='h',
                    title=title,
                    color='count',
                    color_continuous_scale='Reds'
                )
                fig.update_layout(yaxis={'categoryorder': 'total ascending'}, height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("**Top Onsite Rejection Reasons:**")
                for _, row in rejection_df.head(8).iterrows():
                    pct = row['count'] / rejection_df['count'].sum() * 100
                    st.markdown(f"• **{row['reason']}**: {row['count']:,} ({pct:.1f}%)")
        else:
            st.warning("⚠️ Archive reasons not populated. Run `python update_applications.py` to fetch data.")
        
    except Exception as e:
        st.error(f"Error loading rejection reasons: {e}")
    finally:
        conn.close()
    
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📊 Onsite Vote Distribution")
        st.caption("Votes for candidates who reached Onsite stage")
        try:
            conn = duckdb.connect(str(DB_PATH), read_only=True)
            has_history = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='application_history'").fetchone()[0] > 0
            
            dept_filter_sql = f"AND a.department = '{screening_dept_filter}'" if screening_dept_filter else ""
            
            if has_history:
                rating_query = f"""
                WITH onsite_candidates AS (
                    SELECT DISTINCT h.application_id
                    FROM application_history h
                    WHERE h.stage_name ILIKE '%onsite%' 
                       OR h.stage_name = 'All Around'
                       OR h.stage_name = 'Work Trial'
                )
                SELECT 
                    f.vote,
                    COUNT(*) as count
                FROM feedback f
                JOIN applications a ON f.application_id = a.id
                JOIN onsite_candidates oc ON a.id = oc.application_id
                WHERE f.vote IS NOT NULL
                {dept_filter_sql}
                GROUP BY f.vote
                ORDER BY count DESC
                """
            else:
                rating_query = f"""
                SELECT 
                    f.vote,
                    COUNT(*) as count
                FROM feedback f
                JOIN applications a ON f.application_id = a.id
                WHERE f.vote IS NOT NULL
                {dept_filter_sql}
                GROUP BY f.vote
                ORDER BY count DESC
                """
            
            rating_df = conn.execute(rating_query).df()
            conn.close()
            
            if len(rating_df) > 0:
                fig = px.pie(rating_df, values='count', names='vote', 
                            title="Onsite Interview Votes",
                            color_discrete_sequence=['#2ecc71', '#27ae60', '#e74c3c', '#c0392b'])
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No vote data available")
                
        except Exception as e:
            st.error(f"Error loading ratings: {e}")
    
    with col2:
        st.subheader("📈 Onsite → Offer Conversion by Source")
        st.caption("Among candidates who reached Onsite, which sources convert to Offer best?")
        try:
            conn = duckdb.connect(str(DB_PATH), read_only=True)
            has_history = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='application_history'").fetchone()[0] > 0
            
            dept_filter_sql = f"AND a.department = '{screening_dept_filter}'" if screening_dept_filter else ""
            
            if has_history:
                # Find candidates who reached Onsite and whether they got Offer
                source_query = f"""
                WITH onsite_candidates AS (
                    SELECT DISTINCT h.application_id
                    FROM application_history h
                    WHERE h.stage_name ILIKE '%onsite%' 
                       OR h.stage_name = 'All Around'
                       OR h.stage_name = 'Work Trial'
                ),
                offer_candidates AS (
                    SELECT DISTINCT h.application_id
                    FROM application_history h
                    WHERE h.stage_name ILIKE '%offer%'
                )
                SELECT 
                    a.source,
                    COUNT(DISTINCT oc.application_id) as reached_onsite,
                    COUNT(DISTINCT ofc.application_id) as got_offer,
                    ROUND(COUNT(DISTINCT ofc.application_id) * 100.0 / NULLIF(COUNT(DISTINCT oc.application_id), 0), 1) as offer_rate
                FROM applications a
                JOIN onsite_candidates oc ON a.id = oc.application_id
                LEFT JOIN offer_candidates ofc ON a.id = ofc.application_id
                WHERE 1=1 {dept_filter_sql}
                GROUP BY a.source
                HAVING COUNT(DISTINCT oc.application_id) >= 5
                ORDER BY offer_rate DESC
                LIMIT 15
                """
                source_df = conn.execute(source_query).df()
                conn.close()
                
                if len(source_df) > 0:
                    fig = px.bar(
                        source_df,
                        x='source',
                        y='offer_rate',
                        color='offer_rate',
                        title="Onsite → Offer Rate by Source (candidates screened already)",
                        color_continuous_scale='Greens',
                        hover_data=['reached_onsite', 'got_offer']
                    )
                    fig.update_layout(yaxis_title="% Onsite → Offer")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Show the data table too
                    st.caption("Data breakdown:")
                    st.dataframe(source_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No source data available (need application_history)")
            else:
                st.warning("Requires application_history table - run update_history.py first")
                source_df = science.get_source_patterns(screening_dept_filter)
                
                if len(source_df) > 0:
                    fig = px.bar(
                        source_df,
                        x='source',
                        y='hire_rate',
                        color='hire_rate',
                        title="Hire Rate by Source (fallback)",
                        color_continuous_scale='Greens'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(source_df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Error loading source patterns: {e}")
    
    # Feedback theme analysis
    st.markdown("---")
    st.subheader("🤖 AI Analysis: What Should We Screen For Earlier?")
    
    st.markdown("""
    **Hypothesis:** By analyzing why candidates fail at the Onsite stage, we can identify patterns 
    that could be detected earlier in the process through better pre-screening questions or assessments.
    """)
    
    # Show which department is being analyzed
    if screening_dept_filter:
        st.caption(f"Analyzing Onsite rejection feedback for **{screening_dept_filter}**")
    else:
        st.caption("Analyzing Onsite rejection feedback for **All Departments**")
    
    if st.button("🔍 Analyze Onsite Rejections for Pre-Screening Insights", key="analyze_rejections"):
        with st.spinner("Analyzing feedback with OpenAI..."):
            try:
                # Pass department filter and onsite_only flag
                feedback_df = science.get_rejection_feedback(department=screening_dept_filter, onsite_only=True)
                
                if len(feedback_df) > 0:
                    st.caption(f"Analyzing {len(feedback_df)} onsite rejection feedback entries...")
                    feedback_texts = feedback_df['feedback_text'].dropna().tolist()
                    analysis = science.analyze_feedback_themes(feedback_texts, "pre_screening")
                    
                    if not analysis.get('error'):
                        st.success("Analysis complete!")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**🎯 Why Candidates Fail at Onsite:**")
                            for i, theme in enumerate(analysis.get('themes', []), 1):
                                st.markdown(f"{i}. {theme}")
                        
                        with col2:
                            st.markdown("**🔮 Pre-Screening Recommendations:**")
                            st.markdown("*Things we could screen for earlier:*")
                            for rec in analysis.get('recommendations', []):
                                st.markdown(f"• {rec}")
                        
                        st.markdown("**📝 Summary:**")
                        st.info(analysis.get('summary', 'No summary available'))
                    else:
                        st.warning(analysis.get('summary', 'Analysis failed'))
                else:
                    st.info("No onsite rejection feedback available. Make sure application_history is populated.")
                    
            except Exception as e:
                st.error(f"Error analyzing feedback: {e}")

# =============================================================================
# TAB 3: FALSE NEGATIVE DETECTIVE
# =============================================================================
with tab3:
    st.header("❓ False Negative Detective")
    st.markdown("""
    **Question:** Are we rejecting good candidates? 
    
    Finding archived candidates with high ratings who had at least one positive vote.
    """)
    
    # Department filter
    fn_departments = ['All'] + science.get_departments()
    selected_fn_dept = st.selectbox("Filter by Department:", fn_departments, key="fn_dept")
    fn_dept_filter = None if selected_fn_dept == 'All' else selected_fn_dept
    
    # Controls
    col1, col2 = st.columns([1, 3])
    with col1:
        # Rating scale is 1-4: 1=Strong No, 2=No, 3=Yes, 4=Strong Yes
        rating_threshold = st.slider("Min Avg Rating (1-4 scale):", 2.0, 4.0, 3.0, 0.5,
                                    help="1=Strong No, 2=No, 3=Yes, 4=Strong Yes")
    
    try:
        false_negatives = science.detect_false_negatives(rating_threshold, department=fn_dept_filter)
        
        if len(false_negatives) > 0:
            st.success(f"Found **{len(false_negatives)}** potential false negatives to review")
            st.caption("These candidates were archived but had positive ratings from some interviewers")
            
            # Display as table
            display_cols = ['candidate_name', 'department', 'avg_rating', 'hire_votes', 'no_hire_votes', 'archive_reason']
            available_cols = [c for c in display_cols if c in false_negatives.columns]
            
            st.dataframe(
                false_negatives[available_cols],
                use_container_width=True,
                hide_index=True,
                column_config={
                    'avg_rating': st.column_config.NumberColumn("Avg Rating", format="%.2f"),
                    'candidate_name': 'Candidate',
                    'hire_votes': 'Yes Votes',
                    'no_hire_votes': 'No Votes',
                    'archive_reason': 'Archive Reason'
                }
            )
            
            st.markdown("---")
            st.subheader("📊 Rejection Patterns")
            
            rejection_chars = science.get_rejection_characteristics()
            
            if len(rejection_chars) > 0:
                # By department
                dept_rej = rejection_chars.groupby('department')['count'].sum().reset_index()
                fig = px.pie(
                    dept_rej, 
                    values='count', 
                    names='department',
                    title="Rejections by Department"
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No potential false negatives found with current threshold. Try lowering the rating threshold.")
            
    except Exception as e:
        st.error(f"Error detecting false negatives: {e}")
        import traceback
        st.code(traceback.format_exc())
    
    # Additional analyses section
    st.markdown("---")
    st.subheader("🔬 Additional False Negative Signals")
    
    # Create tabs for different analyses
    fn_tab1, fn_tab2, fn_tab3, fn_tab4 = st.tabs([
        "📊 Dissenting Votes", 
        "🎯 Close Calls", 
        "🔄 Rehires",
        "📈 Archive Reasons"
    ])
    
    with fn_tab1:
        st.markdown("**Candidates where interviewers disagreed** (some Yes, some No)")
        try:
            dissenting = science.get_dissenting_votes(fn_dept_filter)
            if len(dissenting) > 0:
                st.info(f"Found **{len(dissenting)}** candidates with split decisions")
                display_cols = ['candidate_name', 'department', 'yes_votes', 'no_votes', 'current_stage_name', 'archive_reason']
                available = [c for c in display_cols if c in dissenting.columns]
                st.dataframe(dissenting[available], use_container_width=True, hide_index=True)
            else:
                st.info("No split decisions found")
        except Exception as e:
            st.error(f"Error: {e}")
    
    with fn_tab2:
        st.markdown("**Borderline candidates** (avg rating 2.5-3.5 on 1-4 scale)")
        try:
            close_calls = science.get_close_call_decisions(fn_dept_filter)
            if len(close_calls) > 0:
                st.info(f"Found **{len(close_calls)}** close-call decisions")
                display_cols = ['candidate_name', 'department', 'avg_rating', 'min_rating', 'max_rating', 'current_stage_name', 'archive_reason']
                available = [c for c in display_cols if c in close_calls.columns]
                st.dataframe(close_calls[available], use_container_width=True, hide_index=True,
                            column_config={'avg_rating': st.column_config.NumberColumn("Avg Rating", format="%.2f")})
            else:
                st.info("No close-call decisions found")
        except Exception as e:
            st.error(f"Error: {e}")
    
    with fn_tab3:
        st.markdown("**Candidates who applied multiple times** - were they eventually hired?")
        try:
            rehires = science.get_rehire_patterns(fn_dept_filter)
            if len(rehires) > 0:
                unique_candidates = rehires['candidate_id'].nunique() if 'candidate_id' in rehires.columns else 0
                st.info(f"Found **{unique_candidates}** candidates with multiple applications")
                display_cols = ['candidate_name', 'department', 'current_stage_name', 'archive_reason', 'total_applications']
                available = [c for c in display_cols if c in rehires.columns]
                st.dataframe(rehires[available], use_container_width=True, hide_index=True)
            else:
                st.info("No repeat applicants found")
        except Exception as e:
            st.error(f"Error: {e}")
    
    with fn_tab4:
        st.markdown("**Archive reasons that suggest good candidates we lost**")
        try:
            archive_reasons = science.get_archive_reason_analysis(fn_dept_filter)
            if len(archive_reasons) > 0:
                # Highlight specific reasons
                good_signals = ['Future Candidate', 'Accepted Other Offer', 'Timing', 'Withdrew']
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**All Archive Reasons:**")
                    st.dataframe(archive_reasons, use_container_width=True, hide_index=True,
                                column_config={'percentage': st.column_config.NumberColumn("% of Total", format="%.1f%%")})
                
                with col2:
                    st.markdown("**🚨 Signals of Lost Good Candidates:**")
                    for reason in good_signals:
                        match = archive_reasons[archive_reasons['archive_reason'].str.contains(reason, case=False, na=False)]
                        if len(match) > 0:
                            count = match['count'].sum()
                            st.metric(reason, f"{count} candidates")
            else:
                st.info("No archive reason data")
        except Exception as e:
            st.error(f"Error: {e}")
    
    st.markdown("---")
    st.markdown("""
    **❌ Not Available:** External Validation (where rejected candidates ended up) - would require LinkedIn/external data integration.
    """)

# =============================================================================
# TAB 4: INTERVIEWER CALIBRATION
# =============================================================================
with tab4:
    st.header("⚖️ Interviewer Calibration Leaderboard")
    st.markdown("""
    **Question:** Do we have uncalibrated interviewers? Hawks who always say no? Doves who always say yes?
    """)
    st.caption("📊 **Key stages only** - includes feedback from Coding 1, Hiring Manager Screen, Technical Interview 1, Technical Interview 2, and Onsite")
    
    # Department filter
    cal_departments = ['All'] + science.get_departments()
    selected_cal_dept = st.selectbox("Filter by Department:", cal_departments, key="cal_dept")
    cal_dept_filter = None if selected_cal_dept == 'All' else selected_cal_dept
    
    try:
        calibration_df = science.calculate_interviewer_calibration(department=cal_dept_filter)
        
        if len(calibration_df) > 0:
            # Summary metrics
            hawks = len(calibration_df[calibration_df['calibration'].str.contains('Hawk')])
            doves = len(calibration_df[calibration_df['calibration'].str.contains('Dove')])
            calibrated = len(calibration_df[calibration_df['calibration'].str.contains('Calibrated')])
            
            col1, col2, col3 = st.columns(3)
            col1.metric("🦅 Hawks (Strict)", hawks)
            col2.metric("🕊️ Doves (Lenient)", doves)
            col3.metric("✅ Calibrated", calibrated)
            
            st.markdown("---")
            
            # Approval rate chart
            fig = px.bar(
                calibration_df.sort_values('approval_rate'),
                x='interviewer_name',
                y='approval_rate',
                color='calibration',
                title="Interviewer Approval Rates",
                color_discrete_map={
                    '🦅 Hawk (Strict)': '#e74c3c',
                    '🕊️ Dove (Lenient)': '#3498db',
                    '✅ Calibrated': '#2ecc71'
                }
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
            
            # Full table
            st.subheader("📋 Full Calibration Data")
            st.dataframe(
                calibration_df[[
                    'interviewer_name', 'interview_count', 'hire_votes', 
                    'no_hire_votes', 'approval_rate', 'avg_rating', 'calibration'
                ]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    'approval_rate': st.column_config.NumberColumn(format="%.1f%%"),
                    'avg_rating': st.column_config.NumberColumn(format="%.2f")
                }
            )
        else:
            st.info("Not enough interview data for calibration analysis")
            
    except Exception as e:
        st.error(f"Error calculating calibration: {e}")

# =============================================================================
# TAB 5: FALSE POSITIVES
# =============================================================================
with tab5:
    st.header("⚠️ False Positive Analysis")
    st.markdown("""
    **Question:** Are there people who passed our interviews but left the company quickly?
    
    This helps identify potential gaps in our interview process.
    """)
    
    # Department filter
    fp_departments = ['All'] + science.get_departments()
    selected_fp_dept = st.selectbox("Filter by Department:", fp_departments, key="fp_dept")
    fp_dept_filter = None if selected_fp_dept == 'All' else selected_fp_dept
    
    try:
        false_positives = science.analyze_false_positives(department=fp_dept_filter)
        
        if len(false_positives) > 0:
            st.warning(f"Found **{len(false_positives)}** employees who left within 12 months")
            
            # Summary stats
            col1, col2, col3 = st.columns(3)
            col1.metric("Avg Tenure (days)", f"{false_positives['tenure_days'].mean():.0f}")
            col2.metric("Min Tenure", f"{false_positives['tenure_days'].min():.0f} days")
            col3.metric("Max Tenure", f"{false_positives['tenure_days'].max():.0f} days")
            
            st.markdown("---")
            
            # Table of early departures
            st.subheader("📋 Early Departures")
            st.dataframe(
                false_positives,
                use_container_width=True,
                hide_index=True
            )
            
            # Analyze feedback for these candidates
            st.markdown("---")
            st.subheader("🤖 AI Analysis: Interview Feedback Review")
            
            if st.button("Analyze Feedback for Early Departures", key="analyze_fp"):
                with st.spinner("Analyzing..."):
                    app_ids = false_positives['application_id'].dropna().tolist() if 'application_id' in false_positives.columns else []
                    
                    if app_ids:
                        fp_feedback = science.get_false_positive_feedback(app_ids)
                        
                        if len(fp_feedback) > 0:
                            feedback_texts = fp_feedback['feedback_text'].dropna().tolist()
                            analysis = science.analyze_feedback_themes(feedback_texts, "general")
                            
                            if not analysis.get('error'):
                                st.markdown("**🎯 Common Themes in Feedback:**")
                                for theme in analysis.get('themes', []):
                                    st.markdown(f"• {theme}")
                                
                                st.markdown("**📝 Summary:**")
                                st.info(analysis.get('summary', 'No summary'))
                        else:
                            st.info("No feedback found for these candidates")
                    else:
                        st.info("No application IDs linked to employees")
        else:
            st.success("✅ No early departures found - good sign for interview quality!")
            st.info("Note: This analysis requires employee data. Upload a CSV with employee departure dates.")
            
    except Exception as e:
        st.error(f"Error analyzing false positives: {e}")

# =============================================================================
# TAB 6: RECOMMENDATIONS
# =============================================================================
# Tab6 removed - content moved to tab_summary

# =============================================================================
# TAB 7: SQL QUERY
# =============================================================================
with tab7:
    st.header("🔎 SQL Query Tool")
    st.markdown("Run custom SQL queries against the interview data for validation and exploration.")
    
    # Schema explorer in sidebar
    with st.sidebar:
        st.header("📊 Schema Explorer")
        
        conn = duckdb.connect(str(DB_PATH), read_only=True)
        tables = conn.execute("SHOW TABLES").df()['name'].tolist()
        
        selected_table = st.selectbox("Select Table:", [""] + tables)
        
        if selected_table:
            st.markdown(f"**Table: `{selected_table}`**")
            
            # Get columns
            sample = conn.execute(f"SELECT * FROM {selected_table} LIMIT 1").df()
            
            st.markdown("**Columns:**")
            for col in sample.columns:
                dtype = str(sample[col].dtype)
                st.code(f"{col} ({dtype})", language=None)
            
            # Row count
            count = conn.execute(f"SELECT COUNT(*) FROM {selected_table}").fetchone()[0]
            st.markdown(f"**Rows:** {count:,}")
        
        conn.close()
        
        st.markdown("---")
        st.markdown("### 💡 Example Queries")
        
        example_queries = {
            "Funnel by Department": """
SELECT 
    department,
    current_stage_name,
    COUNT(*) as count
FROM applications
GROUP BY department, current_stage_name
ORDER BY department, count DESC
            """,
            "Interviewer Stats": """
SELECT 
    interviewer_name,
    COUNT(*) as interviews,
    AVG(overall_rating) as avg_rating,
    SUM(CASE WHEN vote LIKE '%Hire%' AND vote NOT LIKE '%No%' THEN 1 ELSE 0 END) as hire_votes
FROM feedback
GROUP BY interviewer_name
ORDER BY interviews DESC
            """,
            "Source Performance": """
SELECT 
    source,
    COUNT(*) as total,
    SUM(CASE WHEN status = 'Hired' THEN 1 ELSE 0 END) as hired,
    ROUND(SUM(CASE WHEN status = 'Hired' THEN 1.0 ELSE 0 END) / COUNT(*) * 100, 1) as hire_rate_pct
FROM applications
GROUP BY source
ORDER BY hire_rate_pct DESC
            """,
            "Rejection Reasons": """
SELECT 
    archive_reason,
    department,
    COUNT(*) as count
FROM applications
WHERE archived = true
GROUP BY archive_reason, department
ORDER BY count DESC
            """
        }
        
        for name, query in example_queries.items():
            if st.button(f"📌 {name}", key=f"example_{name}"):
                st.session_state['sql_query'] = query.strip()
    
    # Main query interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        default_query = st.session_state.get('sql_query', 'SELECT * FROM applications LIMIT 10')
        
        query = st.text_area(
            "Enter SQL Query:",
            value=default_query,
            height=200
        )
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            run_query = st.button("▶️ Run Query", type="primary", use_container_width=True)
        
        with col_btn2:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state['sql_query'] = ''
                st.rerun()
    
    with col2:
        st.markdown("### 📋 Available Tables")
        conn = duckdb.connect(str(DB_PATH), read_only=True)
        
        for table in tables:
            with st.expander(f"📋 {table}"):
                try:
                    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    st.markdown(f"**Rows:** {count:,}")
                    
                    sample = conn.execute(f"SELECT * FROM {table} LIMIT 0").df()
                    st.markdown("**Columns:**")
                    for col in sample.columns:
                        st.text(f"  • {col}")
                except Exception as e:
                    st.error(str(e))
        
        conn.close()
    
    # Execute query
    if run_query and query:
        try:
            conn = duckdb.connect(str(DB_PATH), read_only=True)
            
            with st.spinner("Executing query..."):
                result_df = conn.execute(query).df()
            
            conn.close()
            
            st.success(f"✅ Query returned {len(result_df)} rows")
            
            # Download button
            csv = result_df.to_csv(index=False)
            st.download_button(
                "📥 Download as CSV",
                csv,
                "query_results.csv",
                "text/csv"
            )
            
            # Display results
            st.dataframe(result_df, use_container_width=True, height=400)
            
            # Summary stats for numeric columns
            numeric_cols = result_df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                with st.expander("📈 Summary Statistics"):
                    st.dataframe(result_df[numeric_cols].describe())
                    
        except Exception as e:
            st.error(f"❌ Query Error: {str(e)}")
            st.info("💡 Check the Schema Explorer in the sidebar for available tables and columns.")

