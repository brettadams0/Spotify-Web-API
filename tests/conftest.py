"""Shared fixtures: an app instance and a stand-in for the Spotify API."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from spotifystats import create_app  # noqa: E402
from spotifystats.config import TestConfig  # noqa: E402
from spotifystats import spotify as sp_service  # noqa: E402


def make_artist(index: int, genres: list[str] | None = None) -> dict:
    return {
        "id": f"artist{index}",
        "name": f"Artist {index}",
        "genres": genres if genres is not None else ["indie rock", "dream pop"],
        "popularity": 70 - index,
        "followers": {"total": 100000 - index * 1000},
        "images": [
            {"url": f"https://i.scdn.co/a{index}-640.jpg", "width": 640, "height": 640},
            {"url": f"https://i.scdn.co/a{index}-160.jpg", "width": 160, "height": 160},
        ],
        "external_urls": {"spotify": f"https://open.spotify.com/artist/artist{index}"},
        "uri": f"spotify:artist:artist{index}",
    }


def make_track(index: int) -> dict:
    return {
        "id": f"track{index}",
        "name": f"Track {index}",
        "duration_ms": 180000 + index * 1000,
        "popularity": 60 - index,
        "explicit": index % 3 == 0,
        "artists": [{"id": "artist1", "name": f"Artist {index}"}],
        "album": {
            "name": f"Album {index}",
            "release_date": f"{2010 + (index % 10)}-05-01",
            "images": [
                {"url": f"https://i.scdn.co/t{index}-640.jpg", "width": 640, "height": 640},
                {"url": f"https://i.scdn.co/t{index}-300.jpg", "width": 300, "height": 300},
            ],
        },
        "external_urls": {"spotify": f"https://open.spotify.com/track/track{index}"},
        "uri": f"spotify:track:track{index}",
    }


class FakeSpotify:
    """Minimal stand-in for spotipy.Spotify covering the calls the app makes."""

    def __init__(self, *, artists=None, tracks=None, playing=None, recent=None):
        self._artists = artists if artists is not None else [make_artist(i) for i in range(1, 26)]
        self._tracks = tracks if tracks is not None else [make_track(i) for i in range(1, 26)]
        self._playing = playing
        self._recent = recent
        self.created_playlists: list[dict] = []
        self.added_items: list[tuple[str, list[str]]] = []

    def current_user(self):
        return {
            "id": "listener1",
            "display_name": "Test Listener",
            "email": "listener@example.com",
            "country": "US",
            "product": "premium",
            "followers": {"total": 42},
            "images": [{"url": "https://i.scdn.co/u-300.jpg", "width": 300, "height": 300}],
            "external_urls": {"spotify": "https://open.spotify.com/user/listener1"},
        }

    def _page(self, source, limit, offset):
        return {"items": source[offset : offset + limit]}

    def current_user_top_artists(self, limit=20, offset=0, time_range="medium_term"):
        return self._page(self._artists, limit, offset)

    def current_user_top_tracks(self, limit=20, offset=0, time_range="medium_term"):
        return self._page(self._tracks, limit, offset)

    def current_user_recently_played(self, limit=50):
        if self._recent is not None:
            return {"items": self._recent}
        return {
            "items": [
                {"track": make_track(i), "played_at": f"2026-09-0{i}T10:15:00.000Z"}
                for i in range(1, 6)
            ]
        }

    def current_user_playlists(self, limit=50):
        return {
            "items": [
                {
                    "id": f"pl{i}",
                    "name": f"Playlist {i}",
                    "description": "",
                    "public": i % 2 == 0,
                    "collaborative": False,
                    "tracks": {"total": i * 10},
                    "owner": {"id": "listener1", "display_name": "Test Listener"},
                    "images": [{"url": f"https://i.scdn.co/p{i}.jpg", "width": 300}],
                    "external_urls": {"spotify": f"https://open.spotify.com/playlist/pl{i}"},
                }
                for i in range(1, 4)
            ]
        }

    def current_user_playing_track(self):
        return self._playing

    def current_user_followed_artists(self, limit=1):
        return {"artists": {"total": 137}}

    def user_playlist_create(self, user, name, public=False, description=""):
        playlist = {
            "id": "newpl",
            "name": name,
            "external_urls": {"spotify": "https://open.spotify.com/playlist/newpl"},
        }
        self.created_playlists.append(
            {"user": user, "name": name, "public": public, "description": description}
        )
        return playlist

    def playlist_add_items(self, playlist_id, items):
        self.added_items.append((playlist_id, list(items)))
        return {"snapshot_id": "snap"}


@pytest.fixture
def app():
    application = create_app(TestConfig)
    sp_service.clear_cache()
    yield application
    sp_service.clear_cache()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def fake_spotify(monkeypatch):
    """Install a FakeSpotify as the client every request receives."""
    instance = FakeSpotify()
    monkeypatch.setattr(sp_service, "get_client", lambda: instance)
    monkeypatch.setattr("spotifystats.data.sp_service.get_client", lambda: instance)
    return instance


@pytest.fixture
def signed_in(client, fake_spotify):
    """A client with a valid-looking token in its session."""
    with client.session_transaction() as session:
        session["token_info"] = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "expires_at": int(time.time()) + 3600,
            "scope": "user-top-read",
        }
        session["user"] = {"id": "listener1"}
    return client
