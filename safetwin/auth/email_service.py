import smtplib
from email.mime.text import MIMEText

EMAIL = "abirsaha548@gmail.com"
APP_PASSWORD = "scyw abkq bquy usco" 

def send_email_otp(to_email, otp):
    msg = MIMEText(f"Your OTP is: {otp}")
    msg['Subject'] = "Your OTP"
    msg['From'] = EMAIL
    msg['To'] = to_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL, APP_PASSWORD)
            server.send_message(msg)
        return True, "OTP sent"
    except Exception as e:
        error_msg = f"Email sending failed: {e}"
        print(error_msg)
        return False, error_msg

