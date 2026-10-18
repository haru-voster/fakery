from django.conf import settings
def site(request):
    return {"BRAND": settings.BRAND, "WHATSAPP_NUMBER": settings.WHATSAPP_NUMBER, "SUPPORT_PHONE": settings.SUPPORT_PHONE, "SUPPORT_EMAIL": settings.SUPPORT_EMAIL}
