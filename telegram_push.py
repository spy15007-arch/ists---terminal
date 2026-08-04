import requests

# Replace with your actual credentials or import them from a config/env file
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID_HERE"

def send_to_telegram(message_text):
    """Safely pushes the message to Telegram, respecting character limits."""
    
    # Telegram has a strict 4096 character limit. Truncate if necessary.
    if len(message_text) > 4000:
        message_text = message_text[:4000] + "\n\n... [Results Truncated Due to Length]"

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message_text,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print("Successfully sent results to Telegram!")
        else:
            print(f"Telegram API Error: {response.status_code}\n{response.text}")
    except Exception as e:
        print(f"Failed to connect to Telegram: {e}")
