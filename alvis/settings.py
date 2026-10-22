import os
from pathlib import Path


# ============================================================
# BASE CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"

ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1,bluerockgroupinvestments.com,www.bluerockgroupinvestments.com",
).split(",")


# ============================================================
# SECURITY AND CSRF
# ============================================================

CSRF_TRUSTED_ORIGINS = os.environ.get(
    "CSRF_TRUSTED_ORIGINS",
    "https://bluerockgroupinvestments.com,https://www.bluerockgroupinvestments.com",
).split(",")


# ============================================================
# APPLICATIONS
# ============================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_countries",
    "accounts",
]


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ============================================================
# URL CONFIGURATION
# ============================================================

ROOT_URLCONF = "alvis.urls"


# ============================================================
# TEMPLATES
# ============================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "accounts.context.site",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

# SQLite is suitable for small/testing deployments.
# For production, configure MySQL through environment variables:
# DB_ENGINE, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT.

DB_ENGINE = os.environ.get(
    "DB_ENGINE",
    "django.db.backends.sqlite3",
)

if DB_ENGINE == "django.db.backends.mysql":
    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE,
            "NAME": os.environ.get("DB_NAME", ""),
            "USER": os.environ.get("DB_USER", ""),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "3306"),
            "OPTIONS": {
                "charset": "utf8mb4",
            },
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DB_PATH = os.environ.get(
        "DJANGO_DB_PATH",
        str(BASE_DIR / "db.sqlite3"),
    )

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": DB_PATH,
            "OPTIONS": {
                "timeout": 20,
            },
        }
    }


# ============================================================
# AUTHENTICATION
# ============================================================

AUTHENTICATION_BACKENDS = [
    "accounts.backends.EmailOrUsernameBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
        "OPTIONS": {
            "min_length": 10,
        },
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]

PASSWORD_RESET_TIMEOUT = 3600  # Password reset links expire after 1 hour

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "home"


# ============================================================
# SESSION AND COOKIE SETTINGS
# ============================================================

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7


# ============================================================
# STATIC AND MEDIA FILES
# ============================================================

STATIC_URL = "static/"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "private_media"

# Keep sensitive KYC files outside publicly accessible directories.

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ============================================================
# EMAIL CONFIGURATION
# ============================================================

EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"
    if os.environ.get("EMAIL_HOST")
    else "django.core.mail.backends.console.EmailBackend"
)

# Zoho Mail SMTP (works with any SMTP provider by changing the env vars).
# Pick the host that matches the data centre your Zoho account lives in:
#   smtp.zoho.com  (global / US)    smtp.zoho.eu  (Europe)
#   smtp.zoho.in   (India)          smtp.zoho.com.au (Australia)
# Port 587 = STARTTLS (default). For port 465 set EMAIL_PORT=465 and
# EMAIL_USE_SSL=1 (EMAIL_USE_TLS is switched off automatically).
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "0") == "1"
EMAIL_USE_TLS = not EMAIL_USE_SSL
EMAIL_TIMEOUT = 20

# Full Zoho mailbox address, e.g. no-reply@bluerockgroupinvestments.com
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
# Mailbox password, or a Zoho "application-specific password" if 2FA is on.
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")

# Zoho only accepts mail whose From address is the authenticated mailbox
# (or an alias of it), so keep this on the same address as EMAIL_HOST_USER.
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL",
    "BlueRock Group Investment <no-reply@bluerockgroupinvestments.com>",
)


# ============================================================
# AFRICASTALKING SMS CONFIGURATION
# ============================================================

AT_USERNAME = os.environ.get("AT_USERNAME", "")
AT_API_KEY = os.environ.get("AT_API_KEY", "")
AT_SENDER_ID = os.environ.get("AT_SENDER_ID", "")


# ============================================================
# BRANDING AND SUPPORT CONTACTS
# ============================================================

BRAND = "BlueRock Group Investments"

WHATSAPP_NUMBER = os.environ.get(
    "WHATSAPP_NUMBER",
    "17746997556",
)  # Digits only, including country code

SUPPORT_PHONE = os.environ.get(
    "SUPPORT_PHONE",
    "",
)  # Configure the real support number in the environment

SUPPORT_EMAIL = os.environ.get(
    "SUPPORT_EMAIL",
    "",
)  # Configure the real support email in the environment


# ============================================================
# HTTPS AND PRODUCTION SECURITY
# ============================================================

# Keep HTTPS redirection disabled here to preserve the original
# configuration. Enable it only after verifying HTTPS/proxy setup.

if not DEBUG:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 31536000
    SECURE_CONTENT_TYPE_NOSNIFF = True


# Configure these values using production environment variables.
# USDT on TRON Mainnet (TRC-20)
USDT_TRC20_RECEIVING_ADDRESS = os.environ.get(
    "USDT_TRC20_RECEIVING_ADDRESS",
    "",
).strip()

# TronGrid API key for querying TRON Mainnet
TRON_PRO_API_KEY = os.environ.get(
    "TRON_PRO_API_KEY",
    "",
).strip()

# Minimum number of TRON block confirmations before crediting deposits
USDT_TRC20_CONFIRMATIONS = int(
    os.environ.get("USDT_TRC20_CONFIRMATIONS", "20")
)

# Official USDT TRC-20 contract on TRON Mainnet
USDT_TRC20_CONTRACT_ADDRESS = "TYvc2efMRD3hKEN77rebUSbFMHd5YvxXsX"