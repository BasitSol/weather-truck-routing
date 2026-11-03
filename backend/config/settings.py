"""Django settings. Everything environment-specific comes from env vars; defaults are for local dev."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Read KEY=value lines from the project's .env into the environment (real env vars win)."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(BASE_DIR.parent / ".env")  # weather-truck-routing/.env, git-ignored


def env_bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).lower() in {"1", "true", "yes"}


DEBUG = env_bool("DJANGO_DEBUG", True)
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key" if DEBUG else "")
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is false")

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o]

INSTALLED_APPS = [
    "rest_framework",
    "trips",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
ASGI_APPLICATION = "config.asgi.application"
WSGI_APPLICATION = "config.wsgi.application"

# No database: the app is stateless by design (see docs/ARCHITECTURE.md §2).
DATABASES: dict[str, dict[str, str]] = {}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": False,
        "OPTIONS": {},
    }
]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "weather-truck-routing",
        "OPTIONS": {"MAX_ENTRIES": 20_000},
    }
}

# The built SPA (frontend/dist) is copied here in the Docker image and served by WhiteNoise.
SPA_DIR = Path(os.environ.get("SPA_DIR", BASE_DIR / "spa"))
STATIC_URL = "/static/"  # unused: no Django static files; WhiteNoise serves the SPA from SPA_DIR
STATIC_ROOT = None
WHITENOISE_ROOT = SPA_DIR if SPA_DIR.exists() else None
WHITENOISE_MAX_AGE = 3600


def _vite_hashed(path: str, url: str) -> bool:
    return url.startswith("/assets/")  # Vite puts content hashes in these names


WHITENOISE_IMMUTABLE_FILE_TEST = _vite_hashed

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
    "EXCEPTION_HANDLER": "trips.api.errors.exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "analyze": os.environ.get("THROTTLE_ANALYZE", "30/min"),
        "geocode": os.environ.get("THROTTLE_GEOCODE", "120/min"),
    },
}

# Routing: Valhalla. With a Stadia Maps key, Stadia's hosted Valhalla is primary and the public
# FOSSGIS server is the fallback; without one, the public server alone (keyless).
STADIA_API_KEY = os.environ.get("STADIA_API_KEY", "").strip()
STADIA_ROUTE_URL = os.environ.get("STADIA_ROUTE_URL", "https://api.stadiamaps.com/route/v1")
VALHALLA_URL = os.environ.get("VALHALLA_URL", "https://valhalla1.openstreetmap.de/route")
OPEN_METEO_URL = os.environ.get("OPEN_METEO_URL", "https://api.open-meteo.com/v1/forecast")
PHOTON_URL = os.environ.get("PHOTON_URL", "https://photon.komoot.io/api/")
HTTP_USER_AGENT = os.environ.get(
    "HTTP_USER_AGENT", "weather-truck-routing/1.0 (assessment project; contact via repository)"
)

CACHE_TTL_ROUTES = int(os.environ.get("CACHE_TTL_ROUTES", 600))
CACHE_TTL_WEATHER = int(os.environ.get("CACHE_TTL_WEATHER", 1800))
CACHE_TTL_GEOCODE = int(os.environ.get("CACHE_TTL_GEOCODE", 86_400))

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SSL_REDIRECT", False)

USE_TZ = True
TIME_ZONE = "UTC"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "loggers": {
        "trips": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
        # httpx logs full request URLs at INFO, which would include the routing API key.
        "httpx": {"level": "WARNING"},
        "httpcore": {"level": "WARNING"},
    },
}
