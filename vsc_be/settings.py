import os
from pathlib import Path
from typing import List

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


# =================================================
# Environment Variables
# =================================================
# General Settings
SECRET_KEY = os.getenv("SECRET_KEY")
DEBUG = os.getenv("DEBUG") == "True"
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY")
ALLOWED_HOSTS: List[str] = os.getenv("ALLOWED_HOSTS", "").split(",")

# Authentication Settings
TOKEN_SECRET = os.getenv("TOKEN_SECRET")
ALGORITHM = os.getenv("ALGORITHM")
TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", 6000))

# Database Settings
DATABASE_NAME = os.getenv("DATABASE_NAME")
DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_HOST = os.getenv("DATABASE_HOST")
DATABASE_PORT = os.getenv("DATABASE_PORT")

# S3 Settings
BUCKET_NAME = os.getenv("BUCKET_NAME")
S3_CLIENT_ENDPOINT = os.getenv("S3_CLIENT_ENDPOINT")
S3_CLIENT_REGION = os.getenv("S3_CLIENT_REGION")
S3_CLIENT_ACCESS_KEY_ID = os.getenv("S3_CLIENT_ACCESS_KEY_ID")
S3_CLIENT_SECRET_ACCESS_KEY = os.getenv("S3_CLIENT_SECRET_ACCESS_KEY")
S3_DOWNLOAD_URL = os.getenv("S3_DOWNLOAD_URL")
S3_IMAGE_FOLDER = os.getenv("S3_IMAGE_FOLDER")

# Business Settings
TAX_PERCENTAGE = float(os.getenv("TAX_PERCENTAGE", 0.0))
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
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Middlewares
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
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL"),
        conn_max_age=600,
        conn_health_checks=True,
    )
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

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Authentication Skip Patterns (endpoints that don't require authentication)
SKIP_AUTH_PATTERNS = [
    "/api/v1/auth/login/",
    # "/admin/"
]


CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS") == "True"
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
CORS_ALLOWED_ORIGIN_REGEXES = os.getenv("CORS_ALLOWED_ORIGIN_REGEXES", "").split(",")
