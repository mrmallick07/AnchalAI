"""
AnchalAI Multi-Agent System using Google ADK.

Architecture:
  OrchestratorAgent (SequentialAgent)
    ├── RiskAnalystAgent   — predicts dropout risk using ML model
    ├── CommunicationAgent — generates culturally appropriate outreach message
    └── EscalationAgent    — decides escalation action based on risk level
"""

import os
import json
import pickle
import pandas as pd
from dotenv import load_dotenv
from google.adk.agents import Agent, SequentialAgent

# ---------------------------------------------------------------------------
# Load environment variables and configure API key for ADK
# ---------------------------------------------------------------------------
load_dotenv()

# ADK reads GOOGLE_GENAI_API_KEY automatically; map from our .env's GEMINI_API_KEY
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    os.environ["GOOGLE_GENAI_API_KEY"] = api_key

# ---------------------------------------------------------------------------
# Load the trained model once at module level
# ---------------------------------------------------------------------------
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "model", "anchal_model.pkl")
with open(MODEL_PATH, "rb") as f:
    _model = pickle.load(f)

FEATURES = [
    "age", "distance_to_phc_km", "previous_pregnancies",
    "attended_last_visit", "household_income_level",
    "husband_support", "literacy", "trimester_at_registration",
    "harvest_season", "asha_visits_so_far",
]


# ---------------------------------------------------------------------------
# Tool function for Risk Analyst Agent
# ---------------------------------------------------------------------------
def predict_dropout_risk(
    age: int,
    distance_to_phc_km: float,
    previous_pregnancies: int,
    attended_last_visit: int,
    household_income_level: int,
    husband_support: int,
    literacy: int,
    trimester_at_registration: int,
    harvest_season: int,
    asha_visits_so_far: int,
) -> dict:
    """Predict the dropout risk for a pregnant woman given her profile features.

    Args:
        age: Age of the woman in years.
        distance_to_phc_km: Distance to the nearest Primary Health Centre in km.
        previous_pregnancies: Number of previous pregnancies.
        attended_last_visit: 1 if she attended her last scheduled visit, 0 otherwise.
        household_income_level: Household income level (1=low, 2=medium, 3=high).
        husband_support: 1 if husband is supportive, 0 otherwise.
        literacy: 1 if literate, 0 otherwise.
        trimester_at_registration: Trimester at which she registered (1, 2, or 3).
        harvest_season: 1 if it is currently harvest season, 0 otherwise.
        asha_visits_so_far: Number of ASHA worker visits so far.

    Returns:
        dict: A dictionary containing risk_percent, risk_label, and top_factors.
    """
    profile = {
        "age": age,
        "distance_to_phc_km": distance_to_phc_km,
        "previous_pregnancies": previous_pregnancies,
        "attended_last_visit": attended_last_visit,
        "household_income_level": household_income_level,
        "husband_support": husband_support,
        "literacy": literacy,
        "trimester_at_registration": trimester_at_registration,
        "harvest_season": harvest_season,
        "asha_visits_so_far": asha_visits_so_far,
    }

    df = pd.DataFrame([profile])
    risk_prob = _model.predict_proba(df)[0][1]
    risk_percent = round(risk_prob * 100, 1)
    risk_label = (
        "High" if risk_percent > 60
        else "Medium" if risk_percent > 35
        else "Low"
    )

    # Determine top risk factors
    factors = []
    if distance_to_phc_km > 15:
        factors.append(f"Lives {distance_to_phc_km}km from PHC")
    if attended_last_visit == 0:
        factors.append("Missed last scheduled visit")
    if age < 20:
        factors.append(f"Teenage pregnancy (age {age})")
    if husband_support == 0:
        factors.append("Limited husband support")
    if trimester_at_registration == 3:
        factors.append("Registered late in third trimester")
    if harvest_season == 1:
        factors.append("Currently harvest season")
    if literacy == 0:
        factors.append("Limited literacy")
    if household_income_level == 1:
        factors.append("Low household income")

    return {
        "risk_percent": risk_percent,
        "risk_label": risk_label,
        "top_factors": factors,
    }


# ---------------------------------------------------------------------------
# 1. Risk Analyst Agent
# ---------------------------------------------------------------------------
risk_analyst_agent = Agent(
    name="risk_analyst_agent",
    model="gemini-1.5-flash",
    description="Predicts maternal dropout risk from a woman's profile using a trained ML model.",
    instruction="""You are the Risk Analyst Agent for AnchalAI.

Your job is to assess the dropout risk of a pregnant woman.

When you receive a woman's profile, call the predict_dropout_risk tool with ALL of
the following fields extracted from the profile:
  age, distance_to_phc_km, previous_pregnancies, attended_last_visit,
  household_income_level, husband_support, literacy, trimester_at_registration,
  harvest_season, asha_visits_so_far

After receiving the tool result, respond with ONLY a JSON object in this exact format:
{
  "risk_percent": <number>,
  "risk_label": "<High/Medium/Low>",
  "top_factors": ["factor1", "factor2", ...]
}

Do not add any other text or explanation outside the JSON.
""",
    tools=[predict_dropout_risk],
    output_key="risk_assessment",
)


# ---------------------------------------------------------------------------
# 2. Communication Agent
# ---------------------------------------------------------------------------
communication_agent = Agent(
    name="communication_agent",
    model="gemini-1.5-flash",
    description="Generates culturally appropriate outreach messages for ASHA workers.",
    instruction="""You are the Communication Agent for AnchalAI.

You help ASHA workers communicate with at-risk pregnant women in rural India.

You will receive:
- The woman's profile: {woman_profile}
- The risk assessment: {risk_assessment}

Using this information, generate a warm, simple, culturally sensitive outreach message
that an ASHA worker can send to the pregnant woman.

Rules:
- Write the message in the language specified in the profile (look for the "language" field;
  default to Bengali if not specified). Supported languages: Bengali, Hindi, English.
- Keep it under 4 sentences.
- Adjust tone based on:
  - Age: use respectful "didi" for younger women, "didi/boudi" for older.
  - Literacy: keep language very simple if literacy=0.
  - Husband support: if husband_support=0, emphasize community support and that
    the ASHA worker will accompany her.
- Mention the ASHA worker will help with transport if distance is high.
- End with encouragement.
- If risk is High, add gentle urgency without being scary.

Respond with ONLY the outreach message text. Nothing else.
""",
    output_key="outreach_message",
)


# ---------------------------------------------------------------------------
# 3. Escalation Agent
# ---------------------------------------------------------------------------
escalation_agent = Agent(
    name="escalation_agent",
    model="gemini-1.5-flash",
    description="Decides the escalation action based on the dropout risk level.",
    instruction="""You are the Escalation Agent for AnchalAI.

You decide what follow-up action should be taken based on the risk assessment.

You will receive the risk assessment: {risk_assessment}

Apply these rules strictly:
- If risk_percent < 35:  action = "Schedule routine follow-up"
- If risk_percent >= 35 and risk_percent <= 60:  action = "ASHA home visit within 7 days"
- If risk_percent > 60:  action = "Immediate PHC alert + home visit within 48 hours"

Respond with ONLY a JSON object in this exact format:
{
  "risk_percent": <number from the assessment>,
  "risk_label": "<from the assessment>",
  "action": "<one of the three actions above>"
}

Do not add any other text or explanation outside the JSON.
""",
    output_key="escalation_decision",
)


# ---------------------------------------------------------------------------
# 4. Orchestrator Agent (Sequential Pipeline)
# ---------------------------------------------------------------------------
root_agent = SequentialAgent(
    name="orchestrator_agent",
    description="Coordinates the AnchalAI care pipeline: risk analysis → communication → escalation.",
    sub_agents=[risk_analyst_agent, communication_agent, escalation_agent],
)
