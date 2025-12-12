"""
Manager for storing and loading insights/narratives for each tab.
Saves to JSON file for persistence across app restarts.
"""
import json
from pathlib import Path

INSIGHTS_FILE = Path(__file__).parent / 'data' / 'insights.json'

def load_insights():
    """Load insights from JSON file"""
    if INSIGHTS_FILE.exists():
        try:
            with open(INSIGHTS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading insights: {e}")
            return {}
    return {}

def save_insights(insights_dict):
    """Save insights to JSON file"""
    try:
        # Ensure data directory exists
        INSIGHTS_FILE.parent.mkdir(exist_ok=True)
        
        with open(INSIGHTS_FILE, 'w') as f:
            json.dump(insights_dict, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving insights: {e}")
        return False

def get_insight(tab_name, insights_dict):
    """Get insight for a specific tab"""
    return insights_dict.get(tab_name, "")

def set_insight(tab_name, insight_text, insights_dict):
    """Set insight for a specific tab"""
    insights_dict[tab_name] = insight_text
    return insights_dict

