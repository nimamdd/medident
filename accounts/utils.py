import random
import requests
from django.conf import settings
from .models import PhoneOTP

def normalize_phone(phone: str) -> str:
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("+98"):
        phone = "0" + phone[3:]
    elif phone.startswith("98"):
        phone = "0" + phone[2:]
    return phone

def generate_code() -> str:
    return f"{random.randint(10000, 99999)}"


def send_otp(phone: str, code: str):
    phone = normalize_phone(phone)

    url = settings.AMOOTSMS_URL
    token = settings.AMOOTSMS_TOKEN
    pattern_id = settings.AMOOTSMS_PATTERN_ID


    payload = {
        "Token": token,
        "Mobile": phone,
        "PatternCodeID": int(pattern_id),
        "PatternValues": code,
    }

    headers = {"Authorization": token}

    r = requests.post(url, data=payload, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text

def issue_otp(phone: str):
    phone = normalize_phone(phone)
    otp = PhoneOTP.create_for_phone(phone=phone, ttl_minutes=2)
    otp.code = generate_code()
    otp.save(update_fields=["code"])
    send_otp(phone, otp.code)
    return otp