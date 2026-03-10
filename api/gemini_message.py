from google import genai
from dotenv import load_dotenv
import os
import traceback

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def generate_asha_message(woman_profile: dict, language: str = "Bengali") -> str:
    """
    Takes a woman's risk profile and generates a personalized
    outreach message for the ASHA worker to send.
    """

    # Build context from profile
    age = woman_profile["age"]
    distance = woman_profile["distance_to_phc_km"]
    attended_last = "attended" if woman_profile["attended_last_visit"] == 1 else "missed"
    trimester = woman_profile["trimester_at_registration"]
    husband_support = "supportive" if woman_profile["husband_support"] == 1 else "unsupportive"
    risk_score = woman_profile.get("risk_percent", "high")

    prompt = f"""
You are AnchalAI, a compassionate maternal health assistant helping ASHA workers 
in rural India reach out to at-risk pregnant women.

Generate a warm, simple, culturally sensitive outreach message in {language} 
for an ASHA worker to send to a pregnant woman with this profile:

- Age: {age} years old
- Distance from nearest PHC: {distance} km
- Last scheduled visit: {attended_last}
- Registered in trimester: {trimester}
- Husband's support level: {husband_support}
- Dropout risk: {risk_score}%

Rules:
- Write ONLY in {language} script
- Keep it under 4 sentences
- Warm and personal, not clinical or scary
- Mention the ASHA worker will help with transport if needed
- End with encouragement

Only output the message. Nothing else.
"""

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"[GEMINI ERROR] Failed to generate message: {e}")
        traceback.print_exc()
        raise


# Test it directly
if __name__ == "__main__":
    test_profile = {
        "age": 19,
        "distance_to_phc_km": 18.5,
        "attended_last_visit": 0,
        "trimester_at_registration": 3,
        "husband_support": 0,
        "literacy": 0,
        "risk_percent": 78
    }

    print("Generating message...\n")
    message = generate_asha_message(test_profile, language="Bengali")
    print("Bengali Message:")
    print(message)
    print("\n---\n")

    message_hindi = generate_asha_message(test_profile, language="Hindi")
    print("Hindi Message:")
    print(message_hindi)
