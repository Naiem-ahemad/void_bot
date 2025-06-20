import os, json, uuid
from datetime import datetime
from config import CHAT_LOG_FOLDER
from chat.summarizer import summarize_title  # You write this using Gemini

def get_user_folder(user_id):
    folder = os.path.join(CHAT_LOG_FOLDER, str(user_id))
    os.makedirs(folder, exist_ok=True)
    return folder
# chat/chat_sessions.py

def rename_chat_title(user_id, session_id, new_title):
    path = os.path.join(get_user_folder(user_id), session_id)
    if not os.path.exists(path):
        return False

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    data["title"] = new_title

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return True

def list_chats(user_id):
    folder = get_user_folder(user_id)
    sessions = []
    for file in os.listdir(folder):
        if file.endswith(".json"):
            with open(os.path.join(folder, file), "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    sessions.append({"id": file, "title": data.get("title", "Unnamed Chat")})
                except: pass
    return sessions

def start_new_chat(user_id):
    folder = get_user_folder(user_id)
    session_id = f"{uuid.uuid4().hex[:8]}.json"
    path = os.path.join(folder, session_id)

    chat_data = {
        "title": "New Chat",
        "created": datetime.now().isoformat(),
        "history": []
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(chat_data, f, indent=2)
    return session_id

def save_message(user_id, session_id, user_msg, bot_reply):
    path = os.path.join(get_user_folder(user_id), session_id)
    if not os.path.exists(path): return False

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    data["history"].append({
        "timestamp": datetime.now().isoformat(),
        "user": user_msg,
        "bot": bot_reply,
    })

    # Update title using summary
    if data["title"] == "New Chat" and len(data["history"]) >= 2:
        data["title"] = summarize_title([m["user"] for m in data["history"]])

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return True

def find_session_by_title(user_id, title):
    folder = get_user_folder(user_id)
    for file in os.listdir(folder):
        if file.endswith(".json"):
            path = os.path.join(folder, file)
            with open(path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    if data.get("title") == title:
                        return file  # return session ID
                except:
                    continue
    return None

def get_chat_history(user_id, session_id):
    path = os.path.join(get_user_folder(user_id), session_id)
    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    history = []
    for entry in data.get("history", []):
        history.append({
            "text": entry["user"],
            "timestamp": entry["timestamp"],
        })
    return history
