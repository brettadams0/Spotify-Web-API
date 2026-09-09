"""Application configuration, sourced from the environment."""
from __future__ import annotations

import os
from datetime import timedelta


def _bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Base configuration shared by every environment."""

    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY") or os.urandom(32).hex()
    SESSION_COOKIE_NAME = "spotify-stats-session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", False)
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    JSON_SORT_KEYS = False

    # Spotify OAuth
    SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID", "")
    SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
    SPOTIFY_REDIRECT_URI = os.environ.get(
        "SPOTIFY_REDIRECT_URI", "http://127.0.0.1:5000/callback"
    )

    # How long an upstream Spotify response may be reused, in seconds.
    CACHE_TTL = int(os.environ.get("CACHE_TTL", "120"))

    # Requests to the Spotify Web API time out after this many seconds.
    SPOTIFY_TIMEOUT = int(os.environ.get("SPOTIFY_TIMEOUT", "10"))


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret-key"
    SPOTIFY_CLIENT_ID = "test-client-id"
    SPOTIFY_CLIENT_SECRET = "test-client-secret"
    SPOTIFY_REDIRECT_URI = "http://localhost/callback"
    CACHE_TTL = 0
