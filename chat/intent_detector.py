import google.generativeai as genai
from config import GEMINI_API_KEY
import json

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

def detect_intent(user_msg):
    classification_prompt = f"""
Decide what task the following message is asking.

Respond ONLY with one of the following exact words:
- "image"
- "search"
- "chat"
- "email"

Rules:
- Use "image" for drawing/illustration/image generation prompts.
- Use "search" if it asks for real-time info (news, prices, current events).
- Use "chat" for normal Q&A and conversations.
- Use "email" if the user is asking to write or send an email, letter, invitation, or message to someone.

Message: "{user_msg}"
Intent:
"""

    try:
        response = model.generate_content(classification_prompt)
        intent = response.text.strip().lower()

        if intent == "email":
            extract_prompt = f"""
You are an email extraction tool.

Extract the following fields from the user's message:
- "to": Who is the email for?
- "e_prompt": What should the email say?

Only respond in valid JSON format like:
{{
  "to": "wife",
  "e_prompt": "Tell her we are going on a surprise honeymoon next week."
}}

Message: "{user_msg}"
Now respond in JSON:
"""
            extraction = model.generate_content(extract_prompt)
            text = extraction.text.strip()

            try:
                parsed = json.loads(text)
                return {
                    "intent": "email",
                    "to": parsed.get("to", "unknown"),
                    "e_prompt": parsed.get("e_prompt", user_msg)
                }
            except json.JSONDecodeError:
                print("[Fallback Parse] Not valid JSON, trying manual keys...")
                to, e_prompt = "unknown", user_msg
                for line in text.splitlines():
                    if "to" in line.lower():
                        to = line.split(":", 1)[-1].strip().strip('"')
                    elif "e_prompt" in line.lower():
                        e_prompt = line.split(":", 1)[-1].strip().strip('"')
                return {
                    "intent": "email",
                    "to": to,
                    "e_prompt": e_prompt
                }

        # Non-email intent — do not return e_prompt
        elif intent in ["chat", "search", "image"]:
            return intent


        # Fallback
        return "chat"
        

    except Exception as e:
        print(f"[ERROR] Gemini exception: {e}")
        return "chat"
        
