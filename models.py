from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.sql import func

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120))
    picture = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TargetCompany(db.Model):
    __tablename__ = 'target_companies'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    career_url = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CompData(db.Model):
    __tablename__ = 'comp_data'
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    role_title = db.Column(db.String(100), nullable=False)
    salary_min = db.Column(db.Integer)
    salary_max = db.Column(db.Integer)
    currency = db.Column(db.String(10), default='USD')
    source_url = db.Column(db.String(500))
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'company': self.company_name,
            'role': self.role_title,
            'min': self.salary_min,
            'max': self.salary_max,
            'avg': (self.salary_min + self.salary_max) / 2 if self.salary_min and self.salary_max else 0
        }
    
    def to_market_data_dict(self):
        """Convert CompData to MarketData format for SPA"""
        return {
            'id': self.id,
            'company': self.company_name,
            'role': self.role_title,
            'level': '',  # Can extract from role_title if needed
            'salary': int((self.salary_min + self.salary_max) / 2) if self.salary_min and self.salary_max else 0
        }

class OfferAnalysis(db.Model):
    __tablename__ = 'offer_analyses'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), default="New Analysis")
    candidate_name = db.Column(db.String(100), default="")
    target_role = db.Column(db.String(100), default="")
    proposed_salary = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='Draft')
    notes = db.Column(db.Text, default="")
    selected_ids = db.Column(db.String(500), default="")  # Comma-separated CompData IDs
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now(), default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # Link to User