"""
AnchalAI Agent — FastAPI HTTP endpoint.

Exposes the OrchestratorAgent as a POST /predict endpoint on port 8080.
Replaces the Flask app for the agent track submission.
"""

import os
import json
import uuid
import traceback

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agent.agent import root_agent

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AnchalAI Agent",
    description="Multi-agent maternal health care pipeline powered by Google ADK",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://mrmallick07.github.io",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "null",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# ADK Runner (shared across requests)
# ---------------------------------------------------------------------------
session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name="anchal_ai",
    session_service=session_service,
)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------
class WomanProfile(BaseModel):
    age: int
    distance_to_phc_km: float
    previous_pregnancies: int
    attended_last_visit: int
    household_income_level: int
    husband_support: int
    literacy: int
    trimester_at_registration: int
    harvest_season: int
    asha_visits_so_far: int
    language: Optional[str] = Field(default="Bengali")


class CareActionPlan(BaseModel):
    risk_percent: float
    risk_label: str
    top_factors: list
    message: str
    escalation: dict


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
async def home():
    return {"status": "AnchalAI Agent is running"}


@app.post("/predict")
async def predict(profile: WomanProfile):
    """
    Accept a woman's profile and return a complete care action plan
    by running the multi-agent pipeline.
    """
    try:
        # Create a fresh session for each request
        session_id = str(uuid.uuid4())
        session = await session_service.create_session(
            app_name="anchal_ai",
            user_id="asha_worker",
            session_id=session_id,
            state={
                "woman_profile": profile.model_dump_json(),
            },
        )

        # Build the user message with the profile data
        profile_dict = profile.model_dump()
        user_message = json.dumps(profile_dict, indent=2)

        user_content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_message)],
        )

        # Run the agent pipeline
        final_response_text = ""
        async for event in runner.run_async(
            user_id="asha_worker",
            session_id=session_id,
            new_message=user_content,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_response_text = event.content.parts[0].text

        # Retrieve results from session state
        updated_session = await session_service.get_session(
            app_name="anchal_ai",
            user_id="asha_worker",
            session_id=session_id,
        )
        state = dict(updated_session.state) if updated_session else {}

        # --- Debug: print raw state values ---
        print("\n[MAIN] ====== Session State After Pipeline ======")
        for key in ["risk_assessment", "outreach_message", "escalation_decision", "woman_profile"]:
            raw = state.get(key, "<MISSING>")
            print(f"[MAIN]   state['{key}'] = {str(raw)[:500]}")
        print("[MAIN] ============================================\n")

        # --- Helper: safely parse JSON from state (handles markdown fences) ---
        def _safe_parse_json(raw_value, fallback: dict) -> dict:
            """Parse a state value that may be a dict, JSON string, or markdown-wrapped JSON."""
            if isinstance(raw_value, dict):
                return raw_value
            if not isinstance(raw_value, str) or not raw_value.strip():
                return fallback
            text = raw_value.strip()
            # Strip markdown code fences if present (```json ... ``` or ``` ... ```)
            if text.startswith("```"):
                lines = text.split("\n")
                # Remove first line (```json or ```) and last line (```)
                lines = [l for l in lines if not l.strip().startswith("```")]
                text = "\n".join(lines).strip()
            try:
                parsed = json.loads(text)
                return parsed if isinstance(parsed, dict) else fallback
            except (json.JSONDecodeError, TypeError):
                print(f"[MAIN] WARNING: Could not parse JSON: {text[:200]}")
                return fallback

        # --- Parse risk assessment ---
        risk_raw = state.get("risk_assessment", None)
        risk_data = _safe_parse_json(risk_raw, {
            "risk_percent": 0,
            "risk_label": "Unknown",
            "top_factors": [],
        })
        risk_percent = risk_data.get("risk_percent", 0)
        risk_label = risk_data.get("risk_label", "Unknown")
        top_factors = risk_data.get("top_factors", [])

        # Ensure risk_percent is a number
        try:
            risk_percent = float(risk_percent)
        except (ValueError, TypeError):
            risk_percent = 0.0

        # --- Parse escalation decision ---
        escalation_raw = state.get("escalation_decision", None)
        escalation_data = _safe_parse_json(escalation_raw, {
            "action": "Unable to determine escalation",
        })

        # --- Get outreach message (plain text, not JSON) ---
        outreach_message = state.get("outreach_message", "Message generation unavailable.")
        if not isinstance(outreach_message, str) or not outreach_message.strip():
            outreach_message = "Message generation unavailable."

        # --- Build final response ---
        response = {
            "risk_percent": risk_percent,
            "risk_label": risk_label,
            "top_factors": top_factors,
            "message": outreach_message.strip(),
            "escalation": escalation_data,
        }
        print(f"[MAIN] Final response: {json.dumps(response, ensure_ascii=False, default=str)[:1000]}")
        return response

    except Exception as e:
        print(f"[PREDICT ERROR] {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
