import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

def summarize_title(user_inputs: list[str]) -> str:
    text = "\n".join(user_inputs[:5])
    prompt = f"Give a short title for this conversation:\n{text}"
    try:
        response = model.generate_content(prompt)
        return response.text.strip().strip('"')
    except:
        return "Chat"
