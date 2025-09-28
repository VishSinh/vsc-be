import os
from pathlib import Path
from typing import Dict, List

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATIC_URL = "/static/"

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# =================================================
# Environment Variables
# =================================================
# General Settings
SECRET_KEY = config("SECRET_KEY", default="")
DEBUG = config("DEBUG", default=False, cast=bool)
SESSION_SECRET_KEY = config("SESSION_SECRET_KEY", default="")
ALLOWED_HOSTS: List[str] = config("ALLOWED_HOSTS", default="localhost,127.0.0.1").split(",")

# Authentication Settings
TOKEN_SECRET = config("TOKEN_SECRET", default="")
ALGORITHM = config("ALGORITHM", default="HS256")
TOKEN_EXPIRE_MINUTES = config("TOKEN_EXPIRE_MINUTES", default=6000, cast=int)

# Database Settings
# DATABASE_NAME = os.getenv("DATABASE_NAME")
# DATABASE_USER = os.getenv("DATABASE_USER")
# DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
# DATABASE_HOST = os.getenv("DATABASE_HOST")
# DATABASE_PORT = os.getenv("DATABASE_PORT")

# S3 Settings
# BUCKET_NAME = os.getenv("BUCKET_NAME")
# S3_CLIENT_ENDPOINT = os.getenv("S3_CLIENT_ENDPOINT")
# S3_CLIENT_REGION = os.getenv("S3_CLIENT_REGION")
# S3_CLIENT_ACCESS_KEY_ID = os.getenv("S3_CLIENT_ACCESS_KEY_ID")
# S3_CLIENT_SECRET_ACCESS_KEY = os.getenv("S3_CLIENT_SECRET_ACCESS_KEY")
# S3_DOWNLOAD_URL = os.getenv("S3_DOWNLOAD_URL")
# S3_IMAGE_FOLDER = os.getenv("S3_IMAGE_FOLDER")

# Media/Uploads Settings (local filesystem)
MEDIA_URL = config("MEDIA_URL", default="/media/")
MEDIA_ROOT = config("MEDIA_ROOT", default=os.path.join(BASE_DIR, "media"))
PUBLIC_BASE_URL = config("PUBLIC_BASE_URL", default="")
IMAGE_UPLOAD_FOLDER = config("IMAGE_UPLOAD_FOLDER", default="images")

# Business Settings
TAX_PERCENTAGE = config("TAX_PERCENTAGE", default=0.0, cast=float)
LOW_STOCK_THRESHOLD = config("LOW_STOCK_THRESHOLD", default=250, cast=int)
OUT_OF_STOCK_THRESHOLD = config("OUT_OF_STOCK_THRESHOLD", default=50, cast=int)
# =================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Django Apps
    "core",
    "accounts",
    "inventory",
    "orders",
    "production",
    "auditing",
    # Third Party Apps
    "django_extensions",
    "corsheaders",
]

AUTH_USER_MODEL = "accounts.Staff"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "vsc_be.middlewares.auth_middleware.AuthMiddleware",
    "vsc_be.middlewares.exception_middleware.ExceptionMiddleware",
    "vsc_be.middlewares.logging_middleware.LoggingMiddleware",
]

ROOT_URLCONF = "vsc_be.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "vsc_be.wsgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST"),
        "PORT": config("DB_PORT"),
        # Optional schema: set search_path
        "OPTIONS": {
            "options": f"-c search_path={config('POSTGRES_SCHEMA', default='public')},public",
        },
        "CONN_MAX_AGE": int(config("DB_CONN_MAX_AGE", default=600)),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Kolkata"

USE_I18N = True

USE_TZ = True


STATIC_URL = "/static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Authentication Skip Patterns (endpoints that don't require authentication)
SKIP_AUTH_PATTERNS = [
    "/api/v1/auth/login/",
    # "/api/v1/auth/register/",
    # "/admin/"
    "/media/",
    "/api/v1/health/",
]


CORS_ALLOW_CREDENTIALS = config("CORS_ALLOW_CREDENTIALS", default=False, cast=bool)
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="").split(",")
CORS_ALLOWED_ORIGIN_REGEXES = config("CORS_ALLOWED_ORIGIN_REGEXES", default="").split(",")


# API logging toggle
ENABLE_API_LOGGING = config("ENABLE_API_LOGGING", default=True, cast=bool)

# API audit logging toggles
ENABLE_API_DB_AUDIT = config("ENABLE_API_DB_AUDIT", default=True, cast=bool)
AUDIT_EXCLUDED_PATHS: List[str] = [
    p
    for p in config(
        "AUDIT_EXCLUDED_PATHS",
        default="/api/v1/audit/model-logs/,/api/v1/audit/api-logs/",
    ).split(",")
    if p
]
AUDIT_REDACTED_FIELDS: List[str] = [
    k for k in config("AUDIT_REDACTED_FIELDS", default="password,token,authorization,cookie,secret,api_key").split(",") if k
]
AUDIT_MAX_BODY_CHARS = config("AUDIT_MAX_BODY_CHARS", default=4096, cast=int)

AUDIT_INCLUDE_APPS: List[str] = ["accounts", "inventory", "orders", "production"]
AUDIT_EXCLUDE_APPS: List[str] = []
AUDIT_EXCLUDE_MODELS: List[str] = ["auditing.ModelAuditLog", "auditing.APIAuditLog"]
AUDIT_FIELD_IGNORE: Dict[str, List[str]] = {"*": ["created_at", "updated_at", "last_login"]}
