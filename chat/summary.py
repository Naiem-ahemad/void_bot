# search/summary.py
import google.generativeai as genai
from config import GEMINI_API_KEY
genai.configure(api_key=GEMINI_API_KEY)

def summarize_search_results(results_text: str) -> str:
    prompt = f"""
You're a helpful assistant. Summarize the following real-time web results in simple words.

Results:
{results_text}

Summary:"""

    try:
        response = genai.GenerativeModel("gemini-1.5-flash").generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"❌ Gemini summary error: {e}"
