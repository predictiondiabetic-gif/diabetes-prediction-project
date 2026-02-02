"""
ML Model Training Script
Trains Random Forest Classifier with SMOTE on 7 features
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from imblearn.over_sampling import SMOTE
import pickle
import os

# Load dataset
print("Loading dataset...")
df = pd.read_csv("diabetes_dataset (1).csv")

# Filter target classes
target_classes = ["No Diabetes", "Pre-Diabetes", "Type 2"]
df = df[df["diabetes_stage"].isin(target_classes)]

# Select only the 7 features required
features = [
    "hba1c",
    "diagnosed_diabetes",
    "glucose_fasting",
    "glucose_postprandial",
    "family_history_diabetes",
    "diabetes_risk_score",
    "hypertension_history"
]

# Prepare features and target
X = df[features].copy()
y = df["diabetes_stage"].copy()

# Handle missing values
X = X.fillna(X.median())

print(f"\nDataset shape: {X.shape}")
print(f"Target distribution:\n{y.value_counts()}")

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\nTraining set shape: {X_train.shape}")
print(f"Test set shape: {X_test.shape}")

# Apply SMOTE
print("\nApplying SMOTE...")
smote = SMOTE(random_state=42)
X_train_smote, y_train_smote = smote.fit_resample(X_train, y_train)

print("Before SMOTE:")
print(y_train.value_counts())
print("\nAfter SMOTE:")
print(pd.Series(y_train_smote).value_counts())

# Train Random Forest Model
print("\nTraining Random Forest Classifier...")
rf_model = RandomForestClassifier(
    n_estimators=300,
    max_depth=14,
    min_samples_split=10,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1
)

rf_model.fit(X_train_smote, y_train_smote)
print("Model trained successfully!")

# Evaluate model
y_pred = rf_model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print(f"\nTest Accuracy: {accuracy:.4f}")
print("\nConfusion Matrix:")
print(confusion_matrix(y_test, y_pred))
print("\nClassification Report:")
print(classification_report(y_test, y_pred))

# Save model
print("\nSaving model...")
with open("diabetes_model.pkl", "wb") as f:
    pickle.dump(rf_model, f)

# Save feature names for reference
with open("model_features.pkl", "wb") as f:
    pickle.dump(features, f)

print("Model saved as 'diabetes_model.pkl'")
print("Feature names saved as 'model_features.pkl'")
print("\nTraining completed!")

