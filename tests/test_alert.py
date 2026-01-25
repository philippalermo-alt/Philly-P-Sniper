import os
from twilio.rest import Client

SID = os.getenv('TWILIO_SID')
TOKEN = os.getenv('TWILIO_TOKEN')
FROM_NUM = os.getenv('TWILIO_FROM')
TO_NUM = os.getenv('USER_PHONE')

def send_test():
    try:
        print("🚀 Sending safe test...")
        client = Client(SID, TOKEN)
        
        # Boring message to bypass spam filters
        msg_body = "Philly P system check. Connection established."
        
        message = client.messages.create(
            body=msg_body,
            from_=FROM_NUM,
            to=TO_NUM
        )
        print(f"✅ Sent! SID: {message.sid}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    send_test()