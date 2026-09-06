from twilio.rest import Client
from app.config import settings

class SMSService:
    def __init__(self):
        if settings.twilio_account_sid and settings.twilio_auth_token:
            self.client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        else:
            self.client = None

    async def send_sms(self, to_number: str, message: str) -> bool:
        if not self.client:
            print(f"Mock SMS to {to_number}: {message}")
            return True
            
        try:
            self.client.messages.create(
                body=message,
                from_=settings.twilio_phone_number,
                to=to_number
            )
            return True
        except Exception as e:
            print(f"Failed to send SMS: {e}")
            return False

sms_service = SMSService()
