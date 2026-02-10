import random
from .models import PhoneOTP


def generate_code() -> str:
    return f"{random.randint(10000, 99999)}"

def send_otp(phone: str, code: str):
    print(f"[OTP] phone={phone} code={code}")

def issue_otp(phone: str):
    otp = PhoneOTP.create_for_phone(phone=phone, ttl_minutes=2)
    otp.code = generate_code()
    otp.save(update_fields=["code"])
    send_otp(phone, otp.code)
    return otp