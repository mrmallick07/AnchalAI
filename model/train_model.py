"""
AnchalAI — Model Training with Cross-Validation and Detailed Metrics

Trains a Random Forest classifier on RCH registration data to predict
dropout risk for pregnant women in antenatal care.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    classification_report, accuracy_score, roc_auc_score,
    precision_recall_fscore_support, confusion_matrix
)
import pickle
import os
import json

# ── Load Data ────────────────────────────────────────────────────────────────
df = pd.read_csv("data/women_profiles.csv")
print(f"Dataset: {len(df)} profiles, {df['dropout'].mean():.1%} dropout rate\n")

# ── Features and Target ─────────────────────────────────────────────────────
FEATURES = [
    "age", "distance_to_phc_km", "previous_pregnancies",
    "attended_last_visit", "household_income_level",
    "husband_support", "literacy", "trimester_at_registration",
    "harvest_season", "asha_visits_so_far"
]

X = df[FEATURES]
y = df["dropout"]

# ── Train / Test Split ───────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"Train: {len(X_train)} samples | Test: {len(X_test)} samples\n")

# ── Cross-Validation ─────────────────────────────────────────────────────────
model = RandomForestClassifier(
    n_estimators=200,
    max_depth=8,
    min_samples_split=5,
    min_samples_leaf=2,
    random_state=42,
    n_jobs=-1
)

cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring="roc_auc")
print(f"Cross-Validation AUC-ROC: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
print(f"  Fold scores: {[f'{s:.3f}' for s in cv_scores]}\n")

# ── Train Final Model ────────────────────────────────────────────────────────
model.fit(X_train, y_train)

# ── Evaluate ─────────────────────────────────────────────────────────────────
y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]

accuracy = accuracy_score(y_test, y_pred)
auc_roc = roc_auc_score(y_test, y_prob)
precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average="binary")

print(f"Test Accuracy:  {accuracy:.1%}")
print(f"Test AUC-ROC:   {auc_roc:.3f}")
print(f"Precision:      {precision:.3f}")
print(f"Recall:         {recall:.3f}")
print(f"F1 Score:       {f1:.3f}\n")

print("Classification Report:")
print(classification_report(y_test, y_pred, target_names=["No Dropout", "Dropout"]))

cm = confusion_matrix(y_test, y_pred)
print(f"Confusion Matrix:")
print(f"  TN={cm[0][0]}  FP={cm[0][1]}")
print(f"  FN={cm[1][0]}  TP={cm[1][1]}\n")

# ── Feature Importance ───────────────────────────────────────────────────────
importance = pd.DataFrame({
    "feature": FEATURES,
    "importance": model.feature_importances_
}).sort_values("importance", ascending=False)

print("Feature Importance (Top Risk Factors):")
for _, row in importance.iterrows():
    bar = "█" * int(row["importance"] * 50)
    print(f"  {row['feature']:30s} {row['importance']:.4f}  {bar}")

# ── Save Model ───────────────────────────────────────────────────────────────
os.makedirs("model", exist_ok=True)
with open("model/anchal_model.pkl", "wb") as f:
    pickle.dump(model, f)

# ── Save Model Metrics (for analytics endpoint) ─────────────────────────────
metrics = {
    "accuracy": round(accuracy, 4),
    "auc_roc": round(auc_roc, 4),
    "precision": round(precision, 4),
    "recall": round(recall, 4),
    "f1_score": round(f1, 4),
    "cv_auc_mean": round(cv_scores.mean(), 4),
    "cv_auc_std": round(cv_scores.std(), 4),
    "feature_importance": importance.set_index("feature")["importance"].round(4).to_dict(),
    "n_train": len(X_train),
    "n_test": len(X_test),
    "n_features": len(FEATURES),
    "model_type": "RandomForestClassifier",
    "n_estimators": 200,
    "max_depth": 8,
}

with open("model/model_metrics.json", "w") as f:
    json.dump(metrics, f, indent=2)

print(f"\n✅ Model saved: model/anchal_model.pkl")
print(f"✅ Metrics saved: model/model_metrics.json")
