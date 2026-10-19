import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,bluerockgroupinvestiments.com,www.bluerockgroupinvestiments.com").split(",")
CSRF_TRUSTED_ORIGINS = os.environ.get("CSRF_TRUSTED_ORIGINS", "https://bluerockgroupinvestiments.com,https://www.bluerockgroupinvestiments.com").split(",")
INSTALLED_APPS = ["django.contrib.admin","django.contrib.auth","django.contrib.contenttypes",
    "django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles",
    "django_countries","accounts"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware","django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware","django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware","django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware"]
ROOT_URLCONF = "alvis.urls"
TEMPLATES = [{"BACKEND":"django.template.backends.django.DjangoTemplates","DIRS":[],"APP_DIRS":True,
  "OPTIONS":{"context_processors":["django.template.context_processors.request",
  "django.contrib.auth.context_processors.auth","accounts.context.site","django.contrib.messages.context_processors.messages"]}}]
DATABASES = {"default":{"ENGINE":"django.db.backends.sqlite3","NAME":BASE_DIR/"db.sqlite3"}}
AUTHENTICATION_BACKENDS = ["accounts.backends.EmailOrUsernameBackend"]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"}]
PASSWORD_RESET_TIMEOUT = 3600  # reset links expire after 1 hour
SESSION_COOKIE_HTTPONLY = True; SESSION_COOKIE_AGE = 60*60*24*7
LOGIN_URL = "login"; LOGIN_REDIRECT_URL = "dashboard"; LOGOUT_REDIRECT_URL = "home"
STATIC_URL = "static/"; MEDIA_URL = "media/"; MEDIA_ROOT = BASE_DIR/"private_media"  # keep KYC files off public paths
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
EMAIL_BACKEND = ("django.core.mail.backends.smtp.EmailBackend" if os.environ.get("EMAIL_HOST")
                 else "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST",""); EMAIL_PORT = 587; EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER",""); EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD","")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL","BlueRock Group Investment <no-reply@bluerockgroupinvestiments.com>")
AT_USERNAME = os.environ.get("AT_USERNAME",""); AT_API_KEY = os.environ.get("AT_API_KEY","")
AT_SENDER_ID = os.environ.get("AT_SENDER_ID","")
BRAND = "BlueRock Group Investiments"
if not DEBUG:
    SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000; SECURE_CONTENT_TYPE_NOSNIFF = True
WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "254700000000")  # digits only, with country code
SUPPORT_PHONE = os.environ.get("SUPPORT_PHONE", "")   # Set the real admin/support number in .env
SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", "")   # Set the real support email in .env

# Ethereum mainnet ERC-20 USDT deposit monitoring. Configure these in production environment.
USDT_ERC20_RECEIVING_ADDRESS = os.environ.get("USDT_ERC20_RECEIVING_ADDRESS", "").strip()
ETHEREUM_RPC_URL = os.environ.get("ETHEREUM_RPC_URL", "").strip()
USDT_ERC20_CONFIRMATIONS = int(os.environ.get("USDT_ERC20_CONFIRMATIONS", "12"))
