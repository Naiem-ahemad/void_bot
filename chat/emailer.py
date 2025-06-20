import google.generativeai as genai
from config import GEMINI_API_KEY
import json, urllib.parse, requests, re

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

def shorten_url(long_url: str) -> str:
    try:
        res = requests.get(f"http://tinyurl.com/api-create.php?url={urllib.parse.quote(long_url)}")
        return res.text if res.status_code == 200 else long_url
    except Exception:
        return long_url

def clean_json(text):
    """Clean and fix common Gemini formatting issues."""
    text = text.strip()
    text = text.replace("“", "\"").replace("”", "\"").replace("‘", "'").replace("’", "'")
    text = re.sub(r",\s*}", "}", text)  # remove trailing commas
    text = re.sub(r",\s*]", "]", text)
    return text

def generate_professional_email(e_prompt: str, recipient_name: str = "Sir/Madam") -> dict:
    prompt = f"""
You are a professional email writer.

Your job is to return a strictly valid JSON object ONLY. Do NOT write explanations.

Return JSON like:
{{
  "subject": "Short, clear subject",
  "body": "Polite email body with greeting and sign-off."
}}

Purpose: "{e_prompt}"
Recipient: "{recipient_name}"

Respond only with JSON, nothing else.
"""

    try:
        response = model.generate_content(prompt)
        content = clean_json(response.text)

        try:
            parsed = json.loads(content)
            subject = parsed.get("subject", "No Subject")
            body = parsed.get("body", "(No body)")
        except json.JSONDecodeError:
            print("[Fallback Parse] Not JSON, trying manual keys...")
            subject, body_lines = "No Subject", []
            for line in content.splitlines():
                if "subject" in line.lower():
                    subject = line.split(":", 1)[-1].strip().strip('"')
                else:
                    body_lines.append(line.strip().strip('"'))
            body = "\n".join(body_lines).strip()

        # Gmail link
        gmail_link = f"https://mail.google.com/mail/?view=cm&fs=1&to=&su={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
        short_link = shorten_url(gmail_link)

        return {
            "subject": subject,
            "body": body,
            "gmail_link": gmail_link,
            "short_link": short_link
        }

    except Exception as e:
        return {
            "subject": "⚠️ Email Generation Failed",
            "body": f"Error generating email: {e}",
            "gmail_link": "",
            "short_link": ""
        }
