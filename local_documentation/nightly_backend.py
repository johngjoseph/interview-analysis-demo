import random
from app import app, db, MarketData

def run_nightly_scrape():
    """
    This function simulates the nightly scraper.
    In a real scenario, this would import your 'ScraperService',
    crawl the URLs, and then save to DB.
    """
    print("Starting Nightly Scraper Job...")
    
    # 1. Setup Context (Required to access Flask-SQLAlchemy)
    with app.app_context():
        
        # Optional: Decide if you want to wipe old data or append
        # For a demo, wiping is often cleaner to keep the DB small.
        print("Clearing old market data...")
        db.session.query(MarketData).delete()
        
        # 2. The "Scraping" Logic (Using your mock data for now)
        companies = [
            'OpenAI', 'Anthropic', 'Google', 'Meta', 
            'GitHub', 'Replit', 'Vercel', 'Stripe', 'Datadog'
        ]
        roles = ['Senior Engineer', 'Staff Engineer', 'Product Manager', 'Eng Manager']
        
        new_records = []
        print(f"Scraping data for {len(companies)} companies...")
        
        for _ in range(75): # generating slightly more data for prod
            role_base = 180000 if 'Senior' in roles else 240000
            salary = int(role_base * random.uniform(0.8, 1.4))
            
            record = MarketData(
                company=random.choice(companies),
                role=random.choice(roles),
                level=random.choice(['L4', 'L5', 'L6']),
                salary=salary,
                source='Nightly Job - ' + datetime.now().strftime('%Y-%m-%d')
            )
            new_records.append(record)

        # 3. Batch Save
        db.session.add_all(new_records)
        db.session.commit()
        print(f"Successfully added {len(new_records)} records.")

if __name__ == "__main__":
    from datetime import datetime
    run_nightly_scrape()