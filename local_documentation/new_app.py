import os
import random
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func

app = Flask(__name__)

# --- Config ---
# Use Railway's DATABASE_URL or fallback to local sqlite
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///talentscout.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Models ---
class MarketData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company = db.Column(db.String(100))
    role = db.Column(db.String(100))
    level = db.Column(db.String(50))
    salary = db.Column(db.Integer)
    source = db.Column(db.String(200))

class OfferAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), default="New Analysis")
    candidate_name = db.Column(db.String(100), default="")
    target_role = db.Column(db.String(100), default="")
    proposed_salary = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='Draft')
    notes = db.Column(db.Text, default="")
    selected_ids = db.Column(db.String(500), default="") # Comma separated IDs
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now(), default=func.now())

# --- Routes ---

@app.route('/')
def index():
    """
    The Single Page App Entry Point.
    We inject ALL initial data here so the UI is instant.
    """
    # 1. Fetch Market Data
    market_rows = MarketData.query.all()
    market_data = [{
        'id': r.id, 
        'company': r.company, 
        'role': r.role, 
        'level': r.level, 
        'salary': r.salary
    } for r in market_rows]

    # 2. Fetch Recent Analyses
    analysis_rows = OfferAnalysis.query.order_by(OfferAnalysis.updated_at.desc()).all()
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

    return render_template('index.html', 
                         market_data=market_data, 
                         analyses=analyses)

@app.route('/api/save', methods=['POST'])
def save_analysis():
    data = request.json
    
    if data.get('id'):
        # Update existing
        analysis = OfferAnalysis.query.get(data['id'])
    else:
        # Create new
        analysis = OfferAnalysis()
        db.session.add(analysis)
    
    # Map JSON fields to DB columns
    analysis.title = data.get('title', 'New Analysis')
    analysis.candidate_name = data.get('candidateName', '')
    analysis.target_role = data.get('targetRole', '')
    analysis.proposed_salary = int(data.get('proposedSalary', 0))
    analysis.notes = data.get('notes', '')
    analysis.status = data.get('status', 'Draft')
    # Convert list of IDs back to CSV string
    analysis.selected_ids = ",".join(map(str, data.get('selectedIds', [])))
    
    db.session.commit()
    
    return jsonify({'status': 'success', 'id': analysis.id, 'updatedAt': datetime.now().strftime('%Y-%m-%d')})

@app.route('/api/seed', methods=['POST'])
def seed():
    # Clear old data for demo
    db.session.query(MarketData).delete()
    
    companies = ['Google', 'Meta', 'OpenAI', 'Anthropic', 'Netflix', 'Amazon', 'Datadog']
    roles = ['Senior Engineer', 'Staff Engineer', 'Product Manager', 'Eng Manager']
    
    for _ in range(50):
        role_base = 180000 if 'Senior' in roles else 240000
        salary = int(role_base * random.uniform(0.8, 1.4))
        
        db.session.add(MarketData(
            company=random.choice(companies),
            role=random.choice(roles),
            level=random.choice(['L4', 'L5', 'L6']),
            salary=salary,
            source='Automated Scraper'
        ))
    db.session.commit()
    return jsonify({'status': 'seeded', 'count': 50})

# --- Init ---
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5000)