import json
import os
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def handler(event, context):
    body = json.loads(event['body'])

    if "message" in body:
        chat_id = body["message"]["chat"]["id"]
        text = body["message"].get("text", "")
        reply = f"You said: {text}"

        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": reply}
        )

    return {
        "statusCode": 200,
        "body": json.dumps({"status": "ok"})
    }