"""Fetch-and-shape helpers that the view functions call.

Each function pulls from Spotify through the cache in ``spotify.cached`` and
returns plain dictionaries and lists ready for a template or a JSON response.
"""
from __future__ import annotations

from typing import Any

from . import spotify as sp_service
from .shaping import (
    aggregate_genres,
    shape_artist,
    shape_playlist,
    shape_profile,
    shape_recent,
    shape_track,
    taste_profile,
)

#: Spotify caps top-items requests at 50 per page; two pages is plenty.
TOP_LIMIT = 50


def _paged_top(client: Any, method_name: str, time_range: str, limit: int) -> list[dict]:
    """Read up to ``limit`` top items, following Spotify's 50-per-page cap."""
    method = getattr(client, method_name)
    items: list[dict] = []
    offset = 0
    while len(items) < limit:
        page_size = min(50, limit - len(items))
        page = sp_service.call(
            method, limit=page_size, offset=offset, time_range=time_range
        )
        batch = (page or {}).get("items") or []
        items.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return items[:limit]


def get_profile() -> dict[str, Any]:
    """The signed-in user's profile."""
    client = sp_service.get_client()
    raw = sp_service.cached("profile", lambda: sp_service.call(client.current_user))
    return shape_profile(raw or {})


def get_top_artists(time_range: str, limit: int = TOP_LIMIT) -> list[dict[str, Any]]:
    """Top artists for a time range, ranked from 1."""
    client = sp_service.get_client()
    raw = sp_service.cached(
        f"top_artists:{time_range}:{limit}",
        lambda: _paged_top(client, "current_user_top_artists", time_range, limit),
    )
    return [shape_artist(a, rank) for rank, a in enumerate(raw, start=1)]


def get_top_tracks(time_range: str, limit: int = TOP_LIMIT) -> list[dict[str, Any]]:
    """Top tracks for a time range, ranked from 1."""
    client = sp_service.get_client()
    raw = sp_service.cached(
        f"top_tracks:{time_range}:{limit}",
        lambda: _paged_top(client, "current_user_top_tracks", time_range, limit),
    )
    return [shape_track(t, rank) for rank, t in enumerate(raw, start=1)]


def get_top_genres(time_range: str, limit: int = 25) -> list[dict[str, Any]]:
    """Genres ranked across the user's top artists for a time range."""
    return aggregate_genres(get_top_artists(time_range), limit=limit)


def get_recently_played(limit: int = 50) -> list[dict[str, Any]]:
    """The most recent plays, newest first, each with a timestamp."""
    client = sp_service.get_client()
    raw = sp_service.cached(
        f"recent:{limit}",
        lambda: sp_service.call(client.current_user_recently_played, limit=limit),
    )
    items = (raw or {}).get("items") or []
    shaped = [shape_recent(item) for item in items]
    return [item for item in shaped if item]


def get_playlists(limit: int = 50) -> list[dict[str, Any]]:
    """The user's playlists."""
    client = sp_service.get_client()
    raw = sp_service.cached(
        f"playlists:{limit}",
        lambda: sp_service.call(client.current_user_playlists, limit=limit),
    )
    return [shape_playlist(p) for p in ((raw or {}).get("items") or [])]


def get_now_playing() -> dict[str, Any] | None:
    """The currently playing track, or None when nothing is playing.

    Spotify answers with 204 No Content when playback is idle, which spotipy
    surfaces as None.
    """
    client = sp_service.get_client()
    raw = sp_service.call(client.current_user_playing_track)
    if not raw or not raw.get("item"):
        return None
    track = shape_track(raw["item"])
    track["is_playing"] = bool(raw.get("is_playing"))
    track["progress_ms"] = raw.get("progress_ms") or 0
    return track


def get_following_count() -> int | None:
    """How many artists the user follows, or None if Spotify withheld it."""
    client = sp_service.get_client()
    raw = sp_service.cached(
        "following",
        lambda: sp_service.call(client.current_user_followed_artists, limit=1),
    )
    return ((raw or {}).get("artists") or {}).get("total")


def get_overview(time_range: str) -> dict[str, Any]:
    """Everything the dashboard needs, in one call."""
    artists = get_top_artists(time_range)
    tracks = get_top_tracks(time_range)
    return {
        "profile": get_profile(),
        "artists": artists,
        "tracks": tracks,
        "genres": aggregate_genres(artists, limit=8),
        "stats": taste_profile(tracks, artists),
    }


def create_playlist_from_tracks(
    name: str, track_uris: list[str], description: str, public: bool = False
) -> dict[str, Any]:
    """Create a playlist on the user's account and fill it with ``track_uris``."""
    client = sp_service.get_client()
    profile = get_profile()
    playlist = sp_service.call(
        client.user_playlist_create,
        user=profile["id"],
        name=name,
        public=public,
        description=description,
    )
    # add_items accepts 100 URIs per request.
    for start in range(0, len(track_uris), 100):
        sp_service.call(
            client.playlist_add_items, playlist["id"], track_uris[start : start + 100]
        )
    return {
        "id": playlist.get("id"),
        "name": playlist.get("name"),
        "url": (playlist.get("external_urls") or {}).get("spotify"),
        "track_count": len(track_uris),
    }
