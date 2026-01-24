"""
Flask API Server for Diabetes Prediction
"""

from flask import Flask, request, jsonify, render_template, send_from_directory
import pickle
import pandas as pd
import numpy as np
import os
from sql_python_script import DiabetesDataProcessor

app = Flask(__name__)

# Tableau Embed config (set this to your published viz URL)
# Default: Your Tableau Public dashboard
# To override: Set TABLEAU_VIZ_URL environment variable
# IMPORTANT: Get the correct URL from Tableau Public:
# 1. Open your dashboard on Tableau Public
# 2. Click "Share" button
# 3. Copy the "Embed Code" or use the URL format: https://public.tableau.com/views/WORKBOOK/DASHBOARD?:showVizHome=no&:embed=true
DEFAULT_TABLEAU_URL = "https://public.tableau.com/views/Project-CDAC/Dashboard1?:showVizHome=no&:embed=true"
TABLEAU_VIZ_URL = os.environ.get("TABLEAU_VIZ_URL", DEFAULT_TABLEAU_URL)

# Initialize database processor (will create DB if it doesn't exist)
try:
    db_processor = DiabetesDataProcessor()
    db_processor.create_database_schema()
except Exception as e:
    print(f"Warning: Could not initialize database: {e}")
    db_processor = None

# Load model and features
MODEL_PATH = "diabetes_model.pkl"
FEATURES_PATH = "model_features.pkl"

try:
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    print(f"Model loaded successfully from {MODEL_PATH}")
except FileNotFoundError:
    print(f"Error: {MODEL_PATH} not found. Please run train_model.py first.")
    model = None

try:
    with open(FEATURES_PATH, "rb") as f:
        feature_names = pickle.load(f)
    print(f"Features loaded: {feature_names}")
except FileNotFoundError:
    print(f"Error: {FEATURES_PATH} not found.")
    feature_names = [
        "hba1c",
        "diagnosed_diabetes",
        "glucose_fasting",
        "glucose_postprandial",
        "family_history_diabetes",
        "diabetes_risk_score",
        "hypertension_history"
    ]

@app.route("/")
def index():
    """Serve the main UI page"""
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    """Serve the Tableau dashboard page"""
    with open("tableau_dashboard.html", "r", encoding="utf-8") as f:
        return f.read()

@app.route("/predict", methods=["POST"])
def predict():
    """API endpoint for diabetes prediction"""
    try:
        if model is None:
            return jsonify({"error": "Model not loaded. Please train the model first."}), 500
        
        # Get data from request
        data = request.get_json()
        
        # Extract features in correct order
        features = [
            float(data.get("hba1c", 0)),
            int(data.get("diagnosed_diabetes", 0)),
            float(data.get("glucose_fasting", 0)),
            float(data.get("glucose_postprandial", 0)),
            int(data.get("family_history_diabetes", 0)),
            float(data.get("diabetes_risk_score", 0)),
            int(data.get("hypertension_history", 0))
        ]
        
        # Create DataFrame
        input_data = pd.DataFrame([features], columns=feature_names)
        
        # Make prediction
        prediction = model.predict(input_data)[0]
        probabilities = model.predict_proba(input_data)[0]
        
        # Get class names
        classes = model.classes_
        prob_dict = {str(cls): float(prob) for cls, prob in zip(classes, probabilities)}
        
        # Get confidence (max probability)
        confidence = float(max(probabilities))
        
        # Save prediction to database
        if db_processor:
            try:
                db_processor.save_prediction(data, str(prediction), confidence)
                db_processor.update_analytics_summary()
                # Also keep tableau_export.csv in sync on every prediction
                db_processor.export_for_tableau()
                # Create refresh trigger file for Tableau Desktop
                try:
                    from tableau_refresh_helper import create_refresh_trigger_file
                    create_refresh_trigger_file()
                except Exception as e:
                    print(f"Warning: Could not create refresh trigger: {e}")
            except Exception as e:
                print(f"Warning: Could not save to database: {e}")
        
        return jsonify({
            "prediction": str(prediction),
            "probabilities": prob_dict,
            "confidence": confidence,
            "status": "success"
        })
    
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 400

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "model_loaded": model is not None
    })

@app.route("/api/statistics", methods=["GET"])
def get_statistics():
    """Get database statistics for dashboard"""
    if not db_processor:
        return jsonify({
            "total_patients": 0,
            "stage_distribution": {}
        })
    try:
        stats = db_processor.get_statistics()
        return jsonify(stats)
    except Exception as e:
        return jsonify({
            "error": str(e),
            "total_patients": 0,
            "stage_distribution": {}
        }), 500

@app.route("/api/export", methods=["GET"])
def export_data():
    """Export data for Tableau"""
    if not db_processor:
        return jsonify({"error": "Database not initialized"}), 500
    try:
        df = db_processor.export_for_tableau()
        return jsonify({
            "status": "success",
            "message": "Data exported to tableau_export.csv",
            "records": len(df)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tableau-config", methods=["GET"])
def tableau_config():
    """Get Tableau embed configuration for the dashboard page."""
    return jsonify({
        "viz_url": TABLEAU_VIZ_URL
    })

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

