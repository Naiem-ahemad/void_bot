import requests
import os
import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
# Load Gemini model
model = genai.GenerativeModel("gemini-1.5-flash")

# Function 1: Extract raw text using ocr.space
def extract_text_from_image(image_path: str) -> str:
    api_url = "https://api.ocr.space/parse/image"
    try:
        with open(image_path, 'rb') as image_file:
            response = requests.post(
                api_url,
                files={'file': image_file},
                data={
                    'language': 'eng',
                    'isOverlayRequired': False,
                    'OCREngine': 2,
                    'scale': True,
                    'detectOrientation': True,
                    'isTable': False,
                    'apikey': 'helloworld'  # Free demo key
                }
            )
        result = response.json()

        if result.get("IsErroredOnProcessing"):
            return f"❌ OCR error: {result.get('ErrorMessage', 'Unknown error')}"

        parsed_text = result['ParsedResults'][0]['ParsedText']
        return parsed_text.strip()
    except Exception as e:
        return f"❌ Failed to extract text: {e}"

# Function 2: Clean/Refine text using Gemini
def clean_text_with_gemini(raw_text: str) -> str:
    prompt = f"""
This is raw text extracted from a screenshot using OCR. 
Clean, rewrite, and organize it in a more readable and user-friendly way. Remove timestamps, battery icons, and noise if present.

Text:
\"\"\"
{raw_text}
\"\"\"
"""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"❌ Gemini failed to clean text: {e}"

