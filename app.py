from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import pickle
import os
from dotenv import load_dotenv
from api.gemini_message import generate_asha_message

load_dotenv()

app = Flask(__name__)
CORS(app)

# Load trained model
with open("model/anchal_model.pkl", "rb") as f:
    model = pickle.load(f)

FEATURES = [
    "age", "distance_to_phc_km", "previous_pregnancies",
    "attended_last_visit", "household_income_level",
    "husband_support", "literacy", "trimester_at_registration",
    "harvest_season", "asha_visits_so_far"
]

@app.route("/")
def home():
    return jsonify({"status": "AnchalAI is running"})


@app.route("/predict", methods=["POST"])
def predict():
    """
    Takes a woman's profile, returns risk score + Gemini message.
    """
    try:
        data = request.json
        profile = {f: data[f] for f in FEATURES}

        # Predict dropout probability
        df = pd.DataFrame([profile])
        risk_prob = model.predict_proba(df)[0][1]
        risk_percent = round(risk_prob * 100, 1)
        risk_label = (
            "High" if risk_percent > 60
            else "Medium" if risk_percent > 35
            else "Low"
        )

        # Generate Gemini message
        profile["risk_percent"] = risk_percent
        language = data.get("language", "Bengali")
        message = generate_asha_message(profile, language=language)

        return jsonify({
            "risk_percent": risk_percent,
            "risk_label": risk_label,
            "message": message,
            "top_factors": get_top_factors(profile)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400


def get_top_factors(profile):
    """Returns human-readable top risk factors for this profile."""
    factors = []
    if profile["distance_to_phc_km"] > 15:
        factors.append(f"Lives {profile['distance_to_phc_km']}km from PHC")
    if profile["attended_last_visit"] == 0:
        factors.append("Missed last scheduled visit")
    if profile["age"] < 20:
        factors.append(f"Teenage pregnancy (age {profile['age']})")
    if profile["husband_support"] == 0:
        factors.append("Limited husband support")
    if profile["trimester_at_registration"] == 3:
        factors.append("Registered late in third trimester")
    if profile["harvest_season"] == 1:
        factors.append("Currently harvest season")
    return factors


@app.route("/dashboard", methods=["GET"])
def dashboard():
    """
    Returns all women profiles with risk scores — sorted highest risk first.
    This powers the ASHA worker's main view.
    """
    df = pd.read_csv("data/women_profiles.csv")
    profiles = df[FEATURES].copy()
    
    probabilities = model.predict_proba(profiles)[:, 1]
    df["risk_percent"] = (probabilities * 100).round(1)
    df["risk_label"] = df["risk_percent"].apply(
        lambda x: "High" if x > 60 else "Medium" if x > 35 else "Low"
    )

    # Sort highest risk first
    df = df.sort_values("risk_percent", ascending=False)
    
    # Return top 20 for dashboard
    result = df.head(20)[[
        "id", "age", "distance_to_phc_km",
        "attended_last_visit", "risk_percent", "risk_label"
    ]].to_dict(orient="records")

    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False, port=8080)
