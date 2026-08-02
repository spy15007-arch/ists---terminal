import os
import requests

# Fetch secrets securely from GitHub Actions
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(text):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram credentials missing. Skipping push.")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # Telegram has a 4096 character limit per message; chunk if necessary
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        payload = {
            "chat_id": CHAT_ID,
            "text": chunk,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Successfully sent to Telegram!")
        else:
            print(f"Failed to send: {response.text}")

if __name__ == "__main__":
    reports = ["breakoutsummary.md", "aggressivesummary.md", "budgetsummary.md"]
    
    for report in reports:
        if os.path.exists(report):
            with open(report, "r", encoding="utf-8") as file:
                content = file.read().strip()
                if len(content) > 10:
                    send_telegram_message(content)
