"""Tests for the JSON API."""
from __future__ import annotations

import pytest


class TestAuthGuard:
    @pytest.mark.parametrize("path", ["/api/now-playing", "/api/top/tracks"])
    def test_signed_out_calls_get_a_401(self, client, path):
        response = client.get(path)
        assert response.status_code == 401
        assert response.get_json()["error"] == "not_authenticated"

    def test_playlist_creation_requires_a_session(self, client):
        assert client.post("/api/playlist", json={}).status_code == 401


class TestNowPlaying:
    def test_reports_idle_playback(self, signed_in):
        body = signed_in.get("/api/now-playing").get_json()
        assert body == {"playing": False}

    def test_reports_the_current_track(self, signed_in, fake_spotify):
        from tests.conftest import make_track

        fake_spotify._playing = {
            "is_playing": True,
            "progress_ms": 42000,
            "item": make_track(7),
        }
        body = signed_in.get("/api/now-playing").get_json()
        assert body["playing"] is True
        assert body["name"] == "Track 7"
        assert body["progress_ms"] == 42000

    def test_treats_a_204_from_spotify_as_idle(self, signed_in, fake_spotify):
        fake_spotify._playing = None
        assert signed_in.get("/api/now-playing").get_json()["playing"] is False


class TestTopEndpoint:
    @pytest.mark.parametrize("kind", ["artists", "tracks", "genres"])
    def test_each_chart_kind_returns_ranked_items(self, signed_in, kind):
        body = signed_in.get(f"/api/top/{kind}").get_json()
        assert body["kind"] == kind
        assert body["range"] == "medium_term"
        assert body["items"][0]["rank"] == 1
        assert all("id" in item for item in body["items"])

    def test_an_unknown_chart_kind_is_a_404(self, signed_in):
        assert signed_in.get("/api/top/albums").status_code == 404

    def test_the_range_parameter_is_validated(self, signed_in):
        body = signed_in.get("/api/top/tracks?range=bogus").get_json()
        assert body["range"] == "medium_term"


class TestPlaylistExport:
    def test_creates_a_playlist_and_fills_it(self, signed_in, fake_spotify):
        response = signed_in.post("/api/playlist", json={"range": "short_term"})
        assert response.status_code == 201
        body = response.get_json()
        assert body["track_count"] == 25
        assert body["url"].startswith("https://open.spotify.com/playlist/")

        assert len(fake_spotify.created_playlists) == 1
        created = fake_spotify.created_playlists[0]
        assert created["user"] == "listener1"
        assert created["public"] is False
        assert "last 4 weeks" in created["description"]

        playlist_id, uris = fake_spotify.added_items[0]
        assert playlist_id == "newpl"
        assert uris[0] == "spotify:track:track1"

    def test_honours_a_custom_name(self, signed_in, fake_spotify):
        signed_in.post("/api/playlist", json={"name": "My mixtape"})
        assert fake_spotify.created_playlists[0]["name"] == "My mixtape"

    def test_clamps_an_absurd_limit(self, signed_in, fake_spotify):
        response = signed_in.post("/api/playlist", json={"limit": 100000})
        # The fake account only has 25 tracks, so that is the ceiling here.
        assert response.get_json()["track_count"] == 25

    @pytest.mark.parametrize("limit", ["abc", None, -4])
    def test_survives_a_nonsense_limit(self, signed_in, limit):
        response = signed_in.post("/api/playlist", json={"limit": limit})
        assert response.status_code == 201

    def test_a_long_name_is_truncated(self, signed_in, fake_spotify):
        signed_in.post("/api/playlist", json={"name": "x" * 400})
        assert len(fake_spotify.created_playlists[0]["name"]) == 100

    def test_batches_uris_in_groups_of_100(self, signed_in, fake_spotify):
        from tests.conftest import make_track

        fake_spotify._tracks = [make_track(i) for i in range(1, 121)]
        response = signed_in.post("/api/playlist", json={"limit": 100})
        assert response.get_json()["track_count"] == 100
        assert len(fake_spotify.added_items) == 1
        assert len(fake_spotify.added_items[0][1]) == 100

    def test_an_empty_chart_is_rejected(self, signed_in, fake_spotify):
        fake_spotify._tracks = []
        response = signed_in.post("/api/playlist", json={})
        assert response.status_code == 400
        assert response.get_json()["error"] == "no_tracks"
