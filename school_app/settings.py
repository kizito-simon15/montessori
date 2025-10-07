import os

# ────────────────────────────────────────────────────────────────────
# Paths
# ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ────────────────────────────────────────────────────────────────────
# Security / Debug
# ────────────────────────────────────────────────────────────────────
# NOTE: move secrets to environment variables for real deployments.
SECRET_KEY = "__$1ud47e&nyso5h5o3fwnqu4+hfqcply9h$k*h2s34)hn5@nc"
DEBUG = True  # keep True for local/ngrok dev; set False in production

# No ports in ALLOWED_HOSTS; use hostnames/IPs only.
ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    ".ngrok-free.app",   # any ngrok subdomain
    # "192.168.x.y",     # <- add your LAN IP here if you test via Wi-Fi
]

# Needed for POST forms/logins via ngrok (scheme required)
CSRF_TRUSTED_ORIGINS = [
    "https://*.ngrok-free.app",
    "http://127.0.0.1",
    "http://localhost",
]

# ────────────────────────────────────────────────────────────────────
# Applications
# ────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",

    # Third-party
    "widget_tweaks",
    "crispy_forms",
    "bootstrap5",
    "crispy_bootstrap5",
    "django_filters",
    "rest_framework",

    # Local apps
    "apps.corecode",
    "apps.students",
    "apps.staffs",
    "apps.finance",
    "expenditures",
    "alevel_students",
    "alevel_results",
    "event",
    "apps.result",
    "updations",
    "school_properties",
    "non_staffs",
    "attendace",
    "library",
    "dashboard",
    "accounts",
    "parents",
    "bursor",
    "teachers",
    "headteacher",
    "sms",
    "mtaa",
    "location",
    "duty",
    "meetings",
    "channels",
    # "django_celery_beat",
    # NOTE: debug_toolbar is added conditionally at the end if enabled
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.corecode.middleware.SiteWideConfigs",
    # debug_toolbar middleware is added conditionally at the end if enabled
]

ROOT_URLCONF = "school_app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.corecode.context_processors.site_defaults",
                "parents.context_processors.student_context",
            ],
        },
    },
]

WSGI_APPLICATION = "school_app.wsgi.application"

# ────────────────────────────────────────────────────────────────────
# Database (SQLite for dev)
# ────────────────────────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
    }
}

# ────────────────────────────────────────────────────────────────────
# Password validation
# ────────────────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ────────────────────────────────────────────────────────────────────
# Static / Media
# ────────────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATICFILES_DIRS = (os.path.join(BASE_DIR, "static"),)
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# ────────────────────────────────────────────────────────────────────
# Authentication
# ────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "accounts.CustomUser"

AUTHENTICATION_BACKENDS = [
    "accounts.backends.ParentUserBackend",       # Custom ParentUser backend
    "django.contrib.auth.backends.ModelBackend", # Default
]

LOGIN_URL = "custom_login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# ────────────────────────────────────────────────────────────────────
# Sessions / I18N / Time
# ────────────────────────────────────────────────────────────────────
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 10800  # 3 hours

TIME_ZONE = "Africa/Dar_es_Salaam"
LANGUAGE_CODE = "en-us"
USE_I18N = True
USE_L10N = False  # keep False if localization formatting interferes
USE_TZ = True
TIME_FORMAT = "H:i"

LANGUAGES = [
    ("en", "English"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("sw", "Kiswahili"),
]
LOCALE_PATHS = [os.path.join(BASE_DIR, "locale")]

# ────────────────────────────────────────────────────────────────────
# Third-party / API keys (dev placeholders)
# ────────────────────────────────────────────────────────────────────
# NOTE: Move these to environment variables in production.
BEEM_API_KEY     = "360d41e9511abd9d"
BEEM_SECRET_KEY  = "NDQ5MzM2ZWQ3OGZkNTQwM2FiZjkwZDgxMzllNTk5MDZlZjQxMmZhZGFjM2Q3ZDIzOWQ4OWI1YjE0ZGM3MzI4OQ=="
BEEM_SOURCE_ADDR = "MONTESSORI"

MPESA_ENVIRONMENT        = "sandbox"  # 'sandbox' or 'production'
MPESA_CONSUMER_KEY       = "uJkuyPeG79kC683dwdWRHFkLHJMpF0QJsb5uGJGkwIDjzfow"
MPESA_CONSUMER_SECRET    = "Em5VTQedGUcxL4Nb7ZPgj57fpoAZhEulUfYHGMsLFOm5E4rdBdn8HYxDcUh04QFQ"
MPESA_SHORTCODE          = "174379"
MPESA_INITIATOR_NAME     = "josephkinyota"
MPESA_INITIATOR_PASSWORD = "Kinyota3543"
MPESA_PASSKEY            = "xVCaovZ4"
MPESA_CALLBACK_URL       = "https://fcd2-197-186-8-1.ngrok-free.app/mpesa-callback/"

# ────────────────────────────────────────────────────────────────────
# Upload limits
# ────────────────────────────────────────────────────────────────────
DATA_UPLOAD_MAX_NUMBER_FIELDS = 200000000
DATA_UPLOAD_MAX_MEMORY_SIZE = None

# ────────────────────────────────────────────────────────────────────
# Channels (ASGI)
# ────────────────────────────────────────────────────────────────────
ASGI_APPLICATION = "school_app.asgi.application"
CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
}

# ────────────────────────────────────────────────────────────────────
# Debug Toolbar — OPT-IN only
# ────────────────────────────────────────────────────────────────────
# To enable, export ENABLE_DJDT=1 in your shell (and keep DEBUG=True)
ENABLE_DJDT = bool(os.getenv("ENABLE_DJDT", ""))

if DEBUG and ENABLE_DJDT:
    try:
        import debug_toolbar  # noqa: F401
        INSTALLED_APPS += ["debug_toolbar"]
        # Insert near the top so it runs early (after Security/Session)
        MIDDLEWARE.insert(1, "debug_toolbar.middleware.DebugToolbarMiddleware")
        INTERNAL_IPS = ["127.0.0.1", "localhost"]
    except Exception:
        # debug_toolbar not installed; skip quietly
        pass
