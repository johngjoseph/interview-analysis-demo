I need you to build a **Recruiting Operations Platform** for a job interview demo. The goal is to demonstrate "Agentic Workflows" in recruiting—moving from data entry to strategic intelligence.  There are two primary things the application needs to do \- 1\) For a provided set of companies, crawl through their career site and extract salaries for each role ; 2\) When a recruiter is making an offer, pull up the right set of roles to provide context for the offers.

### **1\. Project Overview**

* **App Name:** RecOps AI  
* **Tech Stack:** Python (Flask), SQLite (Local) / Postgres (Prod), HTMX (Frontend), TailwindCSS, LangChain \+ OpenAI.  
* **Hosting:** Railway (so code must be production-ready).

### **2\. User Flow**

1. **Login:** User logs in via Google OAuth (restricted access).  
2. **Dashboard:** User sees a high-level "Deal Desk" and "Market Scout".  
3. **Settings & Scraper Lab (NEW):**  
   * **Configuration:** User manages a saved list of "Target Companies" (e.g., OpenAI, Anthropic) so they don't have to copy-paste URLs every time.  
   * **The Lab:** A debugging tool where the user can paste a URL and see *exactly* what the scraper sees (Raw HTML vs. Cleaned Text) to troubleshoot issues.  
4. **Use Case A: The Deal Desk (Offer Simulator)**  
   * User types a proposed salary.  
   * App visually benchmarks it against the scraped data in the DB.  
5. **Use Case B: The Market Scout (Agentic Crawler)**  
   * User clicks "Scan Targets" to crawl all configured companies automatically.  
   * **The Scout Agent:** Visits the page, reads all links, filters for "Engineer" roles using LLM reasoning.  
   * **The Miner Agent:** Visits the top matching links, extracts salary bands, and saves them to the DB.

### **3\. Implementation Instructions**

Please generate the following file structure with the **EXACT** code provided below. Do not simplify the logic.

#### **File 1: requirements.txt**

flask  
authlib  
requests  
flask\_sqlalchemy  
psycopg2-binary  
pandas  
numpy  
textblob  
gunicorn  
openai  
langchain  
langchain-community  
beautifulsoup4  
python-dotenv

#### **File 2: .gitignore**

venv/  
\_\_pycache\_\_/  
.env  
.DS\_Store  
instance/

#### **File 3: models.py**

(Added TargetCompany for configuration)

from flask\_sqlalchemy import SQLAlchemy  
from datetime import datetime

db \= SQLAlchemy()

class User(db.Model):  
    \_\_tablename\_\_ \= 'users'  
    id \= db.Column(db.Integer, primary\_key=True)  
    email \= db.Column(db.String(120), unique=True, nullable=False)  
    name \= db.Column(db.String(120))  
    picture \= db.Column(db.String(255))  
    created\_at \= db.Column(db.DateTime, default=datetime.utcnow)

class TargetCompany(db.Model):  
    \_\_tablename\_\_ \= 'target\_companies'  
    id \= db.Column(db.Integer, primary\_key=True)  
    name \= db.Column(db.String(100), nullable=False)  
    career\_url \= db.Column(db.String(500), nullable=False)  
    created\_at \= db.Column(db.DateTime, default=datetime.utcnow)

class CompData(db.Model):  
    \_\_tablename\_\_ \= 'comp\_data'  
    id \= db.Column(db.Integer, primary\_key=True)  
    company\_name \= db.Column(db.String(100), nullable=False)  
    role\_title \= db.Column(db.String(100), nullable=False)  
    salary\_min \= db.Column(db.Integer)  
    salary\_max \= db.Column(db.Integer)  
    currency \= db.Column(db.String(10), default='USD')  
    source\_url \= db.Column(db.String(500))  
    scraped\_at \= db.Column(db.DateTime, default=datetime.utcnow)

    def to\_dict(self):  
        return {  
            'company': self.company\_name,  
            'role': self.role\_title,  
            'min': self.salary\_min,  
            'max': self.salary\_max,  
            'avg': (self.salary\_min \+ self.salary\_max) / 2 if self.salary\_min and self.salary\_max else 0  
        }

#### **File 4: scraper\_service.py**

(Added debug\_fetch for troubleshooting)

import requests  
from bs4 import BeautifulSoup  
import time  
from langchain\_community.chat\_models import ChatOpenAI  
import os  
import json  
import re

class ScraperService:  
      
    @staticmethod  
    def fetch\_page\_content(url):  
        headers \= {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10\_15\_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'}  
        try:  
            response \= requests.get(url, headers=headers, timeout=10)  
            if response.status\_code \!= 200: return None  
              
            soup \= BeautifulSoup(response.text, 'html.parser')  
            \# Aggressive cleaning for token efficiency  
            for element in soup(\['script', 'style', 'nav', 'footer', 'header', 'svg', 'noscript', 'iframe'\]):  
                element.decompose()  
                  
            text \= soup.get\_text(separator=' ')  
            return " ".join(text.split())\[:12000\]  
        except Exception as e:  
            print(f"Fetch Error: {e}")  
            return None

    @staticmethod  
    def debug\_fetch(url):  
        """  
        Diagnostic tool for the Scraper Lab.  
        Returns detailed logs of what the scraper sees.  
        """  
        log \= {"steps": \[\], "preview": "", "success": False}  
        headers \= {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10\_15\_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'}  
          
        try:  
            log\["steps"\].append(f"1. Requesting {url}...")  
            start \= time.time()  
            response \= requests.get(url, headers=headers, timeout=10)  
            duration \= round(time.time() \- start, 2\)  
              
            log\["steps"\].append(f"2. Response received: {response.status\_code} ({duration}s)")  
              
            if response.status\_code \== 200:  
                soup \= BeautifulSoup(response.text, 'html.parser')  
                raw\_len \= len(response.text)  
                  
                for element in soup(\['script', 'style', 'nav', 'footer', 'header'\]):  
                    element.decompose()  
                  
                text \= soup.get\_text(separator=' ')  
                clean\_text \= " ".join(text.split())  
                  
                log\["steps"\].append(f"3. Cleaning HTML: Reduced {raw\_len} chars to {len(clean\_text)} chars")  
                log\["preview"\] \= clean\_text\[:500\] \+ "..."  
                log\["success"\] \= True  
            else:  
                log\["steps"\].append("3. Failed to retrieve content.")  
                  
        except Exception as e:  
            log\["steps"\].append(f"ERROR: {str(e)}")  
              
        return log

    @staticmethod  
    def discover\_job\_links(board\_url, role\_keyword):  
        headers \= {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10\_15\_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'}  
          
        try:  
            response \= requests.get(board\_url, headers=headers, timeout=10)  
            soup \= BeautifulSoup(response.text, 'html.parser')  
              
            candidates \= \[\]  
            seen \= set()  
              
            for a in soup.find\_all('a', href=True):  
                text \= a.get\_text(strip=True)  
                href \= a\['href'\]  
                  
                if len(text) \< 4 or "mailto" in href: continue  
                  
                if not href.startswith('http'):  
                    base \= "/".join(board\_url.split('/')\[:3\])  
                    href \= base \+ href if href.startswith('/') else base \+ '/' \+ href  
                  
                if href not in seen:  
                    candidates.append({"text": text, "url": href})  
                    seen.add(href)

            llm \= ChatOpenAI(temperature=0, model\_name="gpt-3.5-turbo", openai\_api\_key=os.getenv("OPENAI\_API\_KEY"))  
              
            prompt \= f"""  
            I look for roles matching: "{role\_keyword}".  
            Filter this list to ONLY relevant job posting links.  
            Ignore "Home", "Login", "Benefits".

            Links:  
            {json.dumps(candidates\[:60\])}

            Return valid JSON list of strings (URLs). Example: \["http://..."\]  
            """  
              
            result \= llm.invoke(prompt)  
            content \= result.content.strip()  
            if "\`\`\`" in content:  
                content \= re.search(r'\\\[.\*\\\]', content, re.DOTALL).group(0)  
              
            return json.loads(content)  
        except Exception as e:  
            print(f"Discovery Error: {e}")  
            return \[\]

#### **File 5: analysis\_engine.py**

import pandas as pd  
import numpy as np  
from models import CompData  
from langchain\_community.chat\_models import ChatOpenAI  
from langchain.prompts import PromptTemplate  
import os  
import json

class AnalysisEngine:  
      
    @staticmethod  
    def get\_market\_position(target\_company="Cursor"):  
        query \= CompData.query.all()  
        if not query: return {}  
          
        data \= \[row.to\_dict() for row in query\]  
        df \= pd.DataFrame(data)  
        if df.empty: return {}

        summary \= df.groupby('company').agg({  
            'avg': 'mean', 'min': 'min', 'max': 'max'  
        }).reset\_index()

        return {  
            "summary\_table": summary.to\_dict('records'),  
            "total\_records": len(df)  
        }

    @staticmethod  
    def run\_capacity\_model(team\_size=5):  
        weekly\_hours \= team\_size \* 40 \* 0.85  
        np.random.seed(42)  
        demand \= np.random.normal(loc=weekly\_hours, scale=30, size=12).astype(int).tolist()  
        return {"weekly\_capacity": int(weekly\_hours), "projected\_demand": demand}

    @staticmethod  
    def parse\_job\_description\_with\_ai(text\_content):  
        try:  
            llm \= ChatOpenAI(temperature=0, model\_name="gpt-3.5-turbo", openai\_api\_key=os.getenv("OPENAI\_API\_KEY"))  
              
            prompt \= PromptTemplate.from\_template(  
                """  
                Extract Base Salary Range, Job Title, and Company Name.  
                Ignore equity/benefits. Convert "150k" to 150000\.  
                If no salary found, return 0\.  
                  
                Return JSON:  
                {{  
                    "job\_title": "String",  
                    "company": "String",  
                    "min": Number,  
                    "max": Number  
                }}

                Text: {text}  
                """  
            )  
            chain \= prompt | llm  
            return json.loads(chain.invoke({"text": text\_content}).content)  
        except:  
            return {"min": 0, "max": 0}

#### **File 6: app.py**

(Added Settings Routes)

import os  
import time  
from flask import Flask, url\_for, session, redirect, render\_template, request  
from authlib.integrations.flask\_client import OAuth  
from models import db, User, CompData, TargetCompany  
from analysis\_engine import AnalysisEngine  
from scraper\_service import ScraperService  
from dotenv import load\_dotenv

load\_dotenv()

app \= Flask(\_\_name\_\_)  
app.secret\_key \= os.getenv("FLASK\_SECRET", "dev\_key")  
app.config\['SQLALCHEMY\_DATABASE\_URI'\] \= os.getenv("DATABASE\_URL", "sqlite:///local.db")  
app.config\['SQLALCHEMY\_TRACK\_MODIFICATIONS'\] \= False

db.init\_app(app)  
oauth \= OAuth(app)

google \= oauth.register(  
    name='google',  
    client\_id=os.getenv("GOOGLE\_CLIENT\_ID"),  
    client\_secret=os.getenv("GOOGLE\_CLIENT\_SECRET"),  
    access\_token\_url='https://accounts.google.com/o/oauth2/token',  
    authorize\_url='https://accounts.google.com/o/oauth2/auth',  
    api\_base\_url='https://www.googleapis.com/oauth2/v1/',  
    client\_kwargs={'scope': 'openid email profile'},  
)

@app.route('/')  
def home():  
    if session.get('user'): return redirect('/dashboard')  
    return render\_template('login.html')

@app.route('/login')  
def login():  
    return google.authorize\_redirect(url\_for('authorize', \_external=True))

@app.route('/auth/callback')  
def authorize():  
    try:  
        token \= google.authorize\_access\_token()  
        user\_info \= google.get('userinfo').json()  
        session\['user'\] \= user\_info  
        if not User.query.filter\_by(email=user\_info\['email'\]).first():  
            db.session.add(User(email=user\_info\['email'\], name=user\_info.get('name')))  
            db.session.commit()  
        return redirect('/dashboard')  
    except:  
        return "Auth Error"

@app.route('/dashboard')  
def dashboard():  
    if not session.get('user'): return redirect('/')  
      
    \# Use saved companies for the dropdown/scout  
    targets \= TargetCompany.query.all()  
      
    market \= AnalysisEngine.get\_market\_position()  
    capacity \= AnalysisEngine.run\_capacity\_model()  
    return render\_template('dashboard.html', user=session\['user'\], market=market, capacity=capacity, targets=targets)

@app.route('/settings')  
def settings():  
    if not session.get('user'): return redirect('/')  
    targets \= TargetCompany.query.all()  
    return render\_template('settings.html', user=session\['user'\], targets=targets)

@app.route('/settings/add', methods=\['POST'\])  
def add\_target():  
    if not session.get('user'): return "", 403  
    name \= request.form.get('name')  
    url \= request.form.get('url')  
    if name and url:  
        db.session.add(TargetCompany(name=name, career\_url=url))  
        db.session.commit()  
    return redirect('/settings')

@app.route('/settings/delete/\<int:id\>', methods=\['DELETE'\])  
def delete\_target(id):  
    if not session.get('user'): return "", 403  
    TargetCompany.query.filter\_by(id=id).delete()  
    db.session.commit()  
    return ""

@app.route('/settings/debug', methods=\['POST'\])  
def debug\_scrape():  
    if not session.get('user'): return "", 403  
    url \= request.form.get('debug\_url')  
    log \= ScraperService.debug\_fetch(url)  
      
    status\_color \= "text-green-600" if log\['success'\] else "text-red-600"  
      
    return f"""  
    \<div class="mt-4 p-4 bg-gray-900 text-gray-100 rounded font-mono text-xs overflow-auto h-64"\>  
        \<div class="{status\_color} font-bold mb-2"\>Debug Result: {"SUCCESS" if log\['success'\] else "FAILED"}\</div\>  
        \<div class="mb-2"\>Log Steps:\</div\>  
        \<ul class="list-disc pl-4 mb-4 text-gray-400"\>  
            {''.join(\[f'\<li\>{s}\</li\>' for s in log\['steps'\]\])}  
        \</ul\>  
        \<div class="mb-2"\>Cleaned Text Preview (First 500 chars):\</div\>  
        \<div class="p-2 bg-black rounded border border-gray-700 whitespace-pre-wrap"\>{log.get('preview', 'No content')}\</div\>  
    \</div\>  
    """

@app.route('/run-bulk-crawl', methods=\['POST'\])  
def run\_bulk\_crawl():  
    if not session.get('user'): return "", 403  
      
    \# Allow manual override or use list  
    board\_url \= request.form.get('company\_url')  
    keyword \= request.form.get('role\_keyword')  
      
    urls \= ScraperService.discover\_job\_links(board\_url, keyword)  
    if not urls: return "\<div class='text-red-500'\>No matching jobs found via AI Scout.\</div\>"

    results\_html \= ""  
    for url in urls\[:4\]:  
        time.sleep(1)  
        raw \= ScraperService.fetch\_page\_content(url)  
        if raw:  
            data \= AnalysisEngine.parse\_job\_description\_with\_ai(raw)  
            if data.get('max', 0\) \> 0:  
                db.session.add(CompData(  
                    company\_name=data.get('company', 'Scraped'),  
                    role\_title=data.get('job\_title', keyword),  
                    salary\_min=data.get('min'),  
                    salary\_max=data.get('max'),  
                    source\_url=url  
                ))  
                results\_html \+= f"""  
                \<div class="flex justify-between p-2 mb-1 bg-green-50 border border-green-200 text-sm rounded"\>  
                    \<div\>\<b\>{data.get('job\_title')}\</b\>\</div\>  
                    \<div class="font-mono"\>${data.get('min'):,} \- ${data.get('max'):,}\</div\>  
                \</div\>"""  
      
    db.session.commit()  
    return f"\<div class='p-3 bg-white border rounded'\>\<strong\>Agent Report:\</strong\>\<br\>{results\_html}\</div\>"

@app.route('/logout')  
def logout():  
    session.pop('user', None)  
    return redirect('/')

with app.app\_context():  
    db.create\_all()

if \_\_name\_\_ \== "\_\_main\_\_":  
    app.run(debug=True)

#### **File 7: templates/settings.html**

(New File: Configuration & Lab)

\<\!DOCTYPE html\>  
\<html lang="en"\>  
\<head\>  
    \<title\>RecOps Settings\</title\>  
    \<script src="https://cdn.tailwindcss.com"\>\</script\>  
    \<script src="https://unpkg.com/htmx.org@1.9.10"\>\</script\>  
\</head\>  
\<body class="bg-slate-50 min-h-screen"\>  
    \<nav class="bg-white border-b h-16 flex items-center justify-between px-8"\>  
        \<a href="/dashboard" class="text-xl font-bold text-slate-800"\>RecOps \<span class="text-blue-600"\>AI\</span\>\</a\>  
        \<div class="flex gap-4 text-sm"\>  
            \<a href="/dashboard" class="text-gray-500 hover:text-blue-600"\>Dashboard\</a\>  
            \<span class="font-bold text-blue-600"\>Settings\</span\>  
            \<a href="/logout" class="text-red-500"\>Logout\</a\>  
        \</div\>  
    \</nav\>

    \<main class="max-w-4xl mx-auto mt-8 px-4"\>  
          
        \<div class="grid grid-cols-1 md:grid-cols-2 gap-8"\>  
            \<\!-- CONFIGURATION \--\>  
            \<div class="bg-white rounded-xl shadow p-6"\>  
                \<h2 class="text-lg font-bold text-gray-800 mb-4"\>Target Companies\</h2\>  
                \<form action="/settings/add" method="POST" class="mb-6 bg-gray-50 p-4 rounded border border-gray-200"\>  
                    \<div class="space-y-3"\>  
                        \<input type="text" name="name" placeholder="Company Name (e.g. OpenAI)" class="w-full border p-2 rounded text-sm" required\>  
                        \<input type="url" name="url" placeholder="Career Page URL" class="w-full border p-2 rounded text-sm" required\>  
                        \<button type="submit" class="w-full bg-blue-600 text-white font-bold py-2 rounded text-sm hover:bg-blue-700"\>Add Target\</button\>  
                    \</div\>  
                \</form\>

                \<div class="space-y-2"\>  
                    {% for target in targets %}  
                    \<div class="flex justify-between items-center p-3 border rounded hover:bg-gray-50 group"\>  
                        \<div\>  
                            \<div class="font-bold text-sm"\>{{ target.name }}\</div\>  
                            \<div class="text-xs text-gray-500 truncate w-48"\>{{ target.career\_url }}\</div\>  
                        \</div\>  
                        \<button hx-delete="/settings/delete/{{ target.id }}" hx-target="closest div" hx-swap="outerHTML"   
                                class="text-red-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity"\>  
                            Delete  
                        \</button\>  
                    \</div\>  
                    {% endfor %}  
                \</div\>  
            \</div\>

            \<\!-- SCRAPER LAB \--\>  
            \<div class="bg-white rounded-xl shadow p-6"\>  
                \<h2 class="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2"\>  
                    \<svg class="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"\>\<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.384-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" /\>\</svg\>  
                    Scraper Lab (Debug)  
                \</h2\>  
                \<p class="text-xs text-gray-500 mb-4"\>Troubleshoot scraping issues by seeing exactly what the bot sees.\</p\>  
                  
                \<form hx-post="/settings/debug" hx-target="\#debug-results" hx-swap="innerHTML"\>  
                    \<label class="block text-xs font-bold text-gray-500 uppercase mb-1"\>Test URL\</label\>  
                    \<div class="flex gap-2"\>  
                        \<input type="url" name="debug\_url" placeholder="Paste URL to test..." class="flex-grow border p-2 rounded text-sm"\>  
                        \<button type="submit" class="bg-purple-600 text-white px-4 rounded text-sm font-bold"\>Test\</button\>  
                    \</div\>  
                \</form\>

                \<div id="debug-results" class="mt-4"\>\</div\>  
            \</div\>  
        \</div\>  
    \</main\>  
\</body\>  
\</html\>

#### **File 8: templates/dashboard.html**

(Added link to Settings)

\<\!DOCTYPE html\>  
\<html lang="en"\>  
\<head\>  
    \<title\>RecOps Dashboard\</title\>  
    \<script src="https://cdn.tailwindcss.com"\>\</script\>  
    \<script src="https://cdn.jsdelivr.net/npm/chart.js"\>\</script\>  
    \<script src="https://unpkg.com/htmx.org@1.9.10"\>\</script\>  
    \<style\> .htmx-request.btn { opacity: 0.5; cursor: wait; } \</style\>  
\</head\>  
\<body class="bg-slate-50 min-h-screen pb-10"\>  
    \<nav class="bg-white border-b h-16 flex items-center justify-between px-8"\>  
        \<span class="text-xl font-bold text-slate-800"\>RecOps \<span class="text-blue-600"\>AI\</span\>\</span\>  
        \<div class="flex gap-4 text-sm items-center"\>  
            \<a href="/settings" class="text-gray-500 hover:text-blue-600 flex items-center gap-1"\>  
                \<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"\>\<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"\>\</path\>\<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"\>\</path\>\</svg\>  
                Settings  
            \</a\>  
            \<span class="text-gray-300"\>|\</span\>  
            \<span\>{{ user.name }}\</span\>  
            \<a href="/logout" class="text-red-500"\>Logout\</a\>  
        \</div\>  
    \</nav\>

    \<main class="max-w-6xl mx-auto mt-8 px-4"\>  
          
        \<\!-- OFFER SIMULATOR \--\>  
        \<div class="bg-indigo-900 rounded-xl shadow-lg p-6 mb-8 text-white"\>  
            \<h2 class="text-xl font-bold mb-4"\>Offer Simulator (Deal Desk)\</h2\>  
            \<div class="grid grid-cols-1 md:grid-cols-3 gap-6"\>  
                \<div\>  
                    \<label class="block text-xs font-bold text-indigo-300 uppercase mb-1"\>Proposed Salary\</label\>  
                    \<input type="number" id="offerInput" value="210000" class="w-full text-slate-900 font-bold text-xl p-2 rounded" placeholder="0.00"\>  
                    \<button onclick="recalcOffer()" class="mt-3 w-full bg-indigo-500 hover:bg-indigo-600 font-bold py-2 rounded"\>Analyze Strength\</button\>  
                \</div\>  
                \<div class="md:col-span-2 bg-indigo-800 rounded-lg p-4 space-y-3"\>  
                    \<h3 class="font-bold text-indigo-100 mb-2"\>Competitive Landscape\</h3\>  
                    {% for row in market.summary\_table %}  
                    \<div class="flex items-center text-sm"\>  
                        \<div class="w-24 font-medium text-indigo-200"\>{{ row.company }}\</div\>  
                        \<div class="flex-grow mx-3 relative h-4 bg-indigo-900 rounded-full overflow-hidden"\>  
                            \<div class="absolute h-full bg-indigo-600 opacity-50 w-full"\>\</div\>  
                            \<div id="marker-{{loop.index}}" class="absolute h-full w-1 bg-yellow-400 z-10 transition-all duration-500" style="left: 50%"\>\</div\>  
                        \</div\>  
                        \<div class="w-32 text-right font-mono" id="label-{{loop.index}}"\>...\</div\>  
                    \</div\>  
                    {% endfor %}  
                \</div\>  
            \</div\>  
        \</div\>

        \<\!-- AGENT CRAWLER \--\>  
        \<div class="bg-white rounded-xl shadow p-6 mb-8 border border-gray-200"\>  
            \<h2 class="font-bold text-gray-800 mb-4 flex items-center gap-2"\>  
                \<svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"\>\<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"\>\</path\>\</svg\>  
                Live Market Scout  
            \</h2\>  
            \<form hx-post="/run-bulk-crawl" hx-target="\#results" hx-swap="innerHTML" class="flex gap-4 items-end"\>  
                \<div class="flex-grow"\>  
                    \<label class="text-xs font-bold text-gray-500 uppercase"\>Target Company\</label\>  
                    \<select name="company\_url" class="w-full border p-2 rounded h-10"\>  
                        \<option value="" disabled selected\>Select from saved targets...\</option\>  
                        {% for t in targets %}  
                        \<option value="{{ t.career\_url }}"\>{{ t.name }}\</option\>  
                        {% endfor %}  
                    \</select\>  
                \</div\>  
                \<div class="w-1/3"\>  
                    \<label class="text-xs font-bold text-gray-500 uppercase"\>Role Keyword\</label\>  
                    \<input type="text" name="role\_keyword" placeholder="e.g. Engineer" class="w-full border p-2 rounded h-10"\>  
                \</div\>  
                \<button type="submit" class="btn bg-blue-600 text-white font-bold py-2 px-6 rounded h-10"\>Launch Scout\</button\>  
            \</form\>  
            \<div id="results" class="mt-4"\>\</div\>  
        \</div\>

        \<\!-- CAPACITY CHART \--\>  
        \<div class="bg-white rounded-xl shadow p-6 border border-gray-200"\>  
            \<h3 class="font-bold text-gray-800 mb-4"\>Q4 Capacity Forecast\</h3\>  
            \<canvas id="capChart" height="80"\>\</canvas\>  
        \</div\>  
    \</main\>

    \<script\>  
        // Offer Logic  
        function recalcOffer() {  
            const offer \= parseInt(document.getElementById('offerInput').value);  
            const vizMin \= 150000; const vizMax \= 450000;  
              
            {% for row in market.summary\_table %}  
                let pct \= ((offer \- vizMin) / (vizMax \- vizMin)) \* 100;  
                document.getElementById(\`marker-{{loop.index}}\`).style.left \= Math.max(0, Math.min(100, pct)) \+ '%';  
                  
                let el \= document.getElementById(\`label-{{loop.index}}\`);  
                if (offer \< {{row.min}}) el.innerHTML \= \`\<span class='text-red-400 font-bold'\>Lose (-$${Math.round(({{row.min}}-offer)/1000)}k)\</span\>\`;  
                else if (offer \> {{row.max}}) el.innerHTML \= \`\<span class='text-green-400 font-bold'\>Win (+$${Math.round((offer-{{row.max}})/1000)}k)\</span\>\`;  
                else el.innerHTML \= \`\<span class='text-yellow-400'\>Competitive\</span\>\`;  
            {% endfor %}  
        }  
        setTimeout(recalcOffer, 500);

        // Chart Logic  
        new Chart(document.getElementById('capChart'), {  
            type: 'line',  
            data: {  
                labels: Array.from({length: 12}, (\_, i) \=\> \`W${i+1}\`),  
                datasets: \[{  
                    label: 'Demand',  
                    data: {{ capacity.projected\_demand | tojson }},  
                    borderColor: '\#2563EB', tension: 0.4  
                }, {  
                    label: 'Limit',  
                    data: Array(12).fill({{ capacity.weekly\_capacity }}),  
                    borderColor: '\#DC2626', borderDash: \[5, 5\]  
                }\]  
            }  
        });  
    \</script\>  
\</body\>  
\</html\>

#### **File 9: templates/login.html**

\<\!DOCTYPE html\>  
\<html lang="en"\>  
\<head\>  
    \<meta charset="UTF-8"\>  
    \<title\>RecOps Login\</title\>  
    \<script src="https://cdn.tailwindcss.com"\>\</script\>  
\</head\>  
\<body class="bg-slate-900 h-screen flex items-center justify-center"\>  
    \<div class="bg-white p-10 rounded-xl shadow-2xl text-center"\>  
        \<h1 class="text-3xl font-bold text-slate-800 mb-2"\>Recruiting Ops\</h1\>  
        \<p class="text-slate-500 mb-8"\>Competitive Intelligence Platform\</p\>  
        \<a href="/login" class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg"\>Sign in with Google\</a\>  
    \</div\>  
\</body\>  
\</html\>  
