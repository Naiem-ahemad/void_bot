import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-1.5-flash")

def detect_mood(text):
    prompt = f"""Analyze the emotional mood of this message and respond with only one emoji and a short mood label (max 2 words). Do not explain anything.

Message: "{text}"
Mood:"""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return "😐 Neutral"
