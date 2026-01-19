import os
import requests

# Load credentials from Heroku environment variables
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_test():
    if not TOKEN or not CHAT_ID:
        print("❌ CRITICAL ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not found!")
        print("Run: heroku config:get TELEGRAM_BOT_TOKEN to verify.")
        return

    print(f"🕵️‍♂️ [TEST] Using Token: {TOKEN[:6]}... (masked)")
    print(f"🕵️‍♂️ [TEST] Target Chat ID: {CHAT_ID}")
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    # We use MarkdownV2 style for the fancy formatting
    # Note: Special characters like . and ! must be escaped with \\ in MarkdownV2
    msg_body = (
        "✅ *SYSTEM CHECK: Philly P Sniper is ONLINE* 🦅\n\n"
        "Telegram alerts are fully operational\\.\n"
        "Ready to hunt for Hammer Plays\\. 🚀"
    )
    
    payload = {
        "chat_id": CHAT_ID,
        "text": msg_body,
        "parse_mode": "MarkdownV2"
    }
    
    try:
        print("🚀 [TEST] Sending Telegram broadcast...")
        response = requests.post(url, json=payload)
        result = response.json()
        
        if result.get("ok"):
            print("✅ SUCCESS! Check your Telegram app.")
            print(f"Message ID: {result['result']['message_id']}")
        else:
            print("❌ ERROR: Telegram rejected the message.")
            print(f"Response: {result}")
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Connection failed.")
        print(f"Reason: {e}")

if __name__ == "__main__":
    send_test()