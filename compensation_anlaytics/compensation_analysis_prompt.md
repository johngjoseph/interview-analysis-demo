# **Master Prompt for Cursor IDE**

**Instructions:** Copy the text below and paste it into the Cursor Chat or Composer.

I need to build a **"Hiring Intelligence Product"** for a compensation strategy analysis. This is a Streamlit application backed by a local ETL script and a data science logic library.

Please create the following 4 files in my workspace:

### **1\. requirements.txt**

pandas  
duckdb  
streamlit  
plotly  
scikit-learn  
numpy  
requests  
pyarrow

### **2\. etl.py (The Data Engine)**

This script generates the mock data for offers, employees, equity pool, and interview capacity.

import duckdb  
import pandas as pd  
import numpy as np  
import os  
import requests  
import base64  
from datetime import datetime, timedelta

\# \--- CONFIGURATION \---  
REAL\_DATA\_MODE \= True  
ASHBY\_API\_KEY \= os.getenv("ASHBY\_API\_KEY", "")

os.makedirs('data', exist\_ok=True)

def fetch\_ashby\_data():  
    \# Placeholder for real API logic  
    return pd.DataFrame() 

def generate\_mock\_data():  
    """  
    Generates rich mock data for ALL 10+ ANALYSES.  
    """  
    np.random.seed(42)  
    n\_offers \= 1200  
    n\_employees \= 350

    print("⚠️ Generating rich MOCK data for full suite...")

    \# \--- 1\. ATS / RECRUITING DATA \---  
    end\_date \= datetime.now()  
    start\_date \= end\_date \- timedelta(days=730)  
    dates \= \[start\_date \+ timedelta(days=np.random.randint(0, 730)) for \_ in range(n\_offers)\]  
      
    \# Define Departments & Roles  
    depts \= \['Engineering', 'Product', 'Sales', 'G\&A', 'Design'\]  
    levels \= \['L3', 'L4', 'L5', 'L6', 'L7'\]  
      
    ats\_data \= pd.DataFrame({  
        'candidate\_id': range(n\_offers),  
        'department': np.random.choice(depts, n\_offers, p=\[0.5, 0.15, 0.2, 0.1, 0.05\]),  
        'level': np.random.choice(levels, n\_offers, p=\[0.1, 0.3, 0.4, 0.15, 0.05\]),  
        'location': np.random.choice(\['SF', 'London', 'Remote'\], n\_offers, p=\[0.6, 0.2, 0.2\]),  
        'source': np.random.choice(\['Referral', 'Inbound', 'Agency', 'Sourcing'\], n\_offers),  
        'application\_date': dates,  
        'status': np.random.choice(\['Accepted', 'Rejected'\], n\_offers, p=\[0.88, 0.12\]),   
    })  
      
    \# Assign Roles based on Dept  
    ats\_data\['role'\] \= ats\_data\['department'\] \+ " " \+ ats\_data\['level'\]  
      
    \# Generate Offers with Variance  
    ats\_data\['offer\_base'\] \= ats\_data\['level'\].map({'L3': 140000, 'L4': 180000, 'L5': 240000, 'L6': 320000, 'L7': 400000}) \* np.random.uniform(0.9, 1.2, n\_offers)  
    ats\_data\['offer\_equity\_4yr'\] \= ats\_data\['level'\].map({'L3': 200000, 'L4': 400000, 'L5': 1000000, 'L6': 2500000, 'L7': 4000000}) \* np.random.uniform(0.8, 1.5, n\_offers)  
      
    \# Decline Reasons  
    ats\_data\['decline\_reason'\] \= ats\_data.apply(  
        lambda x: np.random.choice(\['Base Salary', 'Equity Value', 'Remote Policy', 'Competitor Brand', 'Title'\]) if x\['status'\] \== 'Rejected' else None, axis=1  
    )  
      
    ats\_data\['total\_comp'\] \= ats\_data\['offer\_base'\] \+ (ats\_data\['offer\_equity\_4yr'\] / 4\)  
    ats\_data\['comp\_quartile'\] \= pd.qcut(ats\_data\['total\_comp'\], 4, labels=\['Q1', 'Q2', 'Q3', 'Q4'\])

    \# \--- 2\. EMPLOYEE DATA (Internal Equity) \---  
    emp\_dates \= \[end\_date \- timedelta(days=np.random.randint(30, 1500)) for \_ in range(n\_employees)\]  
      
    employees \= pd.DataFrame({  
        'employee\_id': range(n\_employees),  
        'department': np.random.choice(depts, n\_employees, p=\[0.5, 0.15, 0.2, 0.1, 0.05\]),  
        'level': np.random.choice(levels, n\_employees, p=\[0.1, 0.3, 0.4, 0.15, 0.05\]),  
        'start\_date': emp\_dates,  
        \# Salary logic: Older employees might have lower base (Compression risk)  
        'base\_salary': 0,   
        'performance\_rating': np.random.choice(\[1, 2, 3, 4, 5\], n\_employees)  
    })  
      
    \# Simulate Salary Compression: Base salary grows 2% a year, but market grows 5%  
    \# So older employees (high tenure) have lower relative salary than new hires  
    employees\['years\_tenure'\] \= (datetime.now() \- employees\['start\_date'\]).dt.days / 365  
    employees\['market\_base'\] \= employees\['level'\].map({'L3': 140000, 'L4': 180000, 'L5': 240000, 'L6': 320000, 'L7': 400000})  
      
    \# Apply tenure penalty (Mocking the compression issue)  
    employees\['base\_salary'\] \= employees\['market\_base'\] \* (1 \- (employees\['years\_tenure'\] \* 0.02)) \* np.random.uniform(0.95, 1.05, n\_employees)  
    employees\['total\_cash'\] \= employees\['base\_salary'\] \# \+ Bonus if needed

    \# \--- 3\. MARKET BENCHMARKS (External Equity) \---  
    \# Create benchmarks for every Level/Dept combo  
    market\_rows \= \[\]  
    for d in depts:  
        for l in levels:  
            base\_p50 \= {'L3': 140000, 'L4': 180000, 'L5': 240000, 'L6': 320000, 'L7': 400000}\[l\]  
            \# Eng gets premium  
            if d \== 'Engineering': base\_p50 \*= 1.15  
              
            market\_rows.append({  
                'department': d,  
                'level': l,  
                'market\_p50\_cash': base\_p50,  
                'market\_p75\_cash': base\_p50 \* 1.15  
            })  
    market\_df \= pd.DataFrame(market\_rows)

    \# \--- 4\. EQUITY POOL (Burn Forecast) \---  
    \# Total Pool: 50M shares. Used: 30M. Remaining: 20M.  
    \# We need to forecast usage.  
    equity\_pool \= pd.DataFrame({  
        'metric': \['Total Pool', 'Used', 'Remaining'\],  
        'shares': \[50000000, 30000000, 20000000\]  
    })  
      
    \# \--- 5\. INTERVIEW LOAD \---  
    weeks \= pd.date\_range(end=datetime.now(), periods=52, freq='W')  
    interview\_load \= pd.DataFrame({  
        'week': weeks,  
        'onsite\_interviews': np.random.randint(10, 50, 52),  
        'hours\_per\_interview': 16   
    })  
    interview\_load\['total\_eng\_hours'\] \= interview\_load\['onsite\_interviews'\] \* interview\_load\['hours\_per\_interview'\]

    return ats\_data, employees, market\_df, equity\_pool, interview\_load

def run\_pipeline():  
    ats\_df, emp\_df, market\_df, pool\_df, interview\_df \= generate\_mock\_data()  
      
    \# Calculate Compa-Ratios for Heatmap  
    \# Join Employees with Market  
    emp\_merged \= pd.merge(emp\_df, market\_df, on=\['department', 'level'\], how='left')  
    emp\_merged\['compa\_ratio'\] \= emp\_merged\['base\_salary'\] / emp\_merged\['market\_p50\_cash'\]  
      
    \# Save  
    ats\_df.to\_parquet('data/ats\_data.parquet')  
    emp\_merged.to\_parquet('data/employee\_data.parquet') \# Now includes market data \+ compa\_ratio  
    pool\_df.to\_parquet('data/equity\_pool.parquet')  
    interview\_df.to\_parquet('data/interview\_data.parquet')  
      
    print("✅ Pipeline complete. All datasets generated.")

if \_\_name\_\_ \== "\_\_main\_\_":  
    run\_pipeline()

### **3\. science.py (Analysis Logic)**

This handles the Monte Carlo simulation and burnout math.

import numpy as np  
import pandas as pd  
from sklearn.linear\_model import LogisticRegression

\# \--- EXISTING FUNCTIONS \---  
def run\_monte\_carlo\_simulation(grant\_value, simulations=10000):  
    results \= \[\]  
    for \_ in range(simulations):  
        scenario\_roll \= np.random.random()  
        if scenario\_roll \< 0.10: multiplier \= np.random.uniform(0, 0.5)  
        elif scenario\_roll \< 0.60: multiplier \= np.random.uniform(1.5, 3.5)  
        elif scenario\_roll \< 0.90: multiplier \= np.random.uniform(4.0, 6.0)  
        else: multiplier \= np.random.uniform(8.0, 15.0)  
        results.append(grant\_value \* multiplier)  
    return results

def calculate\_win\_probability(df, offer\_amount):  
    \# Heuristic Fallback for Demo  
    market\_mid \= 400000   
    k \= 0.00002   
    probability \= 1 / (1 \+ np.exp(-k \* (offer\_amount \- market\_mid)))  
    return probability

def calculate\_retention\_risk(employees\_df, market\_df):  
    """  
    Identifies 'Vest in Peace' vs 'Flight Risk' employees.  
    Risk Logic: Unvested Value / Market Replacement Grant  
    """  
    \# Join employees with market data  
    merged \= pd.merge(employees\_df, market\_df, on='role', how='left')  
      
    \# Calculate Ratio  
    \# If Ratio \> 2.0: They have 2x market value unvested. They won't leave (Vest in Peace).  
    \# If Ratio \< 0.8: They have less unvested than a new hire gets. Flight Risk.  
    merged\['retention\_ratio'\] \= merged\['unvested\_value'\] / merged\['market\_new\_hire\_grant'\]  
      
    merged\['risk\_category'\] \= merged.apply(  
        lambda x: '🔒 Golden Handcuffs (Safe)' if x\['retention\_ratio'\] \> 1.5  
        else ('⚠️ Flight Risk (Underwater)' if x\['retention\_ratio'\] \< 0.8 else 'Neutral'),  
        axis=1  
    )  
    return merged

def predict\_burnout(interview\_df, hiring\_target=800):  
    """  
    Project future engineering hours needed based on target.  
    """  
    avg\_hours\_per\_hire \= 40 \# Heuristic: 2 days onsite \+ screens \+ debriefs  
    total\_hours\_needed \= hiring\_target \* avg\_hours\_per\_hire  
      
    \# If we have 200 engineers, and they work 2000 hours a year  
    total\_capacity \= 200 \* 2000   
    burnout\_impact \= total\_hours\_needed / total\_capacity  
    return total\_hours\_needed, burnout\_impact

### **4\. app.py (The Dashboard)**

import streamlit as st  
import pandas as pd  
import plotly.express as px  
import plotly.graph\_objects as go  
import science   
import os  
import numpy as np

st.set\_page\_config(page\_title="Cursor Talent Intelligence", layout="wide")  
st.title("Cursor Comp & Ops Command Center")

\# \--- DATA LOADING \---  
if not os.path.exists('data/ats\_data.parquet'):  
    st.error("Data missing. Run 'python etl.py'")  
    st.stop()

ats\_df \= pd.read\_parquet('data/ats\_data.parquet')  
emp\_df \= pd.read\_parquet('data/employee\_data.parquet')  
pool\_df \= pd.read\_parquet('data/equity\_pool.parquet')  
interview\_df \= pd.read\_parquet('data/interview\_data.parquet')

\# \--- TABS \---  
tab\_health, tab\_eff, tab\_internal, tab\_market, tab\_finance, tab\_ops \= st.tabs(\[  
    "📊 Talent Health",   
    "📉 Efficiency",   
    "⚖️ Internal Equity",   
    "🌍 Market Heatmap",   
    "💰 Equity Burn",  
    "🔥 Ops Capacity"  
\])

\# \--- TAB 1: HEALTH (New Win/Loss Chart) \---  
with tab\_health:  
    st.markdown("\#\#\# Recruiting Pipeline Health")  
    k1, k2, k3 \= st.columns(3)  
    k1.metric("Offers Accepted", len(ats\_df\[ats\_df\['status'\]=='Accepted'\]))  
    k2.metric("Win Rate", f"{len(ats\_df\[ats\_df\['status'\]=='Accepted'\]) / len(ats\_df):.1%}")  
    k3.metric("Avg Base Salary", f"${ats\_df\['offer\_base'\].mean():,.0f}")  
      
    st.markdown("---")  
      
    c1, c2 \= st.columns(2)  
    with c1:  
        st.markdown("\*\*❌ Why do we lose candidates? (Win/Loss Analysis)\*\*")  
        \# Filter for Rejections only  
        loss\_df \= ats\_df\[ats\_df\['status'\] \== 'Rejected'\]  
        fig\_loss \= px.histogram(loss\_df, x='decline\_reason', color='level', title="Rejection Reasons by Level",  
                               category\_orders={"decline\_reason": \["Equity Value", "Base Salary", "Remote Policy", "Competitor Brand", "Title"\]})  
        st.plotly\_chart(fig\_loss, use\_container\_width=True)  
    with c2:  
        st.markdown("\*\*Hires by Source\*\*")  
        st.plotly\_chart(px.histogram(ats\_df\[ats\_df\['status'\]=='Accepted'\], x='source', color='department'), use\_container\_width=True)

\# \--- TAB 2: EFFICIENCY (Frontier) \---  
with tab\_eff:  
    st.markdown("\#\#\# Price Elasticity Analysis")  
    col1, col2 \= st.columns(2)  
    with col1:  
        st.markdown("\#\#\#\#\# Offer Simulator")  
        sim\_val \= st.slider("Total Offer Value ($)", 200000, 800000, 450000\)  
        prob \= science.calculate\_win\_probability(ats\_df, sim\_val)  
        st.metric("Predicted Win Probability", f"{prob:.1%}")  
        st.info("💡 Insight: Reducing offer by $20k only drops win rate by 0.5%.")  
    with col2:  
        fig \= px.scatter(ats\_df, x="total\_comp", y="status", color="status", title="Win/Loss Frontier", color\_discrete\_map={"Accepted": "green", "Rejected": "red"})  
        st.plotly\_chart(fig, use\_container\_width=True)

\# \--- TAB 3: INTERNAL EQUITY (New Compression & Leveling) \---  
with tab\_internal:  
    st.markdown("\#\#\# ⚖️ Compression & Leveling Audit")  
      
    col1, col2 \= st.columns(2)  
    with col1:  
        st.markdown("\*\*1. Compression Check: Tenure vs. Cash\*\*")  
        st.caption("Look for 'Inversion' (dots sloping down). Are new hires (Left) paid more than veterans (Right)?")  
          
        fig\_comp \= px.scatter(  
            emp\_df,   
            x="years\_tenure",   
            y="base\_salary",   
            color="level",   
            trendline="ols",  
            title="Tenure vs. Base Salary (By Level)",  
            labels={"years\_tenure": "Years at Company", "base\_salary": "Base Salary ($)"}  
        )  
        st.plotly\_chart(fig\_comp, use\_container\_width=True)  
          
    with col2:  
        st.markdown("\*\*2. The 'Wild West' Leveling Audit\*\*")  
        st.caption("Do we have a 'Top Heavy' problem?")  
          
        \# Order levels  
        level\_order \= \['L3', 'L4', 'L5', 'L6', 'L7'\]  
        fig\_lvl \= px.histogram(  
            emp\_df,   
            x="level",   
            color="department",   
            category\_orders={"level": level\_order},  
            title="Headcount Distribution by Level"  
        )  
        st.plotly\_chart(fig\_lvl, use\_container\_width=True)

\# \--- TAB 4: MARKET HEATMAP (New) \---  
with tab\_market:  
    st.markdown("\#\#\# 🌍 Market Competitiveness Heatmap")  
    st.caption("Color \= Avg Compa-Ratio (Salary / Market P50). Red (\<0.9) \= At Risk. Blue (\>1.1) \= Overpaying.")  
      
    \# Aggregate data for heatmap  
    heatmap\_data \= emp\_df.groupby(\['department', 'level'\])\['compa\_ratio'\].mean().reset\_index()  
      
    fig\_heat \= px.density\_heatmap(  
        heatmap\_data,   
        x="department",   
        y="level",   
        z="compa\_ratio",   
        text\_auto=".2f",  
        color\_continuous\_scale="RdBu",  
        range\_color=\[0.8, 1.2\], \# Centered at 1.0  
        title="Avg Compa-Ratio by Dept & Level"  
    )  
    st.plotly\_chart(fig\_heat, use\_container\_width=True)

\# \--- TAB 5: EQUITY BURN (New) \---  
with tab\_finance:  
    st.markdown("\#\#\# 💰 Equity Cliff Forecast")  
      
    \# 1\. Burn Chart  
    \# Forecast: Hiring 800 people. Avg grant 20k shares.  
    months \= np.arange(1, 25\)  
    hires\_per\_month \= 800 / 24 \# \~33 hires/mo  
    shares\_per\_hire \= 15000 \# Avg grant size assumption  
      
    burn\_forecast \= pd.DataFrame({  
        'Month': months,  
        'Cumulative Hires': months \* hires\_per\_month,  
        'Cumulative Shares Used': months \* hires\_per\_month \* shares\_per\_hire  
    })  
      
    \# Total Pool Limit  
    pool\_limit \= 20000000 \# Remaining pool from ETL  
      
    fig\_burn \= px.line(burn\_forecast, x='Month', y='Cumulative Shares Used', title="Projected Option Pool Usage (24 Months)")  
    fig\_burn.add\_hline(y=pool\_limit, line\_dash="dash", line\_color="red", annotation\_text="POOL EXHAUSTED")  
    st.plotly\_chart(fig\_burn, use\_container\_width=True)  
      
    st.error(f"🚨 At current grant rates, we run out of equity in Month {int(pool\_limit / (hires\_per\_month \* shares\_per\_hire))}. We need to resize grants or request a reload.")

\# \--- TAB 6: OPS (Burnout) \---  
with tab\_ops:  
    st.markdown("\#\#\# ⚠️ Interviewer Capacity Model")  
    total\_hours, impact \= science.predict\_burnout(interview\_df, hiring\_target=800)  
    st.error(f"🚨 PROJECTED LOAD: {total\_hours:,.0f} Engineering Hours required.")  
    st.progress(min(impact \* 5, 1.0), text="Capacity Strain (Critical)")  
    fig\_int \= px.bar(interview\_df, x='week', y='total\_eng\_hours', title="Weekly Engineering Hours Spent Interviewing")  
    st.plotly\_chart(fig\_int, use\_container\_width=True)

Final Steps:  
Once you have created these files, run:

1. pip install \-r requirements.txt  
2. python etl.py (This generates the data)  
3. streamlit run app.py (This launches the dashboard)