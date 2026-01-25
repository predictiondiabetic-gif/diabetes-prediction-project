"""
SQL-Python End-to-End Data Processing Script
Handles data extraction, transformation, and loading
"""

import pandas as pd
import numpy as np
import sqlite3
from sqlalchemy import create_engine
import os
from datetime import datetime

class DiabetesDataProcessor:
    def __init__(self, db_path="diabetes_database.db"):
        """Initialize database connection"""
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        # Allow use across Flask threads
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        
    def create_database_schema(self):
        """Create database tables"""
        cursor = self.conn.cursor()
        
        # Create patients table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
                hba1c REAL,
                diagnosed_diabetes INTEGER,
                glucose_fasting REAL,
                glucose_postprandial REAL,
                family_history_diabetes INTEGER,
                diabetes_risk_score REAL,
                hypertension_history INTEGER,
                predicted_stage TEXT,
                prediction_confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create predictions_history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions_history (
                prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER,
                hba1c REAL,
                diagnosed_diabetes INTEGER,
                glucose_fasting REAL,
                glucose_postprandial REAL,
                family_history_diabetes INTEGER,
                diabetes_risk_score REAL,
                hypertension_history INTEGER,
                predicted_stage TEXT,
                prediction_confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
            )
        """)
        
        # Create analytics_summary table for Tableau
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analytics_summary (
                summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE,
                total_predictions INTEGER,
                type2_count INTEGER,
                prediabetes_count INTEGER,
                no_diabetes_count INTEGER,
                avg_hba1c REAL,
                avg_glucose_fasting REAL,
                avg_glucose_postprandial REAL,
                avg_risk_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.commit()
        print("Database schema created successfully!")
    
    def load_csv_to_database(self, csv_path="diabetes_dataset (1).csv"):
        """Load CSV data into database"""
        print(f"Loading data from {csv_path}...")
        df = pd.read_csv(csv_path)
        
        # Filter target classes
        target_classes = ["No Diabetes", "Pre-Diabetes", "Type 2"]
        df = df[df["diabetes_stage"].isin(target_classes)]
        
        # Select required features
        features = [
            "hba1c",
            "diagnosed_diabetes",
            "glucose_fasting",
            "glucose_postprandial",
            "family_history_diabetes",
            "diabetes_risk_score",
            "hypertension_history",
            "diabetes_stage"
        ]
        
        df_processed = df[features].copy()
        
        # Handle missing values
        df_processed = df_processed.fillna(df_processed.median())
        
        # Rename diabetes_stage to predicted_stage for database
        df_processed.rename(columns={"diabetes_stage": "predicted_stage"}, inplace=True)
        df_processed["prediction_confidence"] = 1.0  # Actual data, so confidence is 1.0
        df_processed["created_at"] = datetime.now()
        
        # Insert into database
        df_processed.to_sql('patients', self.engine, if_exists='append', index=False)
        print(f"Loaded {len(df_processed)} records into database")
        
        return df_processed
    
    def save_prediction(self, features_dict, prediction, confidence):
        """Save a new prediction to database"""
        cursor = self.conn.cursor()
        
        # Insert into patients table
        cursor.execute("""
            INSERT INTO patients (
                hba1c, diagnosed_diabetes, glucose_fasting, glucose_postprandial,
                family_history_diabetes, diabetes_risk_score, hypertension_history,
                predicted_stage, prediction_confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            features_dict['hba1c'],
            features_dict['diagnosed_diabetes'],
            features_dict['glucose_fasting'],
            features_dict['glucose_postprandial'],
            features_dict['family_history_diabetes'],
            features_dict['diabetes_risk_score'],
            features_dict['hypertension_history'],
            prediction,
            confidence
        ))
        
        patient_id = cursor.lastrowid
        
        # Also insert into predictions_history
        cursor.execute("""
            INSERT INTO predictions_history (
                patient_id, hba1c, diagnosed_diabetes, glucose_fasting, glucose_postprandial,
                family_history_diabetes, diabetes_risk_score, hypertension_history,
                predicted_stage, prediction_confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            patient_id,
            features_dict['hba1c'],
            features_dict['diagnosed_diabetes'],
            features_dict['glucose_fasting'],
            features_dict['glucose_postprandial'],
            features_dict['family_history_diabetes'],
            features_dict['diabetes_risk_score'],
            features_dict['hypertension_history'],
            prediction,
            confidence
        ))
        
        self.conn.commit()
        print(f"Prediction saved with patient_id: {patient_id}")
        return patient_id
    
    def update_analytics_summary(self):
        """Update analytics summary table for Tableau dashboard"""
        cursor = self.conn.cursor()
        
        # Get today's date
        today = datetime.now().date()
        
        # Calculate summary statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN predicted_stage = 'Type 2' THEN 1 ELSE 0 END) as type2,
                SUM(CASE WHEN predicted_stage = 'Pre-Diabetes' THEN 1 ELSE 0 END) as prediabetes,
                SUM(CASE WHEN predicted_stage = 'No Diabetes' THEN 1 ELSE 0 END) as no_diabetes,
                AVG(hba1c) as avg_hba1c,
                AVG(glucose_fasting) as avg_glucose_fasting,
                AVG(glucose_postprandial) as avg_glucose_postprandial,
                AVG(diabetes_risk_score) as avg_risk_score
            FROM patients
            WHERE DATE(created_at) = ?
        """, (today,))
        
        result = cursor.fetchone()
        
        if result and result[0] > 0:
            cursor.execute("""
                INSERT OR REPLACE INTO analytics_summary (
                    date, total_predictions, type2_count, prediabetes_count, no_diabetes_count,
                    avg_hba1c, avg_glucose_fasting, avg_glucose_postprandial, avg_risk_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (today, *result))
            self.conn.commit()
            print("Analytics summary updated!")
    
    def export_for_tableau(self, output_path="tableau_export.csv"):
        """Export data for Tableau dashboard"""
        query = """
            SELECT 
                p.*,
                ph.created_at as prediction_date,
                CASE 
                    WHEN p.predicted_stage = 'Type 2' THEN 1 ELSE 0 
                END as is_type2,
                CASE 
                    WHEN p.predicted_stage = 'Pre-Diabetes' THEN 1 ELSE 0 
                END as is_prediabetes,
                CASE 
                    WHEN p.predicted_stage = 'No Diabetes' THEN 1 ELSE 0 
                END as is_no_diabetes
            FROM patients p
            LEFT JOIN predictions_history ph ON p.patient_id = ph.patient_id
            ORDER BY p.created_at DESC
        """
        
        df = pd.read_sql_query(query, self.conn)
        df.to_csv(output_path, index=False)
        print(f"Data exported to {output_path} for Tableau")
        return df
    
    def get_statistics(self):
        """Get database statistics"""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM patients")
        total_patients = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT predicted_stage, COUNT(*) 
            FROM patients 
            GROUP BY predicted_stage
        """)
        stage_counts = dict(cursor.fetchall())
        
        print(f"\nDatabase Statistics:")
        print(f"Total Patients: {total_patients}")
        print(f"Stage Distribution: {stage_counts}")
        
        return {
            "total_patients": total_patients,
            "stage_distribution": stage_counts
        }
    
    def close(self):
        """Close database connection"""
        self.conn.close()
        print("Database connection closed")

def main():
    """Main execution function"""
    print("=" * 50)
    print("Diabetes Data Processing - End to End")
    print("=" * 50)
    
    # Initialize processor
    processor = DiabetesDataProcessor()
    
    # Create schema
    processor.create_database_schema()
    
    # Load CSV data (optional - uncomment if you want to load initial data)
    # processor.load_csv_to_database()
    
    # Export for Tableau
    processor.export_for_tableau()
    
    # Get statistics
    processor.get_statistics()
    
    # Close connection
    processor.close()
    
    print("\nProcessing completed successfully!")

if __name__ == "__main__":
    main()

