"""Spotify Web API integration: OAuth, a cached client, and response shaping.

Every endpoint used here is one that remains available to newly registered
Spotify applications. The endpoints Spotify restricted on 2024-11-27
(audio-features, audio-analysis, recommendations, related-artists,
featured-playlists) are deliberately not used.
"""
from __future__ import annotations

import logging
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Callable

import spotipy
from flask import current_app, session
from spotipy.cache_handler import FlaskSessionCacheHandler
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOAuth

log = logging.getLogger(__name__)

#: Scopes the app requests. Kept to the minimum each feature needs.
SCOPES = " ".join(
    [
        "user-read-private",
        "user-read-email",
        "user-top-read",
        "user-read-recently-played",
        "user-read-currently-playing",
        "user-read-playback-state",
        "user-follow-read",
        "playlist-read-private",
        "playlist-modify-private",
        "playlist-modify-public",
    ]
)

#: Time ranges Spotify supports for top items, with display labels.
TIME_RANGES: dict[str, str] = {
    "short_term": "Last 4 weeks",
    "medium_term": "Last 6 months",
    "long_term": "All time",
}
DEFAULT_TIME_RANGE = "medium_term"

TOKEN_SESSION_KEY = "token_info"


class SpotifyAuthRequired(Exception):
    """Raised when the current visitor has no usable Spotify token."""


class SpotifyUnavailable(Exception):
    """Raised when Spotify answered with an error we cannot recover from."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def normalise_time_range(value: str | None) -> str:
    """Return a valid Spotify time_range, falling back to the default."""
    return value if value in TIME_RANGES else DEFAULT_TIME_RANGE


# --------------------------------------------------------------------------
# OAuth
# --------------------------------------------------------------------------


def make_oauth(state: str | None = None) -> SpotifyOAuth:
    """Build a SpotifyOAuth bound to the current Flask session.

    A fresh instance is created per request so the token cache always points
    at the active session rather than a module-level global.
    """
    cfg = current_app.config
    return SpotifyOAuth(
        client_id=cfg["SPOTIFY_CLIENT_ID"],
        client_secret=cfg["SPOTIFY_CLIENT_SECRET"],
        redirect_uri=cfg["SPOTIFY_REDIRECT_URI"],
        scope=SCOPES,
        state=state,
        cache_handler=FlaskSessionCacheHandler(session),
        show_dialog=True,
        open_browser=False,
        requests_timeout=cfg["SPOTIFY_TIMEOUT"],
    )


def credentials_configured() -> bool:
    """True when a client id and secret are present in the configuration."""
    cfg = current_app.config
    return bool(cfg.get("SPOTIFY_CLIENT_ID") and cfg.get("SPOTIFY_CLIENT_SECRET"))


def is_authenticated() -> bool:
    """True when the session holds a token that is valid or refreshable."""
    token = session.get(TOKEN_SESSION_KEY)
    if not token:
        return False
    if token.get("expires_at", 0) - int(time.time()) > 60:
        return True
    return bool(token.get("refresh_token"))


def get_client() -> spotipy.Spotify:
    """Return an authenticated Spotify client, refreshing the token if needed.

    Raises:
        SpotifyAuthRequired: when no token is present or the refresh failed.
    """
    token = session.get(TOKEN_SESSION_KEY)
    if not token:
        raise SpotifyAuthRequired("No Spotify token in session")

    if token.get("expires_at", 0) - int(time.time()) < 60:
        refresh_token = token.get("refresh_token")
        if not refresh_token:
            session.pop(TOKEN_SESSION_KEY, None)
            raise SpotifyAuthRequired("Token expired and no refresh token available")
        try:
            # refresh_access_token writes the new token back through the
            # cache handler, so the session is updated as a side effect.
            token = make_oauth().refresh_access_token(refresh_token)
        except SpotifyException as exc:
            log.warning("Token refresh failed: %s", exc)
            session.pop(TOKEN_SESSION_KEY, None)
            raise SpotifyAuthRequired("Token refresh failed") from exc

    return spotipy.Spotify(
        auth=token["access_token"],
        requests_timeout=current_app.config["SPOTIFY_TIMEOUT"],
    )


def logout() -> None:
    """Drop all Spotify state from the session."""
    session.pop(TOKEN_SESSION_KEY, None)
    session.pop("user", None)
    session.pop("oauth_state", None)


# --------------------------------------------------------------------------
# Caching
# --------------------------------------------------------------------------

# Cache of upstream responses, keyed by (session id, request key).
# Process-local: adequate for a single web dyno, and every entry expires.
_cache: dict[tuple[str, str], tuple[float, Any]] = {}
_MAX_CACHE_ENTRIES = 2000


def _cache_scope() -> str:
    user = session.get("user") or {}
    return str(user.get("id") or "anonymous")


def cached(key: str, producer: Callable[[], Any]) -> Any:
    """Memoise ``producer`` per user for ``CACHE_TTL`` seconds."""
    ttl = current_app.config.get("CACHE_TTL", 0)
    if ttl <= 0:
        return producer()

    scoped = (_cache_scope(), key)
    now = time.monotonic()
    hit = _cache.get(scoped)
    if hit and hit[0] > now:
        return hit[1]

    value = producer()
    if len(_cache) >= _MAX_CACHE_ENTRIES:
        for stale_key, (expires, _) in list(_cache.items()):
            if expires <= now:
                _cache.pop(stale_key, None)
        if len(_cache) >= _MAX_CACHE_ENTRIES:
            _cache.clear()
    _cache[scoped] = (now + ttl, value)
    return value


def clear_cache() -> None:
    """Forget every cached upstream response (used by tests and /refresh)."""
    _cache.clear()


def call(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Invoke a spotipy method, translating errors into our own exceptions."""
    try:
        return fn(*args, **kwargs)
    except SpotifyException as exc:
        if exc.http_status in (401,):
            session.pop(TOKEN_SESSION_KEY, None)
            raise SpotifyAuthRequired("Spotify rejected the access token") from exc
        if exc.http_status == 403:
            raise SpotifyUnavailable(
                "Spotify refused this request. If your app is in development "
                "mode, make sure this account is added to the app's user list.",
                403,
            ) from exc
        if exc.http_status == 429:
            raise SpotifyUnavailable(
                "Spotify is rate limiting this app. Try again in a moment.", 429
            ) from exc
        log.warning("Spotify API error %s: %s", exc.http_status, exc.msg)
        raise SpotifyUnavailable("Spotify returned an error.", exc.http_status) from exc
    except Exception as exc:  # network failure, timeout, malformed payload
        log.warning("Spotify request failed: %s", exc)
        raise SpotifyUnavailable("Could not reach Spotify. Try again shortly.") from exc
