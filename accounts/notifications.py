import logging, requests
from django.conf import settings
from django.core.mail import send_mail
log = logging.getLogger(__name__)
def send_sms(to, text):
    """Africa's Talking SMS. Skips quietly if keys are not configured."""
    if not (settings.AT_USERNAME and settings.AT_API_KEY):
        log.info("SMS (not sent, no keys) to %s: %s", to, text); return False
    data = {"username": settings.AT_USERNAME, "to": to, "message": text}
    if settings.AT_SENDER_ID: data["from"] = settings.AT_SENDER_ID
    try:
        r = requests.post("https://api.africastalking.com/version1/messaging", data=data, timeout=10,
            headers={"apiKey": settings.AT_API_KEY, "Accept": "application/json"})
        r.raise_for_status(); return True
    except requests.RequestException as e:
        log.warning("SMS failed: %s", e); return False
def notify_signup(user):
    b = settings.BRAND
    send_mail(f"Welcome to {b}", f"Hi {user.username},\n\nYour {b} account was created. If this wasn't you, contact support immediately.",
              settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
    send_sms(user.profile.phone, f"{b}: welcome {user.username}! Your account has been created.")
def notify_support(name, phone, text):
    """Alert staff by SMS and email when a visitor sends a chat message."""
    if settings.SUPPORT_PHONE:
        send_sms(settings.SUPPORT_PHONE, f"{settings.BRAND} chat from {name} {phone}: {text[:120]}")
    if settings.SUPPORT_EMAIL:
        send_mail(f"New chat message from {name}", f"Phone: {phone}\n\n{text}", settings.DEFAULT_FROM_EMAIL,
                  [settings.SUPPORT_EMAIL], fail_silently=True)
