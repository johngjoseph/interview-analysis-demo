import pandas as pd
import numpy as np
from models import CompData
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import PromptTemplate
import os
import json

class AnalysisEngine:
    
    @staticmethod
    def get_market_position(target_company="Cursor"):
        query = CompData.query.all()
        if not query: return {}
        
        data = [row.to_dict() for row in query]
        df = pd.DataFrame(data)
        if df.empty: return {}

        summary = df.groupby('company').agg({
            'avg': 'mean', 'min': 'min', 'max': 'max'
        }).reset_index()

        return {
            "summary_table": summary.to_dict('records'),
            "total_records": len(df)
        }

    @staticmethod
    def run_capacity_model(team_size=5):
        weekly_hours = team_size * 40 * 0.85
        np.random.seed(42)
        demand = np.random.normal(loc=weekly_hours, scale=30, size=12).astype(int).tolist()
        return {"weekly_capacity": int(weekly_hours), "projected_demand": demand}

    @staticmethod
    def parse_job_description_with_ai(text_content):
        # Validate API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("ERROR: OPENAI_API_KEY not set")
            return {"job_title": "", "company": "", "min": 0, "max": 0}
        
        try:
            llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", openai_api_key=api_key)
            
            prompt = PromptTemplate.from_template(
                """
                Extract Base Salary Range, Job Title, and Company Name.
                Ignore equity/benefits. Convert "150k" to 150000.
                If no salary found, return 0.
                
                Return JSON:
                {{
                    "job_title": "String",
                    "company": "String",
                    "min": Number,
                    "max": Number
                }}

                Text: {text}
                """
            )
            chain = prompt | llm
            result = chain.invoke({"text": text_content})
            
            # Parse JSON with error handling
            try:
                parsed = json.loads(result.content)
                
                # Validate extracted data structure
                if not isinstance(parsed, dict):
                    print(f"ERROR: LLM returned non-dict: {type(parsed)}")
                    return {"job_title": "", "company": "", "min": 0, "max": 0}
                
                # Ensure required keys exist
                required_keys = ["job_title", "company", "min", "max"]
                for key in required_keys:
                    if key not in parsed:
                        print(f"ERROR: Missing key '{key}' in extracted data")
                        parsed[key] = "" if key in ["job_title", "company"] else 0
                
                return parsed
            except json.JSONDecodeError as e:
                print(f"ERROR: JSON parsing failed in parse_job_description_with_ai: {e}")
                print(f"Content received: {result.content[:200] if hasattr(result, 'content') else 'No content'}")
                return {"job_title": "", "company": "", "min": 0, "max": 0}
        except KeyError as e:
            print(f"ERROR: KeyError in parse_job_description_with_ai: {e}")
            return {"job_title": "", "company": "", "min": 0, "max": 0}
        except ValueError as e:
            print(f"ERROR: ValueError in parse_job_description_with_ai: {e}")
            return {"job_title": "", "company": "", "min": 0, "max": 0}
        except AttributeError as e:
            print(f"ERROR: AttributeError in parse_job_description_with_ai: {e}")
            return {"job_title": "", "company": "", "min": 0, "max": 0}
        except Exception as e:
            print(f"ERROR: Unexpected error in parse_job_description_with_ai: {type(e).__name__}: {e}")
            return {"job_title": "", "company": "", "min": 0, "max": 0}