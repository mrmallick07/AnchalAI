import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import pickle
import os

# Load data
df = pd.read_csv("data/women_profiles.csv")

# Features and target
features = [
    "age", "distance_to_phc_km", "previous_pregnancies",
    "attended_last_visit", "household_income_level",
    "husband_support", "literacy", "trimester_at_registration",
    "harvest_season", "asha_visits_so_far"
]

X = df[features]
y = df["dropout"]

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Train
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=6,
    random_state=42
)
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
print(f"Accuracy: {accuracy_score(y_test, y_pred):.1%}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred))

# Feature importance — this tells us WHICH factors matter most
print("\nTop Risk Factors:")
importance = pd.DataFrame({
    "feature": features,
    "importance": model.feature_importances_
}).sort_values("importance", ascending=False)
print(importance)

# Save model
os.makedirs("model", exist_ok=True)
with open("model/anchal_model.pkl", "wb") as f:
    pickle.dump(model, f)

print("\nModel saved to model/anchal_model.pkl")
