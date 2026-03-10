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


@app.post("/predict", response_model=CareActionPlan)
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
        state = updated_session.state if updated_session else {}

        # Parse risk assessment
        risk_raw = state.get("risk_assessment", "{}")
        try:
            risk_data = json.loads(risk_raw) if isinstance(risk_raw, str) else risk_raw
        except (json.JSONDecodeError, TypeError):
            risk_data = {"risk_percent": 0, "risk_label": "Unknown", "top_factors": []}

        # Parse escalation decision
        escalation_raw = state.get("escalation_decision", "{}")
        try:
            escalation_data = json.loads(escalation_raw) if isinstance(escalation_raw, str) else escalation_raw
        except (json.JSONDecodeError, TypeError):
            escalation_data = {"action": "Unable to determine escalation"}

        # Get outreach message
        outreach_message = state.get("outreach_message", "Message generation unavailable.")

        return CareActionPlan(
            risk_percent=risk_data.get("risk_percent", 0),
            risk_label=risk_data.get("risk_label", "Unknown"),
            top_factors=risk_data.get("top_factors", []),
            message=outreach_message,
            escalation=escalation_data,
        )

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
