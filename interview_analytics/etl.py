"""
Interview Analytics ETL Pipeline
Fetches data from Ashby API and stores in DuckDB for SQL querying.
"""
import duckdb
import pandas as pd
import numpy as np
import os
import requests
import base64
from datetime import datetime, timedelta
from pathlib import Path

# --- CONFIGURATION ---
ASHBY_API_KEY = os.getenv("ASHBY_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Create data directory relative to script location
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / 'data'
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / 'interview_analytics.duckdb'


class AshbyAPI:
    """Client for Ashby API - all endpoints use POST requests."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.ashbyhq.com"
        self.headers = {
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode()).decode()}",
            "Content-Type": "application/json"
        }
    
    def _post(self, endpoint: str, data: dict = None) -> dict:
        """Make POST request to Ashby API."""
        if data is None:
            data = {}
        
        url = f"{self.base_url}/{endpoint}"
        response = requests.post(url, headers=self.headers, json=data)
        
        if response.status_code != 200:
            print(f"❌ API request failed: {endpoint} - Status {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return None
        
        result = response.json()
        if not result.get('success', False):
            print(f"❌ API error on {endpoint}: {result}")
            return None
        
        return result
    
    def _fetch_all_paginated(self, endpoint: str, data: dict = None) -> list:
        """Fetch all pages from a paginated endpoint."""
        if data is None:
            data = {}
        
        all_results = []
        cursor = None
        page = 1
        
        while True:
            request_data = {**data}
            if cursor:
                request_data['cursor'] = cursor
            
            result = self._post(endpoint, request_data)
            if not result:
                break
            
            results = result.get('results', [])
            all_results.extend(results)
            
            # Check for next page
            next_cursor = result.get('nextCursor') or result.get('moreDataAvailable')
            if not next_cursor or not results:
                break
            
            cursor = result.get('nextCursor')
            if not cursor:
                break
                
            page += 1
            print(f"   Fetching page {page}...")
        
        return all_results
    
    def get_applications(self) -> list:
        """Fetch all applications."""
        print("📥 Fetching applications...")
        return self._fetch_all_paginated('application.list')
    
    def get_application_feedback(self) -> list:
        """Fetch all application feedback."""
        print("📥 Fetching application feedback...")
        return self._fetch_all_paginated('applicationFeedback.list')
    
    def get_interviews(self) -> list:
        """Fetch all interviews."""
        print("📥 Fetching interviews...")
        return self._fetch_all_paginated('interview.list')
    
    def get_interview_plans(self) -> list:
        """Fetch all interview plans."""
        print("📥 Fetching interview plans...")
        return self._fetch_all_paginated('interviewPlan.list')
    
    def get_interview_stages(self) -> list:
        """
        Fetch all interview stages.
        NOTE: interviewStage.list requires an interviewPlanId parameter.
        We first fetch all plans, then get stages for each plan.
        """
        print("📥 Fetching interview stages...")
        
        # First, get all interview plans
        plans = self.get_interview_plans()
        
        if not plans:
            print("   ⚠️  No interview plans found")
            return []
        
        print(f"   Found {len(plans)} interview plans")
        
        # Fetch stages for each plan
        all_stages = []
        seen_stage_ids = set()  # Deduplicate stages that appear in multiple plans
        
        for plan in plans:
            plan_id = plan.get('id')
            if not plan_id:
                continue
            
            result = self._post('interviewStage.list', {'interviewPlanId': plan_id})
            
            if result:
                stages = result.get('results', [])
                for stage in stages:
                    stage_id = stage.get('id')
                    if stage_id and stage_id not in seen_stage_ids:
                        # Add plan info to stage
                        stage['interviewPlanId'] = plan_id
                        stage['interviewPlanTitle'] = plan.get('title', 'Unknown')
                        all_stages.append(stage)
                        seen_stage_ids.add(stage_id)
        
        print(f"   ✅ Found {len(all_stages)} unique stages across {len(plans)} plans")
        return all_stages
    
    def get_users(self) -> list:
        """Fetch all users (interviewers)."""
        print("📥 Fetching users...")
        return self._fetch_all_paginated('user.list')
    
    def get_candidates(self) -> list:
        """Fetch all candidates."""
        print("📥 Fetching candidates...")
        return self._fetch_all_paginated('candidate.list')
    
    def get_departments(self) -> list:
        """Fetch all departments."""
        print("📥 Fetching departments...")
        result = self._post('department.list')
        return result.get('results', []) if result else []
    
    def get_archive_reasons(self) -> list:
        """Fetch all archive reasons."""
        print("📥 Fetching archive reasons...")
        result = self._post('archiveReason.list')
        return result.get('results', []) if result else []
    
    def get_jobs(self) -> list:
        """Fetch all jobs."""
        print("📥 Fetching jobs...")
        return self._fetch_all_paginated('job.list')
    
    def get_application_history(self, application_ids: list = None) -> list:
        """
        Fetch application history (stage transitions) for all applications.
        This gives us the complete journey through interview stages.
        """
        print("📥 Fetching application history...")
        
        # If no specific IDs, fetch for all applications
        if application_ids is None:
            # First get all application IDs
            apps = self.get_applications()
            application_ids = [a.get('id') for a in apps if a.get('id')]
        
        all_history = []
        total = len(application_ids)
        
        for i, app_id in enumerate(application_ids):
            if i > 0 and i % 100 == 0:
                print(f"   Processed {i}/{total} applications...")
            
            result = self._post('application.listHistory', {'applicationId': app_id})
            if result and result.get('results'):
                for entry in result.get('results', []):
                    entry['applicationId'] = app_id  # Add application ID to each entry
                all_history.extend(result.get('results', []))
        
        print(f"   Fetched {len(all_history)} history entries for {total} applications")
        return all_history


def fetch_ashby_data() -> dict:
    """
    Fetches all required data from Ashby API.
    Returns dict of DataFrames or None if API unavailable.
    """
    if not ASHBY_API_KEY:
        print("⚠️  No ASHBY_API_KEY found. Will generate mock data.")
        return None
    
    try:
        api = AshbyAPI(ASHBY_API_KEY)
        
        # Fetch all data
        applications = api.get_applications()
        feedback = api.get_application_feedback()
        interviews = api.get_interviews()
        stages = api.get_interview_stages()
        users = api.get_users()
        candidates = api.get_candidates()
        departments = api.get_departments()
        archive_reasons = api.get_archive_reasons()
        jobs = api.get_jobs()
        
        print(f"\n📊 Data fetched:")
        print(f"   Applications: {len(applications)}")
        print(f"   Feedback: {len(feedback)}")
        print(f"   Interviews: {len(interviews)}")
        print(f"   Stages: {len(stages)}")
        print(f"   Users: {len(users)}")
        print(f"   Candidates: {len(candidates)}")
        print(f"   Departments: {len(departments)}")
        print(f"   Archive Reasons: {len(archive_reasons)}")
        print(f"   Jobs: {len(jobs)}")
        
        return {
            'applications': applications,
            'feedback': feedback,
            'interviews': interviews,
            'stages': stages,
            'users': users,
            'candidates': candidates,
            'departments': departments,
            'archive_reasons': archive_reasons,
            'jobs': jobs
        }
        
    except Exception as e:
        print(f"❌ Error fetching API data: {e}")
        import traceback
        traceback.print_exc()
        return None


def transform_applications(raw_applications: list, raw_candidates: list, raw_departments: list, raw_jobs: list) -> pd.DataFrame:
    """Transform raw application data into structured DataFrame."""
    if not raw_applications:
        return pd.DataFrame()
    
    # Create lookup dicts
    candidates_lookup = {c.get('id'): c for c in raw_candidates} if raw_candidates else {}
    departments_lookup = {d.get('id'): d.get('name') for d in raw_departments} if raw_departments else {}
    jobs_lookup = {j.get('id'): j for j in raw_jobs} if raw_jobs else {}
    
    rows = []
    for app in raw_applications:
        candidate = candidates_lookup.get(app.get('candidateId'), {})
        
        # Handle job - can be nested object or just jobId
        job_data = app.get('job', {}) or {}
        job_id = job_data.get('id') if job_data else app.get('jobId')
        job_title = job_data.get('title', 'Unknown') if job_data else 'Unknown'
        
        # If we have job_id but no job_data, look up from jobs table
        if job_id and not job_data:
            job_data = jobs_lookup.get(job_id, {})
            job_title = job_data.get('title', 'Unknown')
        
        # Get department - try from job data first, then from jobs lookup
        dept_id = job_data.get('departmentId')
        department = departments_lookup.get(dept_id, 'Unknown') if dept_id else 'Unknown'
        
        # If still unknown, try department from job data directly
        if department == 'Unknown' and job_data.get('department'):
            dept_info = job_data.get('department', {})
            if isinstance(dept_info, dict):
                department = dept_info.get('name', 'Unknown')
            elif isinstance(dept_info, str):
                department = dept_info
        
        # Get current stage info
        current_stage = app.get('currentInterviewStage', {}) or {}
        
        rows.append({
            'id': app.get('id'),
            'candidate_id': app.get('candidateId'),
            'candidate_name': candidate.get('name', 'Unknown'),
            'job_id': job_id,
            'job_title': job_title,
            'department': department,
            'source': app.get('source', {}).get('title', 'Unknown') if isinstance(app.get('source'), dict) else str(app.get('source', 'Unknown')),
            'current_stage_id': current_stage.get('id') if current_stage else None,
            'current_stage_name': current_stage.get('title') if current_stage else None,
            'status': app.get('status', 'Unknown'),
            'archived': app.get('isArchived', False),
            'archive_reason': app.get('archiveReason', {}).get('text') if app.get('archiveReason') else None,
            'hired_at': app.get('hiredAt'),
            'created_at': app.get('createdAt'),
            'updated_at': app.get('updatedAt')
        })
    
    return pd.DataFrame(rows)


def transform_feedback(raw_feedback: list, raw_users: list) -> pd.DataFrame:
    """Transform raw feedback data into structured DataFrame."""
    if not raw_feedback:
        return pd.DataFrame()
    
    users_lookup = {u.get('id'): u for u in raw_users} if raw_users else {}
    
    rows = []
    for fb in raw_feedback:
        # Extract submittedValues (contains rating and feedback text)
        submitted_values = fb.get('submittedValues', {}) or {}
        
        # Extract interviewer from submittedByUser (not interviewerId)
        submitted_by = fb.get('submittedByUser', {}) or {}
        interviewer_id = submitted_by.get('id')
        interviewer_name = f"{submitted_by.get('firstName', '')} {submitted_by.get('lastName', '')}".strip() or 'Unknown'
        interviewer_email = submitted_by.get('email', '')
        
        # Rating is in submittedValues.overall_recommendation (values: "1", "2", "3", "4")
        overall_recommendation = submitted_values.get('overall_recommendation')
        
        # Map string values to descriptive ratings
        rating_map = {
            '4': 'Strong Yes',
            '3': 'Yes', 
            '2': 'No',
            '1': 'Strong No'
        }
        vote = rating_map.get(overall_recommendation) if overall_recommendation else None
        
        # Convert to numeric rating (1-4)
        overall_rating = int(overall_recommendation) if overall_recommendation and overall_recommendation.isdigit() else None
        
        # Feedback text is in submittedValues.feedback
        feedback_text = submitted_values.get('feedback', '') or ''
        
        rows.append({
            'id': fb.get('id'),
            'application_id': fb.get('applicationId'),
            'interviewer_id': interviewer_id,
            'interviewer_name': interviewer_name,
            'interviewer_email': interviewer_email,
            'interview_stage_id': fb.get('interviewStageId'),
            'interview_id': fb.get('interviewId'),
            'overall_rating': overall_rating,
            'vote': vote,
            'feedback_text': feedback_text,
            'submitted_at': fb.get('submittedAt') or fb.get('createdAt'),
            'created_at': fb.get('createdAt')
        })
    
    return pd.DataFrame(rows)


def transform_interviews(raw_interviews: list) -> pd.DataFrame:
    """Transform raw interview data into structured DataFrame."""
    if not raw_interviews:
        return pd.DataFrame()
    
    rows = []
    for interview in raw_interviews:
        # Handle interviewers list
        interviewers = interview.get('interviewers', [])
        interviewer_ids = [i.get('id') if isinstance(i, dict) else i for i in interviewers]
        
        # Calculate duration if start/end times available
        duration_minutes = None
        if interview.get('startTime') and interview.get('endTime'):
            try:
                start = datetime.fromisoformat(interview['startTime'].replace('Z', '+00:00'))
                end = datetime.fromisoformat(interview['endTime'].replace('Z', '+00:00'))
                duration_minutes = (end - start).total_seconds() / 60
            except:
                pass
        
        rows.append({
            'id': interview.get('id'),
            'application_id': interview.get('applicationId'),
            'interview_stage_id': interview.get('interviewStageId'),
            'interviewer_ids': ','.join(interviewer_ids) if interviewer_ids else '',
            'interviewer_count': len(interviewer_ids),
            'duration_minutes': duration_minutes,
            'status': interview.get('status'),
            'start_time': interview.get('startTime'),
            'end_time': interview.get('endTime'),
            'created_at': interview.get('createdAt')
        })
    
    return pd.DataFrame(rows)


def transform_stages(raw_stages: list) -> pd.DataFrame:
    """Transform raw stage data into structured DataFrame."""
    if not raw_stages:
        return pd.DataFrame()
    
    rows = []
    for stage in raw_stages:
        rows.append({
            'id': stage.get('id'),
            'title': stage.get('title', 'Unknown'),
            'order_in_plan': stage.get('orderInInterviewPlan', 0),
            'stage_type': stage.get('type', 'Unknown'),
            'interview_plan_id': stage.get('interviewPlanId'),
            'interview_plan_title': stage.get('interviewPlanTitle', 'Unknown')
        })
    
    return pd.DataFrame(rows)


def transform_users(raw_users: list) -> pd.DataFrame:
    """Transform raw user data into structured DataFrame."""
    if not raw_users:
        return pd.DataFrame()
    
    rows = []
    for user in raw_users:
        rows.append({
            'id': user.get('id'),
            'name': user.get('name', 'Unknown'),
            'email': user.get('email', ''),
            'is_enabled': user.get('isEnabled', True),
            'department': user.get('department', {}).get('name') if isinstance(user.get('department'), dict) else None
        })
    
    return pd.DataFrame(rows)


def transform_archive_reasons(raw_reasons: list) -> pd.DataFrame:
    """Transform raw archive reason data into structured DataFrame."""
    if not raw_reasons:
        return pd.DataFrame()
    
    rows = []
    for reason in raw_reasons:
        rows.append({
            'id': reason.get('id'),
            'reason_text': reason.get('text', '') or reason.get('title', 'Unknown')
        })
    
    return pd.DataFrame(rows)


def transform_application_history(raw_history: list) -> pd.DataFrame:
    """
    Transform raw application history data into structured DataFrame.
    Each row represents a stage transition for an application.
    """
    if not raw_history:
        return pd.DataFrame()
    
    rows = []
    for entry in raw_history:
        rows.append({
            'id': entry.get('id'),
            'application_id': entry.get('applicationId'),
            'stage_id': entry.get('stageId'),
            'stage_name': entry.get('title', 'Unknown'),
            'stage_number': entry.get('stageNumber'),
            'entered_at': entry.get('enteredStageAt'),
            'actor_id': entry.get('actorId'),
        })
    
    df = pd.DataFrame(rows)
    
    # Sort by application and entry time for proper sequencing
    if len(df) > 0 and 'entered_at' in df.columns:
        df = df.sort_values(['application_id', 'entered_at'])
    
    return df


def generate_mock_data() -> dict:
    """Generate realistic mock data for development/demo."""
    np.random.seed(42)
    
    print("⚠️  Generating mock data for development...")
    
    # --- Departments ---
    departments = ['Engineering', 'Product', 'Design', 'Sales', 'Marketing', 'G&A']
    
    # --- Interview Stages ---
    stages_data = [
        {'id': 'stage_1', 'title': 'Application Review', 'order_in_plan': 1, 'stage_type': 'ApplicationReview', 'interview_plan_id': 'plan_1'},
        {'id': 'stage_2', 'title': 'Recruiter Screen', 'order_in_plan': 2, 'stage_type': 'PhoneScreen', 'interview_plan_id': 'plan_1'},
        {'id': 'stage_3', 'title': 'Technical Screen', 'order_in_plan': 3, 'stage_type': 'TechnicalScreen', 'interview_plan_id': 'plan_1'},
        {'id': 'stage_4', 'title': 'Onsite Interview', 'order_in_plan': 4, 'stage_type': 'Onsite', 'interview_plan_id': 'plan_1'},
        {'id': 'stage_5', 'title': 'Offer', 'order_in_plan': 5, 'stage_type': 'Offer', 'interview_plan_id': 'plan_1'},
        {'id': 'stage_6', 'title': 'Hired', 'order_in_plan': 6, 'stage_type': 'Hired', 'interview_plan_id': 'plan_1'},
    ]
    stages_df = pd.DataFrame(stages_data)
    
    # --- Interviewers ---
    interviewer_names = [
        'Alex Chen', 'Sarah Kim', 'Mike Johnson', 'Emily Davis', 'Chris Lee',
        'Jessica Wang', 'David Brown', 'Rachel Green', 'Tom Wilson', 'Lisa Zhang',
        'James Miller', 'Amanda Taylor', 'Kevin Park', 'Michelle Liu', 'Brian Adams'
    ]
    
    interviewers_df = pd.DataFrame({
        'id': [f'user_{i}' for i in range(len(interviewer_names))],
        'name': interviewer_names,
        'email': [f'{name.lower().replace(" ", ".")}@company.com' for name in interviewer_names],
        'is_enabled': [True] * len(interviewer_names),
        'department': np.random.choice(departments, len(interviewer_names))
    })
    
    # --- Applications ---
    n_applications = 500
    
    # Generate candidate names
    first_names = ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda', 
                   'William', 'Elizabeth', 'David', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
                  'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Wilson', 'Anderson', 'Thomas', 'Taylor']
    
    sources = ['LinkedIn', 'Referral', 'Direct Application', 'Indeed', 'Greenhouse', 'Recruiter Sourced']
    statuses = ['Active', 'Hired', 'Archived']
    archive_reasons = ['Not a fit', 'Declined offer', 'Failed technical', 'Failed culture', 'Withdrew', 'Position filled', None]
    
    # Simulate funnel - fewer candidates at each stage
    stage_distribution = {
        'stage_1': 0.15,  # Application Review
        'stage_2': 0.20,  # Recruiter Screen
        'stage_3': 0.25,  # Technical Screen
        'stage_4': 0.20,  # Onsite
        'stage_5': 0.10,  # Offer
        'stage_6': 0.10,  # Hired
    }
    
    applications_data = []
    for i in range(n_applications):
        # Determine current stage based on funnel
        current_stage_id = np.random.choice(
            list(stage_distribution.keys()),
            p=list(stage_distribution.values())
        )
        current_stage_name = next(s['title'] for s in stages_data if s['id'] == current_stage_id)
        
        # Determine status
        if current_stage_id == 'stage_6':
            status = 'Hired'
            archived = False
            archive_reason = None
        elif np.random.random() < 0.3:  # 30% archived at various stages
            status = 'Archived'
            archived = True
            archive_reason = np.random.choice([r for r in archive_reasons if r])
        else:
            status = 'Active'
            archived = False
            archive_reason = None
        
        dept = np.random.choice(departments, p=[0.45, 0.15, 0.10, 0.15, 0.10, 0.05])
        
        applications_data.append({
            'id': f'app_{i}',
            'candidate_id': f'cand_{i}',
            'candidate_name': f'{np.random.choice(first_names)} {np.random.choice(last_names)}',
            'job_id': f'job_{np.random.randint(1, 20)}',
            'job_title': f'{dept} Role {np.random.randint(1, 5)}',
            'department': dept,
            'source': np.random.choice(sources),
            'current_stage_id': current_stage_id,
            'current_stage_name': current_stage_name,
            'status': status,
            'archived': archived,
            'archive_reason': archive_reason,
            'hired_at': datetime.now().isoformat() if status == 'Hired' else None,
            'created_at': (datetime.now() - timedelta(days=np.random.randint(1, 365))).isoformat(),
            'updated_at': datetime.now().isoformat()
        })
    
    applications_df = pd.DataFrame(applications_data)
    
    # --- Feedback ---
    # Generate feedback for applications past recruiter screen
    feedback_data = []
    feedback_id = 0
    
    rubric_categories = ['Technical Skills', 'Communication', 'Problem Solving', 'Culture Fit', 'Experience']
    votes = ['Strong Hire', 'Hire', 'No Hire', 'Strong No Hire']
    vote_weights = [0.15, 0.35, 0.35, 0.15]
    
    # Common feedback themes
    positive_themes = [
        "Strong technical foundation and problem-solving abilities.",
        "Excellent communication skills, very articulate.",
        "Great culture fit, would be a strong team player.",
        "Impressive project experience and depth of knowledge.",
        "Shows growth mindset and eagerness to learn.",
    ]
    
    negative_themes = [
        "Technical skills below bar for the level.",
        "Communication was unclear, hard to follow thought process.",
        "Concerns about culture fit and collaboration style.",
        "Limited experience with our tech stack.",
        "Did not demonstrate senior-level thinking.",
        "Struggled with system design concepts.",
    ]
    
    for app in applications_data:
        stage_order = int(app['current_stage_id'].split('_')[1])
        
        # Generate feedback for stages 2-4 (Screen through Onsite)
        for stage_num in range(2, min(stage_order + 1, 5)):
            stage_id = f'stage_{stage_num}'
            
            # Number of interviewers depends on stage
            if stage_num == 2:  # Recruiter Screen
                n_interviewers = 1
            elif stage_num == 3:  # Technical Screen
                n_interviewers = np.random.randint(1, 3)
            else:  # Onsite
                n_interviewers = np.random.randint(3, 6)
            
            selected_interviewers = np.random.choice(interviewers_df['id'].tolist(), n_interviewers, replace=False)
            
            for interviewer_id in selected_interviewers:
                interviewer = interviewers_df[interviewers_df['id'] == interviewer_id].iloc[0]
                
                # Determine vote based on outcome
                if app['status'] == 'Hired':
                    vote = np.random.choice(votes[:2], p=[0.3, 0.7])  # Mostly Hire
                elif app['archived'] and app['archive_reason'] in ['Failed technical', 'Failed culture', 'Not a fit']:
                    vote = np.random.choice(votes[2:], p=[0.7, 0.3])  # Mostly No Hire
                else:
                    vote = np.random.choice(votes, p=vote_weights)
                
                # Generate feedback text
                if vote in ['Strong Hire', 'Hire']:
                    feedback_text = np.random.choice(positive_themes)
                else:
                    feedback_text = np.random.choice(negative_themes)
                
                feedback_data.append({
                    'id': f'fb_{feedback_id}',
                    'application_id': app['id'],
                    'interviewer_id': interviewer_id,
                    'interviewer_name': interviewer['name'],
                    'interviewer_email': interviewer['email'],
                    'interview_stage_id': stage_id,
                    'interview_id': f'interview_{feedback_id}',
                    'overall_rating': np.random.randint(1, 6),  # 1-5 scale
                    'vote': vote,
                    'feedback_text': feedback_text,
                    'submitted_at': app['created_at'],
                    'created_at': app['created_at']
                })
                feedback_id += 1
    
    feedback_df = pd.DataFrame(feedback_data)
    
    # --- Interviews ---
    interviews_data = []
    interview_id = 0
    
    for app in applications_data:
        stage_order = int(app['current_stage_id'].split('_')[1])
        
        for stage_num in range(2, min(stage_order + 1, 5)):
            stage_id = f'stage_{stage_num}'
            
            # Duration based on stage
            if stage_num == 2:
                duration = np.random.randint(30, 45)
            elif stage_num == 3:
                duration = np.random.randint(45, 60)
            else:
                duration = np.random.randint(45, 60)
            
            n_interviewers = np.random.randint(1, 4)
            interviewer_ids = np.random.choice(interviewers_df['id'].tolist(), n_interviewers, replace=False)
            
            interviews_data.append({
                'id': f'interview_{interview_id}',
                'application_id': app['id'],
                'interview_stage_id': stage_id,
                'interviewer_ids': ','.join(interviewer_ids),
                'interviewer_count': n_interviewers,
                'duration_minutes': duration,
                'status': 'Completed',
                'start_time': app['created_at'],
                'end_time': app['created_at'],
                'created_at': app['created_at']
            })
            interview_id += 1
    
    interviews_df = pd.DataFrame(interviews_data)
    
    # --- Archive Reasons ---
    archive_reasons_df = pd.DataFrame({
        'id': [f'ar_{i}' for i in range(6)],
        'reason_text': ['Not a fit', 'Declined offer', 'Failed technical', 'Failed culture', 'Withdrew', 'Position filled']
    })
    
    # --- Employees (for false positive analysis) ---
    # Simulate some hired candidates who left
    hired_apps = applications_df[applications_df['status'] == 'Hired'].head(50)
    employees_data = []
    
    for idx, app in hired_apps.iterrows():
        hire_date = datetime.now() - timedelta(days=np.random.randint(30, 500))
        
        # 20% left within a year
        if np.random.random() < 0.2:
            departure_date = hire_date + timedelta(days=np.random.randint(30, 365))
        else:
            departure_date = None
        
        employees_data.append({
            'employee_id': f'emp_{idx}',
            'application_id': app['id'],
            'candidate_name': app['candidate_name'],
            'department': app['department'],
            'hire_date': hire_date.isoformat(),
            'departure_date': departure_date.isoformat() if departure_date else None,
            'tenure_days': (departure_date - hire_date).days if departure_date else None
        })
    
    employees_df = pd.DataFrame(employees_data)
    
    return {
        'applications': applications_df,
        'feedback': feedback_df,
        'interviews': interviews_df,
        'stages': stages_df,
        'interviewers': interviewers_df,
        'archive_reasons': archive_reasons_df,
        'employees': employees_df
    }


def save_to_duckdb(dataframes: dict):
    """Save all DataFrames to DuckDB."""
    print(f"\n💾 Saving to DuckDB: {DB_PATH}")
    
    conn = duckdb.connect(str(DB_PATH))
    
    for table_name, df in dataframes.items():
        if df is not None and len(df) > 0:
            # Register DataFrame and create table
            conn.register(f'temp_{table_name}', df)
            conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM temp_{table_name}")
            print(f"   ✅ {table_name}: {len(df)} rows")
    
    conn.close()
    print(f"\n✅ Data saved to {DB_PATH}")


def run_pipeline():
    """Main ETL pipeline."""
    print("=" * 60)
    print("Interview Analytics ETL Pipeline")
    print("=" * 60)
    
    # Try to fetch real data from Ashby
    raw_data = fetch_ashby_data()
    
    if raw_data:
        print("\n🔄 Transforming Ashby data...")
        
        dataframes = {
            'applications': transform_applications(
                raw_data['applications'],
                raw_data['candidates'],
                raw_data['departments'],
                raw_data['jobs']
            ),
            'feedback': transform_feedback(raw_data['feedback'], raw_data['users']),
            'interviews': transform_interviews(raw_data['interviews']),
            'stages': transform_stages(raw_data['stages']),
            'interviewers': transform_users(raw_data['users']),
            'archive_reasons': transform_archive_reasons(raw_data['archive_reasons']),
            'employees': pd.DataFrame()  # Will be loaded from CSV separately
        }
    else:
        print("\n⚠️  Using mock data...")
        dataframes = generate_mock_data()
    
    # Save to DuckDB
    save_to_duckdb(dataframes)
    
    print("\n" + "=" * 60)
    print("ETL Pipeline Complete!")
    print("=" * 60)
    print(f"\nRun the Streamlit app: streamlit run app.py")


if __name__ == "__main__":
    run_pipeline()

