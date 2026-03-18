"""
AnchalAI — Flask Backend API

Endpoints:
  GET  /               — health check
  GET  /dashboard      — all women profiles with risk scores
  POST /predict        — predict risk for a single profile + Gemini message
  POST /contact        — log an outreach contact
  GET  /contacts       — get outreach history
  GET  /analytics      — aggregate analytics data
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import pickle
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from api.gemini_message import generate_asha_message

load_dotenv()

app = Flask(__name__)
CORS(app, origins=[
    "https://mrmallick07.github.io",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "null",
])

# ── Load trained model ───────────────────────────────────────────────────────
with open("model/anchal_model.pkl", "rb") as f:
    model = pickle.load(f)

# ── Load model metrics ───────────────────────────────────────────────────────
METRICS_PATH = "model/model_metrics.json"
model_metrics = {}
if os.path.exists(METRICS_PATH):
    with open(METRICS_PATH) as f:
        model_metrics = json.load(f)

FEATURES = [
    "age", "distance_to_phc_km", "previous_pregnancies",
    "attended_last_visit", "household_income_level",
    "husband_support", "literacy", "trimester_at_registration",
    "harvest_season", "asha_visits_so_far"
]

# ── Contact log storage ──────────────────────────────────────────────────────
CONTACTS_FILE = "data/contacts.json"


def load_contacts():
    if os.path.exists(CONTACTS_FILE):
        with open(CONTACTS_FILE) as f:
            return json.load(f)
    return []


def save_contacts(contacts):
    with open(CONTACTS_FILE, "w") as f:
        json.dump(contacts, f, indent=2, ensure_ascii=False)


def get_top_factors(profile):
    """Returns human-readable risk factors for a profile."""
    factors = []
    if profile.get("distance_to_phc_km", 0) > 15:
        factors.append(f"Lives {profile['distance_to_phc_km']}km from PHC")
    if profile.get("attended_last_visit") == 0:
        factors.append("Missed last scheduled visit")
    if profile.get("age", 25) < 20:
        factors.append(f"Teenage pregnancy (age {profile['age']})")
    if profile.get("age", 25) > 35:
        factors.append(f"Advanced maternal age ({profile['age']})")
    if profile.get("husband_support") == 0:
        factors.append("Limited husband support")
    if profile.get("trimester_at_registration") == 3:
        factors.append("Registered late in third trimester")
    if profile.get("harvest_season") == 1:
        factors.append("Currently harvest season")
    if profile.get("literacy") == 0:
        factors.append("Limited literacy")
    if profile.get("household_income_level") == 1:
        factors.append("Low household income")
    if profile.get("asha_visits_so_far", 5) < 2:
        factors.append("Very few ASHA visits so far")
    if profile.get("previous_pregnancies", 1) == 0:
        factors.append("First pregnancy")
    return factors


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def home():
    return jsonify({"status": "AnchalAI is running", "version": "2.0"})


@app.route("/dashboard", methods=["GET"])
def dashboard():
    """
    Returns all women profiles with risk scores, names, villages, etc.
    Sorted by highest risk first.
    """
    df = pd.read_csv("data/women_profiles.csv")
    profiles = df[FEATURES].copy()

    probabilities = model.predict_proba(profiles)[:, 1]
    df["risk_percent"] = (probabilities * 100).round(1)
    df["risk_label"] = df["risk_percent"].apply(
        lambda x: "High" if x > 60 else "Medium" if x > 35 else "Low"
    )

    # Add top factors for each woman
    records = []
    for _, row in df.iterrows():
        profile_dict = row[FEATURES].to_dict()
        factors = get_top_factors(profile_dict)
        record = {
            "id": int(row["id"]),
            "name": row["name"],
            "village": row["village"],
            "phone": row.get("phone", ""),
            "age": int(row["age"]),
            "blood_group": row.get("blood_group", ""),
            "distance_to_phc_km": float(row["distance_to_phc_km"]),
            "previous_pregnancies": int(row["previous_pregnancies"]),
            "attended_last_visit": int(row["attended_last_visit"]),
            "household_income_level": int(row["household_income_level"]),
            "husband_support": int(row["husband_support"]),
            "literacy": int(row["literacy"]),
            "trimester_at_registration": int(row["trimester_at_registration"]),
            "harvest_season": int(row["harvest_season"]),
            "asha_visits_so_far": int(row["asha_visits_so_far"]),
            "registration_date": row.get("registration_date", ""),
            "last_visit_date": row.get("last_visit_date", ""),
            "edd": row.get("edd", ""),
            "asha_worker_name": row.get("asha_worker_name", ""),
            "risk_percent": float(row["risk_percent"]),
            "risk_label": row["risk_label"],
            "top_factors": factors,
        }
        records.append(record)

    # Sort by risk_percent descending
    records.sort(key=lambda x: x["risk_percent"], reverse=True)
    return jsonify(records)


@app.route("/predict", methods=["POST"])
def predict():
    """
    Takes a woman's profile, returns risk score + Gemini message + escalation.
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

        # Get risk factors
        profile["risk_percent"] = risk_percent
        top_factors = get_top_factors(profile)

        # Generate Gemini message
        language = data.get("language", "Bengali")
        try:
            message = generate_asha_message(profile, language=language)
        except Exception as e:
            print(f"[PREDICT] Gemini message failed: {e}")
            message = "Message generation temporarily unavailable. Please contact this patient directly."

        # Determine escalation action
        if risk_percent > 60:
            escalation = {
                "action": "Immediate PHC alert + home visit within 48 hours",
                "urgency": "critical",
                "icon": "🚨"
            }
        elif risk_percent > 35:
            escalation = {
                "action": "ASHA home visit within 7 days",
                "urgency": "moderate",
                "icon": "⚠️"
            }
        else:
            escalation = {
                "action": "Schedule routine follow-up in 14 days",
                "urgency": "low",
                "icon": "📋"
            }

        return jsonify({
            "risk_percent": risk_percent,
            "risk_label": risk_label,
            "message": message,
            "top_factors": top_factors,
            "escalation": escalation,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/contact", methods=["POST"])
def log_contact():
    """
    Log an outreach contact.
    Body: { patient_id, patient_name, language, message, risk_percent, risk_label }
    """
    try:
        data = request.json
        contacts = load_contacts()

        contact = {
            "id": len(contacts) + 1,
            "patient_id": data.get("patient_id"),
            "patient_name": data.get("patient_name", "Unknown"),
            "village": data.get("village", ""),
            "language": data.get("language", "Bengali"),
            "message": data.get("message", ""),
            "risk_percent": data.get("risk_percent", 0),
            "risk_label": data.get("risk_label", "Unknown"),
            "timestamp": datetime.now().isoformat(),
            "follow_up_status": "pending",
        }
        contacts.append(contact)
        save_contacts(contacts)

        return jsonify({"status": "ok", "contact_id": contact["id"]})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/contacts", methods=["GET"])
def get_contacts():
    """Returns all outreach contact history, most recent first."""
    contacts = load_contacts()
    contacts.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return jsonify(contacts)


@app.route("/analytics", methods=["GET"])
def analytics():
    """
    Returns aggregate analytics: risk distribution, village stats,
    outreach progress, and model metrics.
    """
    df = pd.read_csv("data/women_profiles.csv")
    profiles = df[FEATURES].copy()

    probabilities = model.predict_proba(profiles)[:, 1]
    df["risk_percent"] = (probabilities * 100).round(1)
    df["risk_label"] = df["risk_percent"].apply(
        lambda x: "High" if x > 60 else "Medium" if x > 35 else "Low"
    )

    # Risk distribution
    risk_dist = df["risk_label"].value_counts().to_dict()

    # Village statistics
    village_stats = (
        df.groupby("village")
        .agg(
            count=("id", "count"),
            avg_risk=("risk_percent", "mean"),
            high_risk_count=("risk_label", lambda x: (x == "High").sum()),
        )
        .round(1)
        .sort_values("avg_risk", ascending=False)
        .head(15)
    )
    village_data = []
    for village, row in village_stats.iterrows():
        village_data.append({
            "village": village,
            "count": int(row["count"]),
            "avg_risk": float(row["avg_risk"]),
            "high_risk_count": int(row["high_risk_count"]),
        })

    # Outreach contacts summary
    contacts = load_contacts()
    total_contacts = len(contacts)
    contacts_this_week = sum(
        1 for c in contacts
        if c.get("timestamp", "")[:10] >= (datetime.now().isoformat()[:10])
    )

    # Overall stats
    total_women = len(df)
    avg_risk = round(df["risk_percent"].mean(), 1)
    highest_risk = df.loc[df["risk_percent"].idxmax()]

    result = {
        "total_women": total_women,
        "risk_distribution": {
            "High": risk_dist.get("High", 0),
            "Medium": risk_dist.get("Medium", 0),
            "Low": risk_dist.get("Low", 0),
        },
        "avg_risk_percent": avg_risk,
        "highest_risk_patient": {
            "name": highest_risk.get("name", "Unknown"),
            "village": highest_risk.get("village", ""),
            "risk_percent": float(highest_risk["risk_percent"]),
        },
        "village_stats": village_data,
        "outreach": {
            "total_contacts": total_contacts,
            "contacts_today": contacts_this_week,
            "pending_follow_ups": sum(
                1 for c in contacts if c.get("follow_up_status") == "pending"
            ),
        },
        "model_metrics": model_metrics,
    }

    return jsonify(result)


@app.route("/chat", methods=["POST"])
def chat():
    """
    Gemini Chat Assistant — "Anchal Sahayak"
    Body: { message, patient_id? (optional), language? (default: Hindi) }
    Returns: { reply }
    """
    try:
        import google.generativeai as genai

        data = request.json
        user_message = data.get("message", "")
        language = data.get("language", "Hindi")
        patient_id = data.get("patient_id")

        # Build patient context if a patient is selected
        patient_context = ""
        if patient_id:
            df = pd.read_csv("data/women_profiles.csv")
            patient = df[df["id"] == int(patient_id)]
            if not patient.empty:
                p = patient.iloc[0]
                profiles_df = pd.DataFrame([{f: p[f] for f in FEATURES}])
                risk_prob = model.predict_proba(profiles_df)[0][1]
                risk_pct = round(risk_prob * 100, 1)
                patient_context = f"""
CURRENT PATIENT CONTEXT:
- Name: {p.get('name', 'Unknown')}
- Age: {p['age']} years
- Village: {p.get('village', 'Unknown')}
- Distance to PHC: {p['distance_to_phc_km']} km
- Previous pregnancies: {p['previous_pregnancies']}
- Last visit attended: {'Yes' if p['attended_last_visit'] == 1 else 'No'}
- Husband support: {'Yes' if p['husband_support'] == 1 else 'No'}
- Literacy: {'Literate' if p['literacy'] == 1 else 'Limited literacy'}
- Trimester at registration: {p['trimester_at_registration']}
- Dropout risk: {risk_pct}% ({'High' if risk_pct > 60 else 'Medium' if risk_pct > 35 else 'Low'})
"""

        system_prompt = f"""You are "Anchal Sahayak" (आंचल सहायक), an AI assistant for ASHA (Accredited Social Health Activist) workers in rural India.

Your role:
- Help ASHA workers understand patient risk factors and what they mean
- Suggest what to say during home visits
- Explain medical terms in simple, culturally appropriate language
- Provide guidance on when to escalate to PHC (Primary Health Centre)
- Generate motivational messages for pregnant women

Rules:
1. Reply in {language} (use the script of that language)
2. Keep responses concise — ASHA workers are busy field workers
3. Be warm, supportive, and practical
4. If asked about a specific patient (context provided below), use that data
5. Never diagnose — always recommend visiting PHC for medical concerns
6. Focus on antenatal care dropout prevention
{patient_context}
"""

        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        gemini_model = genai.GenerativeModel("gemini-2.0-flash")
        response = gemini_model.generate_content(
            [system_prompt, user_message],
            generation_config=genai.GenerationConfig(
                max_output_tokens=500,
                temperature=0.7,
            )
        )

        reply = response.text.strip()
        return jsonify({"reply": reply})

    except Exception as e:
        print(f"[CHAT] Error: {e}")
        return jsonify({
            "reply": "मुझसे बात करने के लिए धन्यवाद। अभी कोई तकनीकी समस्या है। कृपया कुछ देर बाद पुनः प्रयास करें। (Thank you for chatting. There is a technical issue. Please try again later.)"
        }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False, port=8080)
