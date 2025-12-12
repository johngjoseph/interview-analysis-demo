"""
Interview Analytics Science Module
Analysis functions for all dashboard tabs.
"""
import pandas as pd
import numpy as np
import duckdb
from pathlib import Path
import os
from openai import OpenAI
import json

# --- CONFIGURATION ---
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / 'data'
DB_PATH = DATA_DIR / 'interview_analytics.duckdb'

# OpenAI client (lazy loaded)
_openai_client = None


def get_openai_client():
    """Get or create OpenAI client."""
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def get_db_connection():
    """Get DuckDB connection."""
    return duckdb.connect(str(DB_PATH), read_only=True)


# =============================================================================
# TAB 1: FUNNEL RATIOS
# =============================================================================

def calculate_funnel_ratios(department: str = None) -> dict:
    """
    Calculate funnel conversion rates between stages.
    
    Returns:
        dict with 'funnel_data', 'conversion_rates', 'interview_hours'
    """
    conn = get_db_connection()
    
    # Get stage order
    stages_df = conn.execute("SELECT * FROM stages ORDER BY order_in_plan").df()
    
    # Build query with optional department filter
    where_clause = f"WHERE a.department = '{department}'" if department else ""
    where_clause_apps = f"WHERE department = '{department}'" if department else ""
    
    # Count applications at each stage
    query = f"""
    SELECT 
        current_stage_id,
        current_stage_name,
        COUNT(*) as count,
        SUM(CASE WHEN status = 'Hired' THEN 1 ELSE 0 END) as hired_count,
        SUM(CASE WHEN archived THEN 1 ELSE 0 END) as archived_count
    FROM applications
    {where_clause_apps}
    GROUP BY current_stage_id, current_stage_name
    """
    
    stage_counts = conn.execute(query).df()
    
    # Get total applications
    total_query = f"SELECT COUNT(*) as total FROM applications {where_clause_apps}"
    total = conn.execute(total_query).df()['total'].iloc[0]
    
    # Calculate interview hours using FEEDBACK as proxy (1 hour per feedback entry)
    # This is more reliable than the interviews table which may lack duration data
    feedback_hours_query = f"""
    SELECT 
        COUNT(*) as interview_count
    FROM feedback f
    JOIN applications a ON f.application_id = a.id
    {where_clause}
    """
    try:
        feedback_stats = conn.execute(feedback_hours_query).df()
        interview_count = int(feedback_stats['interview_count'].iloc[0] or 0)
    except:
        interview_count = 0
    
    # Assume 1 hour per interview (feedback entry)
    total_interview_hours = interview_count  # 1 hour each
    avg_interview_duration = 60  # 60 minutes assumed
    
    # Calculate hours per hire
    hired_query = f"SELECT COUNT(*) FROM applications {where_clause_apps} {'AND' if where_clause_apps else 'WHERE'} status = 'Hired'"
    hired_count = conn.execute(hired_query).fetchone()[0]
    hours_per_hire = total_interview_hours / hired_count if hired_count > 0 else 0
    
    conn.close()
    
    # Calculate conversion rates - group by stage NAME to avoid duplicates
    conversion_rates = []
    
    # Aggregate stage_counts by current_stage_name (not ID)
    if len(stage_counts) > 0:
        grouped_counts = stage_counts.groupby('current_stage_name').agg({
            'count': 'sum'
        }).reset_index()
        grouped_counts = grouped_counts.sort_values('count', ascending=False)
        
        cumulative = total
        for _, row in grouped_counts.iterrows():
            stage_count = int(row['count'])
            conversion_rates.append({
                'stage': row['current_stage_name'],
                'count': stage_count,
                'rate': round((stage_count / cumulative * 100), 1) if cumulative > 0 else 0
            })
    
    return {
        'stage_counts': stage_counts.to_dict('records'),
        'conversion_rates': conversion_rates,
        'total_applications': int(total),
        'total_interview_hours': float(total_interview_hours),
        'avg_interview_duration': float(avg_interview_duration),
        'interview_count': int(interview_count),
        'hours_per_hire': float(hours_per_hire)
    }


def get_funnel_sankey_data(department: str = None) -> dict:
    """Get data formatted for Sankey diagram."""
    conn = get_db_connection()
    
    where_clause = f"WHERE department = '{department}'" if department else ""
    
    # Get stage transitions
    query = f"""
    SELECT 
        current_stage_name as stage,
        status,
        COUNT(*) as count
    FROM applications
    {where_clause}
    GROUP BY current_stage_name, status
    ORDER BY current_stage_name
    """
    
    df = conn.execute(query).df()
    conn.close()
    
    return df.to_dict('records')


# =============================================================================
# TAB 2: PRE-ONSITE SCREENING / RUBRIC HEATMAP
# =============================================================================

def get_rejection_feedback(department: str = None, onsite_only: bool = False) -> pd.DataFrame:
    """Get feedback for rejected/archived candidates."""
    conn = get_db_connection()
    
    dept_filter = f"AND a.department = '{department}'" if department else ""
    
    # Check if we have application_history table for onsite filtering
    has_history = False
    try:
        has_history = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='application_history'").fetchone()[0] > 0
    except:
        pass
    
    if onsite_only and has_history:
        query = f"""
        WITH onsite_candidates AS (
            SELECT DISTINCT h.application_id
            FROM application_history h
            WHERE h.stage_name ILIKE '%onsite%' 
               OR h.stage_name = 'All Around'
               OR h.stage_name = 'Work Trial'
        )
        SELECT 
            f.feedback_text,
            f.vote,
            f.overall_rating,
            f.interviewer_name,
            a.department,
            a.source,
            a.archive_reason,
            a.current_stage_name
        FROM feedback f
        JOIN applications a ON f.application_id = a.id
        JOIN onsite_candidates oc ON a.id = oc.application_id
        WHERE a.current_stage_name = 'Archived'
        AND f.feedback_text IS NOT NULL
        AND f.feedback_text != ''
        {dept_filter}
        LIMIT 500
        """
    else:
        query = f"""
        SELECT 
            f.feedback_text,
            f.vote,
            f.overall_rating,
            f.interviewer_name,
            a.department,
            a.source,
            a.archive_reason,
            a.current_stage_name
        FROM feedback f
        JOIN applications a ON f.application_id = a.id
        WHERE a.current_stage_name = 'Archived'
        AND f.feedback_text IS NOT NULL
        AND f.feedback_text != ''
        {dept_filter}
        LIMIT 500
        """
    
    df = conn.execute(query).df()
    conn.close()
    
    return df


def build_rubric_heatmap() -> pd.DataFrame:
    """
    Build correlation matrix showing which rubric scores correlate with hire decisions.
    """
    conn = get_db_connection()
    
    # Get feedback with outcomes
    query = """
    SELECT 
        f.overall_rating,
        f.vote,
        a.status,
        a.department
    FROM feedback f
    JOIN applications a ON f.application_id = a.id
    WHERE f.overall_rating IS NOT NULL
    """
    
    df = conn.execute(query).df()
    conn.close()
    
    if len(df) == 0:
        return pd.DataFrame()
    
    # Convert vote to numeric
    vote_map = {
        'Strong Hire': 4,
        'Hire': 3,
        'No Hire': 2,
        'Strong No Hire': 1
    }
    df['vote_numeric'] = df['vote'].map(vote_map).fillna(2.5)
    
    # Add hire outcome
    df['hired'] = (df['status'] == 'Hired').astype(int)
    
    # Calculate correlations by department
    correlations = df.groupby('department').agg({
        'overall_rating': 'mean',
        'vote_numeric': 'mean',
        'hired': 'mean'
    }).reset_index()
    
    correlations.columns = ['department', 'avg_rating', 'avg_vote', 'hire_rate']
    
    return correlations


def get_source_patterns(department: str = None) -> pd.DataFrame:
    """Analyze patterns by source for rejected vs hired candidates."""
    conn = get_db_connection()
    
    dept_where = f"WHERE department = '{department}'" if department else ""
    
    query = f"""
    SELECT 
        source,
        COUNT(*) as total,
        SUM(CASE WHEN status = 'Hired' THEN 1 ELSE 0 END) as hired,
        SUM(CASE WHEN archived THEN 1 ELSE 0 END) as archived,
        ROUND(SUM(CASE WHEN status = 'Hired' THEN 1.0 ELSE 0 END) / COUNT(*) * 100, 1) as hire_rate
    FROM applications
    {dept_where}
    GROUP BY source
    HAVING COUNT(*) > 5
    ORDER BY hire_rate DESC
    """
    
    df = conn.execute(query).df()
    conn.close()
    
    return df


# =============================================================================
# TAB 3: FALSE NEGATIVE DETECTIVE
# =============================================================================

def detect_false_negatives(rating_threshold: float = 3.0, department: str = None) -> pd.DataFrame:
    """
    Find archived candidates who had high technical scores but were rejected.
    
    Criteria for potential false negatives:
    - Candidate is archived (rejected)
    - Average rating >= threshold (default 3.0 on 1-4 scale)
    - Had at least 2 feedback entries
    - Mix of positive and negative votes (not unanimous rejection)
    
    Args:
        rating_threshold: Minimum avg rating to be considered "high" (1-4 scale)
        department: Optional department filter
    
    Returns:
        DataFrame of potential false negatives
    """
    conn = get_db_connection()
    
    dept_filter = f"AND a.department = '{department}'" if department else ""
    
    query = f"""
    WITH candidate_feedback AS (
        SELECT 
            f.application_id,
            a.candidate_name,
            a.department,
            a.source,
            a.archive_reason,
            COUNT(*) as feedback_count,
            AVG(f.overall_rating) as avg_rating,
            MAX(f.overall_rating) as max_rating,
            MIN(f.overall_rating) as min_rating,
            SUM(CASE WHEN f.vote IN ('No', 'Strong No') THEN 1 ELSE 0 END) as no_hire_votes,
            SUM(CASE WHEN f.vote IN ('Yes', 'Strong Yes') THEN 1 ELSE 0 END) as hire_votes
        FROM feedback f
        JOIN applications a ON f.application_id = a.id
        WHERE a.current_stage_name = 'Archived'
        AND f.overall_rating IS NOT NULL
        {dept_filter}
        GROUP BY f.application_id, a.candidate_name, a.department, a.source, a.archive_reason
    )
    SELECT *
    FROM candidate_feedback
    WHERE avg_rating >= {rating_threshold}
    AND feedback_count >= 2
    AND hire_votes >= 1
    ORDER BY avg_rating DESC, hire_votes DESC
    LIMIT 50
    """
    
    df = conn.execute(query).df()
    conn.close()
    
    return df


def get_rejection_characteristics() -> pd.DataFrame:
    """Analyze characteristics of rejected candidates."""
    conn = get_db_connection()
    
    query = """
    SELECT 
        department,
        source,
        archive_reason,
        COUNT(*) as count,
        AVG(f.overall_rating) as avg_rating
    FROM applications a
    LEFT JOIN feedback f ON a.id = f.application_id
    WHERE a.archived = true
    GROUP BY department, source, archive_reason
    ORDER BY count DESC
    """
    
    df = conn.execute(query).df()
    conn.close()
    
    return df


def get_dissenting_votes(department: str = None) -> pd.DataFrame:
    """
    Find candidates where interviewers disagreed (some Yes, some No).
    These are contentious decisions worth reviewing.
    """
    conn = get_db_connection()
    
    dept_filter = f"AND a.department = '{department}'" if department else ""
    
    query = f"""
    WITH vote_summary AS (
        SELECT 
            f.application_id,
            a.candidate_name,
            a.department,
            a.current_stage_name,
            a.archive_reason,
            COUNT(*) as total_votes,
            SUM(CASE WHEN f.vote IN ('Yes', 'Strong Yes') THEN 1 ELSE 0 END) as yes_votes,
            SUM(CASE WHEN f.vote IN ('No', 'Strong No') THEN 1 ELSE 0 END) as no_votes,
            STRING_AGG(f.interviewer_name || ': ' || COALESCE(f.vote, 'N/A'), ' | ') as vote_details
        FROM feedback f
        JOIN applications a ON f.application_id = a.id
        WHERE f.vote IS NOT NULL
        {dept_filter}
        GROUP BY f.application_id, a.candidate_name, a.department, a.current_stage_name, a.archive_reason
    )
    SELECT *
    FROM vote_summary
    WHERE yes_votes >= 1 AND no_votes >= 1
    ORDER BY total_votes DESC, yes_votes DESC
    LIMIT 50
    """
    
    df = conn.execute(query).df()
    conn.close()
    return df


def get_close_call_decisions(department: str = None) -> pd.DataFrame:
    """
    Find candidates with borderline average ratings (2.5 - 3.5 on 1-4 scale).
    These are close calls that could have gone either way.
    """
    conn = get_db_connection()
    
    dept_filter = f"AND a.department = '{department}'" if department else ""
    
    query = f"""
    SELECT 
        f.application_id,
        a.candidate_name,
        a.department,
        a.current_stage_name,
        a.archive_reason,
        COUNT(*) as feedback_count,
        ROUND(AVG(f.overall_rating), 2) as avg_rating,
        MIN(f.overall_rating) as min_rating,
        MAX(f.overall_rating) as max_rating
    FROM feedback f
    JOIN applications a ON f.application_id = a.id
    WHERE f.overall_rating IS NOT NULL
    {dept_filter}
    GROUP BY f.application_id, a.candidate_name, a.department, a.current_stage_name, a.archive_reason
    HAVING AVG(f.overall_rating) BETWEEN 2.5 AND 3.5
    AND COUNT(*) >= 2
    ORDER BY avg_rating DESC
    LIMIT 50
    """
    
    df = conn.execute(query).df()
    conn.close()
    return df


def get_rehire_patterns(department: str = None) -> pd.DataFrame:
    """
    Find candidates who applied multiple times.
    Compare their outcomes across applications.
    """
    conn = get_db_connection()
    
    dept_filter = f"WHERE a.department = '{department}'" if department else ""
    
    query = f"""
    WITH multi_applicants AS (
        SELECT candidate_id
        FROM applications
        WHERE candidate_id IS NOT NULL
        GROUP BY candidate_id
        HAVING COUNT(*) > 1
    )
    SELECT 
        a.candidate_id,
        a.candidate_name,
        a.department,
        a.current_stage_name,
        a.archive_reason,
        a.created_at,
        (SELECT COUNT(*) FROM applications a2 WHERE a2.candidate_id = a.candidate_id) as total_applications
    FROM applications a
    JOIN multi_applicants ma ON a.candidate_id = ma.candidate_id
    {dept_filter}
    ORDER BY a.candidate_id, a.created_at
    LIMIT 100
    """
    
    df = conn.execute(query).df()
    conn.close()
    return df


def get_archive_reason_analysis(department: str = None) -> pd.DataFrame:
    """
    Analyze archive reasons that suggest false negatives.
    'Future Candidate' and 'Accepted Other Offer' are signals.
    """
    conn = get_db_connection()
    
    dept_filter = f"AND department = '{department}'" if department else ""
    
    query = f"""
    SELECT 
        archive_reason,
        COUNT(*) as count,
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
    FROM applications
    WHERE current_stage_name = 'Archived'
    AND archive_reason IS NOT NULL
    AND archive_reason != ''
    {dept_filter}
    GROUP BY archive_reason
    ORDER BY count DESC
    """
    
    df = conn.execute(query).df()
    conn.close()
    return df


# =============================================================================
# TAB 4: INTERVIEWER CALIBRATION
# =============================================================================

def calculate_interviewer_calibration(department: str = None) -> pd.DataFrame:
    """
    Calculate interviewer calibration metrics for key interview stages.
    Identifies Hawks (always No) and Doves (always Yes).
    
    Only includes feedback from these stages:
    - Coding 1
    - Hiring Manager Screen
    - Technical Interview 1
    - Technical Interview 2
    - Onsite
    """
    conn = get_db_connection()
    
    # Check if we have application_history for stage filtering
    has_history = False
    try:
        has_history = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='application_history'").fetchone()[0] > 0
    except:
        pass
    
    dept_filter = f"AND a.department = '{department}'" if department else ""
    
    if has_history:
        # Filter to only specific interview stages
        query = f"""
        WITH operator_applications AS (
            SELECT DISTINCT application_id
            FROM application_history
            WHERE stage_name ILIKE '%coding 1%'
               OR stage_name ILIKE '%hiring manager%'
               OR stage_name ILIKE '%technical interview 1%'
               OR stage_name ILIKE '%technical interview 2%'
               OR stage_name ILIKE '%onsite%'
        )
        SELECT 
            f.interviewer_id,
            f.interviewer_name,
            COUNT(*) as interview_count,
            SUM(CASE WHEN f.vote IN ('Hire', 'Strong Hire', 'Yes', 'Strong Yes') THEN 1 ELSE 0 END) as hire_votes,
            SUM(CASE WHEN f.vote IN ('No Hire', 'Strong No Hire', 'No', 'Strong No') THEN 1 ELSE 0 END) as no_hire_votes,
            ROUND(SUM(CASE WHEN f.vote IN ('Hire', 'Strong Hire', 'Yes', 'Strong Yes') THEN 1.0 ELSE 0 END) / COUNT(*) * 100, 1) as approval_rate,
            AVG(f.overall_rating) as avg_rating
        FROM feedback f
        JOIN applications a ON f.application_id = a.id
        JOIN operator_applications oa ON f.application_id = oa.application_id
        WHERE f.vote IS NOT NULL
        {dept_filter}
        GROUP BY f.interviewer_id, f.interviewer_name
        HAVING COUNT(*) >= 5
        ORDER BY approval_rate DESC
        """
    else:
        # Fallback without history - just use department filter
        query = f"""
        SELECT 
            f.interviewer_id,
            f.interviewer_name,
            COUNT(*) as interview_count,
            SUM(CASE WHEN f.vote IN ('Hire', 'Strong Hire', 'Yes', 'Strong Yes') THEN 1 ELSE 0 END) as hire_votes,
            SUM(CASE WHEN f.vote IN ('No Hire', 'Strong No Hire', 'No', 'Strong No') THEN 1 ELSE 0 END) as no_hire_votes,
            ROUND(SUM(CASE WHEN f.vote IN ('Hire', 'Strong Hire', 'Yes', 'Strong Yes') THEN 1.0 ELSE 0 END) / COUNT(*) * 100, 1) as approval_rate,
            AVG(f.overall_rating) as avg_rating
        FROM feedback f
        JOIN applications a ON f.application_id = a.id
        WHERE f.vote IS NOT NULL
        {dept_filter}
        GROUP BY f.interviewer_id, f.interviewer_name
        HAVING COUNT(*) >= 5
        ORDER BY approval_rate DESC
        """
    
    df = conn.execute(query).df()
    conn.close()
    
    if len(df) == 0:
        return df
    
    # Calculate z-scores for approval rate
    mean_rate = df['approval_rate'].mean()
    std_rate = df['approval_rate'].std()
    
    if std_rate > 0:
        df['z_score'] = (df['approval_rate'] - mean_rate) / std_rate
    else:
        df['z_score'] = 0
    
    # Classify as Hawk/Dove/Calibrated
    df['calibration'] = df['z_score'].apply(
        lambda z: '🦅 Hawk (Strict)' if z < -1.5 
        else ('🕊️ Dove (Lenient)' if z > 1.5 else '✅ Calibrated')
    )
    
    return df


def get_interviewer_patterns() -> pd.DataFrame:
    """Get common rejection patterns by interviewer."""
    conn = get_db_connection()
    
    query = """
    SELECT 
        f.interviewer_name,
        f.vote,
        f.feedback_text,
        a.archive_reason,
        COUNT(*) as count
    FROM feedback f
    JOIN applications a ON f.application_id = a.id
    WHERE f.vote IN ('No Hire', 'Strong No Hire')
    GROUP BY f.interviewer_name, f.vote, f.feedback_text, a.archive_reason
    ORDER BY count DESC
    """
    
    df = conn.execute(query).df()
    conn.close()
    
    return df


# =============================================================================
# TAB 5: FALSE POSITIVE ANALYSIS
# =============================================================================

def analyze_false_positives(department: str = None) -> pd.DataFrame:
    """
    Analyze employees who left within 12 months (potential false positives).
    """
    conn = get_db_connection()
    
    dept_filter = f"AND e.department = '{department}'" if department else ""
    
    # Check if employees table exists
    try:
        query = f"""
        SELECT 
            e.employee_id,
            e.candidate_name,
            e.department,
            e.hire_date,
            e.departure_date,
            e.tenure_days,
            a.source
        FROM employees e
        LEFT JOIN applications a ON e.application_id = a.id
        WHERE e.departure_date IS NOT NULL
        AND e.tenure_days IS NOT NULL
        AND e.tenure_days < 365
        {dept_filter}
        ORDER BY e.tenure_days ASC
        """
        
        df = conn.execute(query).df()
    except:
        df = pd.DataFrame()
    
    conn.close()
    
    return df


def get_false_positive_feedback(employee_application_ids: list) -> pd.DataFrame:
    """Get original interview feedback for employees who left."""
    if not employee_application_ids:
        return pd.DataFrame()
    
    conn = get_db_connection()
    
    ids_str = "', '".join(employee_application_ids)
    
    query = f"""
    SELECT 
        f.application_id,
        f.interviewer_name,
        f.vote,
        f.overall_rating,
        f.feedback_text
    FROM feedback f
    WHERE f.application_id IN ('{ids_str}')
    """
    
    df = conn.execute(query).df()
    conn.close()
    
    return df


# =============================================================================
# OPENAI INTEGRATION
# =============================================================================

def analyze_feedback_themes(feedback_texts: list, analysis_type: str = "rejection") -> dict:
    """
    Use OpenAI to extract themes from feedback text.
    
    Args:
        feedback_texts: List of feedback text strings
        analysis_type: "rejection" or "general"
    
    Returns:
        dict with 'themes', 'summary', 'recommendations'
    """
    client = get_openai_client()
    
    if not client:
        return {
            'themes': ['OpenAI API key not configured'],
            'summary': 'Unable to analyze - no API key',
            'recommendations': [],
            'error': True
        }
    
    if not feedback_texts or len(feedback_texts) == 0:
        return {
            'themes': [],
            'summary': 'No feedback to analyze',
            'recommendations': [],
            'error': False
        }
    
    # Sample if too many
    sample_size = min(50, len(feedback_texts))
    sampled = np.random.choice(feedback_texts, sample_size, replace=False).tolist()
    
    feedback_block = "\n---\n".join(sampled)
    
    if analysis_type == "pre_screening":
        prompt = f"""You are analyzing interview feedback from candidates who were REJECTED at the ONSITE stage.

Your goal is to identify patterns that could have been detected EARLIER in the hiring process through better pre-screening.

Analyze these onsite rejection feedback excerpts and identify:

1. TOP 5 REJECTION REASONS: What are the most common reasons these candidates failed at onsite?

2. PRE-SCREENING RECOMMENDATIONS: For each rejection reason, suggest a specific question, assessment, or screening method that could identify this issue BEFORE the onsite stage. Be specific and actionable.

3. SUMMARY: A brief summary of the key patterns and what the recruiting team should prioritize.

Feedback excerpts:
{feedback_block}

Respond in JSON format:
{{
    "themes": ["Rejection reason 1", "Rejection reason 2", ...],
    "summary": "Brief summary of patterns and priorities...",
    "recommendations": ["Add X question to phone screen to detect Y", "Include Z assessment before onsite", ...]
}}"""
    elif analysis_type == "rejection":
        prompt = f"""Analyze these interview feedback excerpts for rejected candidates.
        
Identify:
1. The top 5 most common themes/reasons for rejection
2. A brief summary of patterns you see
3. 2-3 actionable recommendations for the recruiting team

Feedback excerpts:
{feedback_block}

Respond in JSON format:
{{
    "themes": ["theme 1", "theme 2", ...],
    "summary": "Brief summary...",
    "recommendations": ["rec 1", "rec 2", ...]
}}"""
    else:
        prompt = f"""Analyze these interview feedback excerpts.
        
Identify:
1. The top 5 most common themes
2. A brief summary of patterns
3. Any notable insights

Feedback excerpts:
{feedback_block}

Respond in JSON format:
{{
    "themes": ["theme 1", "theme 2", ...],
    "summary": "Brief summary...",
    "insights": ["insight 1", ...]
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert HR analyst helping to improve hiring processes."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        result['error'] = False
        return result
        
    except Exception as e:
        return {
            'themes': [f'Error: {str(e)}'],
            'summary': 'Analysis failed',
            'recommendations': [],
            'error': True
        }


def summarize_candidate_feedback(feedback_df: pd.DataFrame) -> str:
    """Generate a summary of feedback for a specific candidate."""
    client = get_openai_client()
    
    if not client or len(feedback_df) == 0:
        return "Unable to generate summary"
    
    feedback_list = []
    for _, row in feedback_df.iterrows():
        feedback_list.append(f"- {row['interviewer_name']} ({row['vote']}): {row['feedback_text']}")
    
    feedback_text = "\n".join(feedback_list)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Summarize interview feedback concisely."},
                {"role": "user", "content": f"Summarize this interview feedback in 2-3 sentences:\n\n{feedback_text}"}
            ],
            temperature=0.3,
            max_tokens=200
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Error generating summary: {str(e)}"


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_departments() -> list:
    """Get list of all departments."""
    conn = get_db_connection()
    
    # First try to get from departments table
    try:
        df = conn.execute("SELECT DISTINCT name FROM departments WHERE name IS NOT NULL ORDER BY name").df()
        if len(df) > 0:
            conn.close()
            return df['name'].tolist()
    except:
        pass
    
    # Fallback to applications table
    df = conn.execute("SELECT DISTINCT department FROM applications WHERE department != 'Unknown' ORDER BY department").df()
    conn.close()
    return df['department'].tolist() if len(df) > 0 else []


def get_summary_stats() -> dict:
    """Get high-level summary statistics."""
    conn = get_db_connection()
    
    stats = {}
    
    stats['total_applications'] = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    stats['total_hired'] = conn.execute("SELECT COUNT(*) FROM applications WHERE status = 'Hired'").fetchone()[0]
    stats['total_archived'] = conn.execute("SELECT COUNT(*) FROM applications WHERE archived = true").fetchone()[0]
    stats['total_interviews'] = conn.execute("SELECT COUNT(*) FROM interviews").fetchone()[0]
    stats['total_feedback'] = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
    stats['total_interviewers'] = conn.execute("SELECT COUNT(DISTINCT interviewer_id) FROM feedback").fetchone()[0]
    
    # Hire rate
    if stats['total_applications'] > 0:
        stats['overall_hire_rate'] = round(stats['total_hired'] / stats['total_applications'] * 100, 1)
    else:
        stats['overall_hire_rate'] = 0
    
    conn.close()
    
    return stats

