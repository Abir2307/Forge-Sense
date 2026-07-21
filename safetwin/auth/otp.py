import secrets
import time

OTP_EXPIRY = 180  # 3 minutes

otp_store = {}

def generate_otps(user_id):
    email_otp = f"{secrets.randbelow(900000) + 100000}"
    sms_otp = f"{secrets.randbelow(900000) + 100000}"

    otp_store[user_id] = {
        "email": email_otp,
        "sms": sms_otp,
        "expiry": time.time() + OTP_EXPIRY
    }

    return email_otp, sms_otp


def verify_email_otp(user_id, otp):
    data = otp_store.get(user_id)
    if not data:
        return False

    if time.time() > data["expiry"]:
        otp_store.pop(user_id, None)
        return False

    if otp == data["email"]:
        otp_store.pop(user_id, None)
        return True

    return False


def verify_sms_otp(user_id, otp):
    data = otp_store.get(user_id)
    if not data:
        return False

    if time.time() > data["expiry"]:
        otp_store.pop(user_id, None)
        return False

    if otp == data["sms"]:
        otp_store.pop(user_id, None)  
        return True

    return False

