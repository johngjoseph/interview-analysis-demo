import os
import time
import random
from flask import Flask, url_for, session, redirect, render_template, request, jsonify
from authlib.integrations.flask_client import OAuth
from models import db, User, CompData, TargetCompany, OfferAnalysis
from analysis_engine import AnalysisEngine
from scraper_service import ScraperService
from dotenv import load_dotenv
from datetime import datetime
import re

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "dev_key")

# Configure for Railway/proxy (force HTTPS)
# Railway uses a proxy, so we need to trust proxy headers
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure session for production
app.config['SESSION_COOKIE_SECURE'] = True  # Always use secure cookies in production
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
# Increase session timeout
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours

# Handle Railway's postgres:// URL format (SQLAlchemy needs postgresql://)
database_url = os.getenv("DATABASE_URL", "sqlite:///local.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db.init_app(app)
oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={'scope': 'openid email profile'},
)

@app.route('/')
def index():
    """The Single Page App Entry Point. Injects all initial data for instant UI."""
    if not session.get('user'): 
        return redirect('/login')
    
    # Fetch all CompData as market_data
    comp_rows = CompData.query.all()
    market_data = [r.to_market_data_dict() for r in comp_rows]
    
    # Fetch OfferAnalysis for current user
    user = User.query.filter_by(email=session['user']['email']).first()
    if not user:
        # Create user if doesn't exist (shouldn't happen, but safety check)
        user = User(email=session['user']['email'], name=session['user'].get('name'))
        db.session.add(user)
        db.session.commit()
    
    analysis_rows = OfferAnalysis.query.filter_by(user_id=user.id).order_by(OfferAnalysis.updated_at.desc()).all()
    analyses = [{
        'id': r.id,
        'title': r.title,
        'candidateName': r.candidate_name,
        'targetRole': r.target_role,
        'proposedSalary': r.proposed_salary,
        'status': r.status,
        'notes': r.notes,
        'selectedIds': [int(x) for x in r.selected_ids.split(',') if x] if r.selected_ids else [],
        'updatedAt': r.updated_at.strftime('%Y-%m-%d') if r.updated_at else 'New'
    } for r in analysis_rows]
    
    return render_template('index.html', market_data=market_data, analyses=analyses)

@app.route('/login')
def login():
    # Make session permanent to ensure it persists across redirects
    session.permanent = True
    # Force HTTPS for Railway
    # Railway always uses HTTPS, so we need to override Flask's URL generation
    redirect_uri = url_for('authorize', _external=True)
    # Ensure HTTPS (Railway always uses HTTPS)
    # Check if we're on Railway or if URL is http://
    if 'railway.app' in request.host or redirect_uri.startswith('http://'):
        redirect_uri = redirect_uri.replace('http://', 'https://', 1)
    print(f"OAuth redirect URI: {redirect_uri}")
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/callback')
def authorize():
    try:
        # Make session permanent to ensure it persists
        session.permanent = True
        token = google.authorize_access_token()
        if not token:
            return "Error: Failed to get access token", 400
        
        # Get user info
        user_info_response = google.get('userinfo')
        if not user_info_response:
            return "Error: Failed to get user info response", 400
        
        user_info = user_info_response.json()
        if not user_info or 'email' not in user_info:
            return f"Error: Failed to get user info. Response: {user_info}", 400
        
        session['user'] = user_info
        
        # Ensure user exists in DB
        try:
            if not User.query.filter_by(email=user_info['email']).first():
                db.session.add(User(email=user_info['email'], name=user_info.get('name')))
                db.session.commit()
        except Exception as db_error:
            print(f"Database error in authorize: {db_error}")
            db.session.rollback()
            # Continue anyway - user can still log in
            
        return redirect('/')
    except Exception as e:
        print(f"Auth Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return f"Auth Error: {str(e)}", 500

@app.route('/dashboard')
def dashboard():
    """Redirect old dashboard to new SPA"""
    return redirect('/')

@app.route('/run-bulk-crawl', methods=['POST'])
def run_bulk_crawl():
    if not session.get('user'): return "", 403
    
    board_url = request.form.get('company_url')
    keyword = request.form.get('role_keyword')
    
    # Input validation
    if not board_url or not board_url.strip():
        return "<div class='text-red-500'>Error: Company URL is required.</div>"
    if not keyword or not keyword.strip():
        return "<div class='text-red-500'>Error: Role keyword is required.</div>"
    
    # Basic URL validation
    if not (board_url.startswith('http://') or board_url.startswith('https://')):
        return "<div class='text-red-500'>Error: Invalid URL format. Must start with http:// or https://</div>"
    
    try:
        # 1. SCOUT
        urls = ScraperService.discover_job_links(board_url.strip(), keyword.strip())
        if not urls:
            return "<div class='text-yellow-600'>No matching jobs found via AI Scout. The AI filtered out all links or no links were discovered.</div>"

        # 2. MINE (Top 4)
        results_html = ""
        errors_html = ""
        skipped_html = ""
        saved_count = 0
        processed_count = 0
        
        for url in urls[:4]:
            time.sleep(1)
            processed_count += 1
            raw = ScraperService.fetch_page_content(url)
            if raw:
                data = AnalysisEngine.parse_job_description_with_ai(raw)
                
                # Validate extracted data
                if not data.get('job_title') or not data.get('company'):
                    skipped_html += f"<div class='text-xs text-gray-500 mb-1'>⚠️ Skipped {url[:50]}... (missing job title or company)</div>"
                    continue
                
                # Validate salary range
                salary_min = data.get('min', 0)
                salary_max = data.get('max', 0)
                
                if salary_max <= 0:
                    skipped_html += f"<div class='text-xs text-gray-500 mb-1'>⚠️ Skipped <b>{data.get('job_title', 'Unknown')}</b> at {data.get('company', 'Unknown')} (no salary found)</div>"
                    continue
                
                # Handle case where min > max
                if salary_min > salary_max:
                    salary_min, salary_max = salary_max, salary_min
                
                # Deduplication check (company_name + role_title)
                existing = CompData.query.filter_by(
                    company_name=data.get('company'),
                    role_title=data.get('job_title')
                ).first()
                
                if existing:
                    skipped_html += f"<div class='text-xs text-yellow-600 mb-1'>🔄 Skipped <b>{data.get('job_title')}</b> at {data.get('company')} (already exists in DB: ${existing.salary_min:,}-${existing.salary_max:,})</div>"
                    continue
                
                # Save to database
                try:
                    db.session.add(CompData(
                        company_name=data.get('company'),
                        role_title=data.get('job_title'),
                        salary_min=salary_min,
                        salary_max=salary_max,
                        source_url=url
                    ))
                    saved_count += 1
                    results_html += f"""
                    <div class="flex justify-between p-2 mb-1 bg-green-50 border border-green-200 text-sm rounded">
                        <div><b>{data.get('job_title')}</b> at {data.get('company')}</div>
                        <div class="font-mono">${salary_min:,} - ${salary_max:,}</div>
                    </div>"""
                except Exception as e:
                    print(f"ERROR: Failed to add CompData: {e}")
                    errors_html += f"<div class='text-xs text-red-500 mb-1'>Error saving {data.get('job_title')}: {str(e)}</div>"
            else:
                errors_html += f"<div class='text-xs text-gray-500 mb-1'>Failed to fetch {url[:50]}...</div>"
        
        # Commit transaction
        try:
            db.session.commit()
            status_msg = f"<div class='text-green-600 font-bold mb-2'>✅ Successfully saved {saved_count} job posting(s) out of {processed_count} processed</div>" if saved_count > 0 else ""
            
            summary_html = ""
            if skipped_html:
                summary_html = f"<div class='mt-3 pt-3 border-t border-gray-200'><div class='text-xs font-bold text-gray-600 mb-2'>Skipped Items:</div>{skipped_html}</div>"
            
            if errors_html:
                summary_html += f"<div class='mt-2'><div class='text-xs font-bold text-red-600 mb-2'>Errors:</div>{errors_html}</div>"
            
            if saved_count == 0 and not skipped_html and not errors_html:
                return "<div class='text-yellow-600'>No data was extracted. All URLs failed to return salary information.</div>"
            
            return f"<div class='p-3 bg-white border rounded'><strong>Agent Report:</strong><br>{status_msg}{results_html}{summary_html}</div>"
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Database commit failed: {e}")
            return f"<div class='text-red-500'>Error: Failed to save data to database. {str(e)}</div>"
            
    except Exception as e:
        print(f"ERROR: Scraping workflow failed: {e}")
        return f"<div class='text-red-500'>Error: Scraping failed. {str(e)}</div>"

@app.route('/settings')
def settings():
    if not session.get('user'): return redirect('/')
    targets = TargetCompany.query.all()
    return render_template('settings.html', user=session['user'], targets=targets)

@app.route('/settings/add', methods=['POST'])
def add_target():
    if not session.get('user'): return "", 403
    name = request.form.get('name')
    url = request.form.get('url')
    
    if not name or not url:
        return redirect('/settings')
    
    # Basic URL validation
    if not (url.startswith('http://') or url.startswith('https://')):
        return redirect('/settings')
    
    try:
        db.session.add(TargetCompany(name=name.strip(), career_url=url.strip()))
        db.session.commit()
    except Exception as e:
        print(f"ERROR: Failed to add target company: {e}")
        db.session.rollback()
    
    return redirect('/settings')

@app.route('/settings/delete/<int:id>', methods=['DELETE'])
def delete_target(id):
    if not session.get('user'): return "", 403
    try:
        TargetCompany.query.filter_by(id=id).delete()
        db.session.commit()
    except Exception as e:
        print(f"ERROR: Failed to delete target company: {e}")
        db.session.rollback()
    return ""

@app.route('/settings/debug', methods=['POST'])
def debug_scrape():
    if not session.get('user'): return "", 403
    url = request.form.get('debug_url')
    if not url:
        return "<div class='text-red-500'>No URL provided</div>"
    
    log = ScraperService.debug_fetch(url)
    
    status_color = "text-green-600" if log['success'] else "text-red-600"
    
    return f"""
    <div class="mt-4 p-4 bg-gray-900 text-gray-100 rounded font-mono text-xs overflow-auto h-64">
        <div class="{status_color} font-bold mb-2">Debug Result: {"SUCCESS" if log['success'] else "FAILED"}</div>
        <div class="mb-2">Log Steps:</div>
        <ul class="list-disc pl-4 mb-4 text-gray-400">
            {''.join([f'<li>{s}</li>' for s in log['steps']])}
        </ul>
        <div class="mb-2">Cleaned Text Preview (First 500 chars):</div>
        <div class="p-2 bg-black rounded border border-gray-700 whitespace-pre-wrap">{log.get('preview', 'No content')}</div>
    </div>
    """

@app.route('/test-scraper')
def test_scraper():
    if not session.get('user'): return redirect('/')
    targets = TargetCompany.query.all()
    return render_template('test_scraper.html', user=session['user'], targets=targets)

@app.route('/test-scraper/run', methods=['POST'])
def test_scraper_run():
    if not session.get('user'): return "", 403
    
    board_url = request.form.get('company_url')
    keyword = request.form.get('role_keyword')
    
    if not board_url or not keyword:
        return "<div class='text-red-500'>Error: Both company URL and role keyword are required.</div>"
    
    if not (board_url.startswith('http://') or board_url.startswith('https://')):
        return "<div class='text-red-500'>Error: Invalid URL format.</div>"
    
    try:
        # Step 1: Discover links
        urls = ScraperService.discover_job_links(board_url.strip(), keyword.strip())
        
        if not urls:
            return """
            <div class='p-4 bg-yellow-50 border border-yellow-200 rounded'>
                <h3 class='font-bold text-yellow-800 mb-2'>Step 1: Link Discovery</h3>
                <p class='text-yellow-700'>No matching job links found via AI Scout.</p>
            </div>
            """
        
        # Step 2: Extract salaries
        results_html = f"""
        <div class='space-y-4'>
            <div class='p-4 bg-blue-50 border border-blue-200 rounded'>
                <h3 class='font-bold text-blue-800 mb-2'>Step 1: Link Discovery - SUCCESS</h3>
                <p class='text-blue-700 mb-2'>Found {len(urls)} matching job link(s):</p>
                <ul class='list-disc pl-5 text-sm'>
                    {''.join([f'<li class="mb-1"><a href="{url}" target="_blank" class="text-blue-600 hover:underline">{url[:80]}...</a></li>' for url in urls[:10]])}
                </ul>
            </div>
            <div class='p-4 bg-green-50 border border-green-200 rounded'>
                <h3 class='font-bold text-green-800 mb-2'>Step 2: Salary Extraction</h3>
        """
        
        extracted_count = 0
        for url in urls[:4]:
            time.sleep(1)
            raw = ScraperService.fetch_page_content(url)
            if raw:
                data = AnalysisEngine.parse_job_description_with_ai(raw)
                if data.get('max', 0) > 0:
                    extracted_count += 1
                    results_html += f"""
                    <div class="mb-2 p-2 bg-white rounded border">
                    <div class="font-bold">{data.get('job_title', 'Unknown')} at {data.get('company', 'Unknown')}</div>
                    <div class="text-sm text-gray-600">Salary: ${data.get('min', 0):,} - ${data.get('max', 0):,}</div>
                    <div class="text-xs text-gray-500 mt-1">Source: <a href="{url}" target="_blank" class="text-blue-600">{url[:60]}...</a></div>
                    </div>
                    """
                else:
                    results_html += f"""
                    <div class="mb-2 p-2 bg-yellow-50 rounded border border-yellow-200">
                        <div class="text-sm text-yellow-700">No salary found for: <a href="{url}" target="_blank" class="text-blue-600">{url[:60]}...</a></div>
                    </div>
                    """
            else:
                results_html += f"""
                <div class="mb-2 p-2 bg-red-50 rounded border border-red-200">
                    <div class="text-sm text-red-700">Failed to fetch: <a href="{url}" target="_blank" class="text-blue-600">{url[:60]}...</a></div>
                </div>
                """
        
        results_html += f"""
                <div class="mt-3 pt-3 border-t border-green-300">
                    <p class="text-sm font-bold text-green-700">Extracted salary data from {extracted_count} out of {min(len(urls), 4)} tested links.</p>
                </div>
            </div>
        </div>
        """
        
        return results_html
        
    except Exception as e:
        print(f"ERROR: Test scraper failed: {e}")
        return f"<div class='text-red-500'>Error: {str(e)}</div>"

@app.route('/test-scraper/discover', methods=['POST'])
def test_scraper_discover():
    if not session.get('user'): return "", 403
    
    board_url = request.form.get('company_url')
    keyword = request.form.get('role_keyword')
    
    if not board_url or not keyword:
        return "<div class='text-red-500'>Error: Both company URL and role keyword are required.</div>"
    
    try:
        # Get all links first (before AI filtering) using Jina
        markdown_content = ScraperService.fetch_page_content(board_url.strip())
        if not markdown_content:
            return "<div class='text-red-500'>Error: Failed to fetch page via Jina Reader.</div>"
        
        # Parse Markdown links
        link_pattern = r'\[([^\]]+)\]\((http[^\)]+)\)'
        matches = re.findall(link_pattern, markdown_content)
        
        all_links = []
        seen = set()
        for text, href in matches:
            if len(text) < 4 or "mailto" in href or "linkedin" in href:
                continue
            if href not in seen:
                all_links.append({"text": text, "url": href})
                seen.add(href)
        
        # Now get AI-filtered links
        filtered_urls = ScraperService.discover_job_links(board_url.strip(), keyword.strip())
        
        return f"""
        <div class='space-y-4'>
            <div class='p-4 bg-gray-50 border rounded'>
                <h3 class='font-bold mb-2'>All Discovered Links (Before AI Filtering)</h3>
                <p class='text-sm text-gray-600 mb-2'>Found {len(all_links)} total links</p>
                <div class='max-h-40 overflow-y-auto text-xs'>
                    <ul class='list-disc pl-5'>
                        {''.join([f'<li class="mb-1"><span class="font-medium">{link["text"][:50]}</span><br><a href="{link["url"]}" target="_blank" class="text-blue-600">{link["url"][:80]}...</a></li>' for link in all_links[:20]])}
                    </ul>
                </div>
            </div>
            <div class='p-4 bg-blue-50 border border-blue-200 rounded'>
                <h3 class='font-bold text-blue-800 mb-2'>AI-Filtered Links (After Filtering)</h3>
                <p class='text-blue-700 mb-2'>Found {len(filtered_urls)} matching links for "{keyword}"</p>
                <div class='max-h-40 overflow-y-auto text-xs'>
                    <ul class='list-disc pl-5'>
                        {''.join([f'<li class="mb-1"><a href="{url}" target="_blank" class="text-blue-600">{url[:80]}...</a></li>' for url in filtered_urls[:20]]) if filtered_urls else '<li class="text-gray-500">No matching links found</li>'}
                    </ul>
                </div>
            </div>
        </div>
        """
    except Exception as e:
        print(f"ERROR: Link discovery test failed: {e}")
        return f"<div class='text-red-500'>Error: {str(e)}</div>"

@app.route('/test-scraper/extract', methods=['POST'])
def test_scraper_extract():
    if not session.get('user'): return "", 403
    
    url = request.form.get('test_url')
    if not url:
        return "<div class='text-red-500'>Error: URL is required.</div>"
    
    try:
        raw = ScraperService.fetch_page_content(url)
        if not raw:
            return "<div class='text-red-500'>Error: Failed to fetch page content.</div>"
        
        data = AnalysisEngine.parse_job_description_with_ai(raw)
        
        preview = raw[:500] + "..." if len(raw) > 500 else raw
        
        return f"""
        <div class='space-y-4'>
            <div class='p-4 bg-green-50 border border-green-200 rounded'>
                <h3 class='font-bold text-green-800 mb-2'>Extracted Data</h3>
                <div class='space-y-2'>
                    <div><span class='font-bold'>Job Title:</span> {data.get('job_title', 'Not found')}</div>
                    <div><span class='font-bold'>Company:</span> {data.get('company', 'Not found')}</div>
                    <div><span class='font-bold'>Salary Range:</span> ${data.get('min', 0):,} - ${data.get('max', 0):,}</div>
                    <div class='text-sm text-gray-600 mt-2'><span class='font-bold'>Source URL:</span> <a href="{url}" target="_blank" class="text-blue-600">{url}</a></div>
                </div>
            </div>
            <div class='p-4 bg-gray-50 border rounded'>
                <h3 class='font-bold mb-2'>Cleaned Text Preview (First 500 chars)</h3>
                <div class='p-2 bg-white rounded border font-mono text-xs max-h-40 overflow-y-auto whitespace-pre-wrap'>{preview}</div>
            </div>
        </div>
        """
    except Exception as e:
        print(f"ERROR: Extraction test failed: {e}")
        return f"<div class='text-red-500'>Error: {str(e)}</div>"

@app.route('/api/save', methods=['POST'])
def save_analysis():
    """Create or update an OfferAnalysis record."""
    if not session.get('user'): 
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    user = User.query.filter_by(email=session['user']['email']).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if data.get('id'):
        # Update existing
        analysis = OfferAnalysis.query.filter_by(id=data['id'], user_id=user.id).first()
        if not analysis:
            return jsonify({'error': 'Analysis not found'}), 404
    else:
        # Create new
        analysis = OfferAnalysis(user_id=user.id)
        db.session.add(analysis)
    
    # Map JSON fields to DB columns
    analysis.title = data.get('title', 'New Analysis')
    analysis.candidate_name = data.get('candidateName', '')
    analysis.target_role = data.get('targetRole', '')
    analysis.proposed_salary = int(data.get('proposedSalary', 0))
    analysis.notes = data.get('notes', '')
    analysis.status = data.get('status', 'Draft')
    # Convert list of IDs back to CSV string
    selected_ids = data.get('selectedIds', [])
    analysis.selected_ids = ",".join(map(str, selected_ids))
    
    try:
        db.session.commit()
        return jsonify({
            'status': 'success', 
            'id': analysis.id, 
            'updatedAt': analysis.updated_at.strftime('%Y-%m-%d') if analysis.updated_at else datetime.now().strftime('%Y-%m-%d')
        })
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: Failed to save analysis: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/seed', methods=['POST'])
def seed():
    """Run scraper to populate market data, or generate mock data if mock=true."""
    if not session.get('user'): 
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json or {}
    use_mock = data.get('mock', False)
    
    # Mock data generation
    if use_mock:
        try:
            companies = [
                'OpenAI', 'Anthropic', 'Google', 'Meta', 
                'GitHub', 'Replit', 'Vercel', 'Stripe', 'Datadog'
            ]
            roles = ['Senior Engineer', 'Staff Engineer', 'Product Manager', 'Engineering Manager', 'Senior SWE']
            
            saved_count = 0
            for _ in range(50):
                company = random.choice(companies)
                role = random.choice(roles)
                
                # Check for duplicates
                existing = CompData.query.filter_by(
                    company_name=company,
                    role_title=role
                ).first()
                
                if not existing:
                    # Generate realistic salary ranges based on role
                    if 'Senior' in role or 'SWE' in role:
                        base = random.randint(200000, 350000)
                    elif 'Staff' in role:
                        base = random.randint(280000, 450000)
                    elif 'Manager' in role:
                        base = random.randint(250000, 400000)
                    else:
                        base = random.randint(180000, 300000)
                    
                    # Create a range around the base (typically ±15-25%)
                    range_pct = random.uniform(0.15, 0.25)
                    salary_min = int(base * (1 - range_pct))
                    salary_max = int(base * (1 + range_pct))
                    
                    db.session.add(CompData(
                        company_name=company,
                        role_title=role,
                        salary_min=salary_min,
                        salary_max=salary_max,
                        source_url=f'https://mock-data/{company.lower()}/jobs/{random.randint(1000, 9999)}'
                    ))
                    saved_count += 1
            
            db.session.commit()
            return jsonify({'status': 'success', 'count': saved_count, 'mode': 'mock'})
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Mock seed operation failed: {e}")
            return jsonify({'error': str(e)}), 500
    
    # Real scraper workflow
    targets = TargetCompany.query.all()
    company_url = data.get('company_url')
    role_keyword = data.get('role_keyword', 'Engineer')
    
    if not company_url:
        if not targets:
            return jsonify({'error': 'No target companies configured. Add some in Settings, or use mock=true for mock data.'}), 400
        # Use first target company
        target = targets[0]
        company_url = target.career_url
    
    try:
        # Use existing scraper workflow
        urls = ScraperService.discover_job_links(company_url, role_keyword)
        if not urls:
            return jsonify({'error': 'No matching jobs found'}), 400
        
        saved_count = 0
        
        for url in urls[:20]:  # Limit to 20 for seed operation
            time.sleep(1)
            raw = ScraperService.fetch_page_content(url)
            if raw:
                parsed_data = AnalysisEngine.parse_job_description_with_ai(raw)
                if parsed_data.get('max', 0) > 0:
                    # Check for duplicates
                    existing = CompData.query.filter_by(
                        company_name=parsed_data.get('company'),
                        role_title=parsed_data.get('job_title')
                    ).first()
                    
                    if not existing:
                        salary_min = parsed_data.get('min', 0)
                        salary_max = parsed_data.get('max', 0)
                        
                        # Handle case where min > max
                        if salary_min > salary_max:
                            salary_min, salary_max = salary_max, salary_min
                        
                        db.session.add(CompData(
                            company_name=parsed_data.get('company'),
                            role_title=parsed_data.get('job_title'),
                            salary_min=salary_min,
                            salary_max=salary_max,
                            source_url=url
                        ))
                        saved_count += 1
        
        db.session.commit()
        return jsonify({'status': 'success', 'count': saved_count, 'mode': 'scraper'})
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: Seed operation failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

def seed_db():
    """Legacy seed function - kept for backward compatibility"""
    if CompData.query.count() == 0:
        db.session.add(CompData(company_name="OpenAI", role_title="Senior SWE", salary_min=240000, salary_max=370000))
        db.session.add(CompData(company_name="Anthropic", role_title="Senior SWE", salary_min=230000, salary_max=360000))
        db.session.commit()

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)