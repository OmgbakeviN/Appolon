from pathlib import Path
import os
from dotenv import load_dotenv
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

IS_RENDER = bool(os.getenv("RENDER_SERVICE_ID") or os.getenv("RENDER_EXTERNAL_HOSTNAME"))

SECRET_KEY = os.getenv("SECRET_KEY") or "dev-only-unsafe-secret-key"
DEBUG = (os.getenv("DEBUG", "true").lower() == "true") if not IS_RENDER else False

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
external = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if external:
    ALLOWED_HOSTS.append(external)
    CSRF_TRUSTED_ORIGINS = [f"https://{external}"]

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
if not DEBUG:
    STORAGES["staticfiles"] = {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates"]
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
