"""
Helper script to notify Tableau Desktop about data updates
This can be used to trigger refresh in Tableau Desktop
"""

import sqlite3
import os
import time
from datetime import datetime

def get_latest_prediction_time():
    """Get the timestamp of the most recent prediction"""
    try:
        conn = sqlite3.connect('diabetes_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(created_at) FROM patients")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result[0] else None
    except Exception as e:
        print(f"Error getting latest prediction time: {e}")
        return None

def create_refresh_trigger_file():
    """Create a trigger file that Tableau can watch for changes"""
    try:
        # Create a simple text file with current timestamp
        # Tableau can be set to refresh when this file changes
        with open('tableau_refresh_trigger.txt', 'w') as f:
            f.write(f"Last updated: {datetime.now().isoformat()}\n")
            f.write(f"Latest prediction: {get_latest_prediction_time()}\n")
        print("Refresh trigger file updated")
        return True
    except Exception as e:
        print(f"Error creating trigger file: {e}")
        return False

if __name__ == "__main__":
    create_refresh_trigger_file()

