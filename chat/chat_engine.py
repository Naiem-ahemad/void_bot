import os, json
import tiktoken
from config import GEMINI_API_KEY
import google.generativeai as genai
from datetime import datetime
from chat.chat_sessions import get_chat_history, save_message

# Init model
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# -------------------------------
# Token helpers
# -------------------------------
def count_tokens_gemini(messages, model_name="gpt-3.5-turbo"):
    enc = tiktoken.encoding_for_model(model_name)
    total = 0
    for msg in messages:
        for part in msg["parts"]:
            total += len(enc.encode(part))
    return total

def estimate_token_count(text: str) -> int:
    enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
    return len(enc.encode(text))

# -------------------------------
# File paths
# -------------------------------
def get_session_file_path(user_id: str, session_id: str) -> str:
    return os.path.join("user_data", str(user_id), f"{session_id}.json")

def get_memory_file_path(user_id: int) -> str:
    return os.path.join("user_data", str(user_id), "save", "memory.json")

# -------------------------------
# Memory summarizer
# -------------------------------
def load_memory_summary(user_id: str, session_id: str) -> str:
    path = get_session_file_path(user_id, session_id)
    
    if not os.path.exists(path):
        return ""

    with open(path, "r", encoding="utf-8") as f:
        chat_data = json.load(f)

    if "summary" in chat_data:
        return chat_data["summary"]

    # Build memory lines
    lines = []
    for entry in chat_data.get("history", []):
        user_msg = entry.get("user", "").strip()
        mood = entry.get("mood", "").strip() if "mood" in entry else ""
        if user_msg:
            line = f"User: {user_msg}"
            if mood:
                line += f" (Mood: {mood})"
            lines.append(line)

    full_text = "\n".join(lines)

    if estimate_token_count(full_text) > 300:
        try:
            response = model.generate_content(f"Summarize this chat for memory and emotions:\n{full_text}")
            summary_text = response.text.strip()
            chat_data["summary"] = summary_text
            with open(path, "w", encoding="utf-8") as fw:
                json.dump(chat_data, fw, indent=2)
            return summary_text
        except Exception as e:
            return f"⚠️ Summarization failed: {e}\n\n{full_text}"
    else:
        return full_text

# -------------------------------
# 1. See Msg – extract real memory
# -------------------------------
def see_msg(user_id: int, user_msg: str):
    if len(user_msg.strip()) < 4:
        return

    prompt = f"""
Extract useful memory info from this message:
"{user_msg}"

Only return a valid JSON dictionary of facts like name, city, goal etc.
Ignore small talk or greetings. Example output:

{{
  "name": "Naiem",
  "city": "Delhi"
}}
"""

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()

        # ✅ Fix: Safely find and parse the first JSON block
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1:
            print(f"[Memory Extract Error] No JSON in output:\n{raw}")
            return

        json_str = raw[start:end+1]
        facts = json.loads(json_str)

        if isinstance(facts, dict):
            append_user_memory(user_id, facts)
    except json.JSONDecodeError as e:
        print(f"[Memory Extract Error] Invalid JSON from model:\n{e}\nRaw:\n{response.text}")
    except Exception as e:
        print(f"[Memory Extract Error] {e}")


# -------------------------------
# 2. Append user memory
# -------------------------------
def append_user_memory(user_id: int, facts: dict):
    folder = os.path.join("user_data", str(user_id), "save")
    os.makedirs(folder, exist_ok=True)
    path = get_memory_file_path(user_id)

    memory = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            memory = json.load(f)

    for key, value in facts.items():
        if isinstance(value, list):
            memory[key] = list(set(memory.get(key, []) + value))
        else:
            memory[key] = value

    with open(path, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2)

# -------------------------------
# 3. Load memory before reply
# -------------------------------
def get_user_memory(user_id: int) -> str:
    path = get_memory_file_path(user_id)
    if not os.path.exists(path):
        return ""
    
    with open(path, "r", encoding="utf-8") as f:
        memory = json.load(f)

    memory_lines = [f"{k.capitalize()}: {', '.join(v) if isinstance(v, list) else v}" for k, v in memory.items()]
    return "\n".join(memory_lines)

# -------------------------------
# 4. Final Response Generator
# -------------------------------
def generate_response(user_msg: str, user_id: int, session_id: str, memory: str = "") -> str:
    see_msg(user_id, user_msg)  # ✅ extract memory info every time

    # Load personal memory too
    personal_memory = get_user_memory(user_id)
    
    prompt = f"""You are a smart, emotionally aware Telegram chatbot.
Use memory from previous conversations + user memory.

🧠 Chat Memory:
{memory}

📌 User Memory:
{personal_memory}

Now continue this chat.

User: {user_msg}
Bot:"""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"⚠️ Failed to generate response: {e}"
