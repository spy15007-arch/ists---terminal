import os
import requests
import time

def send_telegram_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("✅ Message sent successfully.")
    except Exception as e:
        print(f"❌ Failed to send message: {e}")

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("❌ Telegram credentials not found in environment variables.")
        return

    # Pointing Telegram directly to the mobile-formatted card files
    files_to_send = [
        "intraday_tg.txt",
        "btst_tg.txt",
        "swing_tg.txt"
    ]

    for filename in files_to_send:
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
            if content.strip():
                chunks = [content[i:i+4000] for i in range(0, len(content), 4000)]
                for chunk in chunks:
                    send_telegram_message(token, chat_id, chunk)
                    time.sleep(1) 
        else:
            print(f"⚠️ {filename} not found.")

if __name__ == "__main__":
    main()
