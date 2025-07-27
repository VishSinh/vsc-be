import os
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "django-insecure-xmz33x=#rph_-+0f&p&y)b7xz55%xoi-5@@b8u=d%-#ndh!lbn"

DEBUG = True

ALLOWED_HOSTS: List[str] = []

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
]

AUTH_USER_MODEL = "accounts.Staff"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Middlewares
    "vsc_be.middlewares.auth_middleware.AuthMiddleware",
    "vsc_be.middlewares.exception_middleware.ExceptionMiddleware",
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
        "NAME": "vsc",
        "USER": "vish",
        "PASSWORD": "vish123",
        "HOST": "localhost",
        "PORT": "5432",
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

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Authentication Settings
TOKEN_SECRET = os.getenv("TOKEN_SECRET", SECRET_KEY)
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", SECRET_KEY)
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_MINUTES = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", 60 * 24 * 30))

# Authentication Skip Patterns (endpoints that don't require authentication)
SKIP_AUTH_PATTERNS = [
    # Authentication endpoints
    "/api/v1/auth/login/",
]


TAX_PERCENTAGE = 0
