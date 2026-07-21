from twilio.rest import Client

ACCOUNT_SID = ""
AUTH_TOKEN = ""
FROM_NUMBER = ""

client = Client(ACCOUNT_SID, AUTH_TOKEN)

def send_sms_otp(phone, otp):
    client.messages.create(
        body=f"Your OTP is {otp}",
        from_=FROM_NUMBER,
        to=phone
    )
