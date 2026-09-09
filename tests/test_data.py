"""Tests for the fetch-and-shape layer, including paging and caching."""
from __future__ import annotations

import time

import pytest

from spotifystats import data
from spotifystats import spotify as sp_service
from tests.conftest import FakeSpotify, make_artist, make_track


@pytest.fixture
def ctx(app, monkeypatch):
    """A request context with a signed-in session and a fake Spotify client."""
    fake = FakeSpotify()
    monkeypatch.setattr(sp_service, "get_client", lambda: fake)
    with app.test_request_context("/"):
        from flask import session

        session["token_info"] = {
            "access_token": "t",
            "refresh_token": "r",
            "expires_at": int(time.time()) + 3600,
        }
        session["user"] = {"id": "listener1"}
        yield fake


class TestPaging:
    def test_requests_more_than_50_items_across_pages(self, app, monkeypatch):
        calls: list[tuple[int, int]] = []
        tracks = [make_track(i) for i in range(1, 121)]

        class PagingSpotify(FakeSpotify):
            def current_user_top_tracks(self, limit=20, offset=0, time_range="medium_term"):
                calls.append((limit, offset))
                return {"items": tracks[offset : offset + limit]}

        fake = PagingSpotify(tracks=tracks)
        monkeypatch.setattr(sp_service, "get_client", lambda: fake)

        with app.test_request_context("/"):
            result = data.get_top_tracks("medium_term", limit=100)

        assert len(result) == 100
        assert calls == [(50, 0), (50, 50)]
        assert result[0]["rank"] == 1
        assert result[-1]["rank"] == 100

    def test_stops_early_when_spotify_runs_out(self, app, monkeypatch):
        fake = FakeSpotify(tracks=[make_track(i) for i in range(1, 8)])
        monkeypatch.setattr(sp_service, "get_client", lambda: fake)
        with app.test_request_context("/"):
            assert len(data.get_top_tracks("short_term", limit=50)) == 7


class TestCaching:
    def test_repeat_reads_hit_the_cache(self, app, monkeypatch):
        app.config["CACHE_TTL"] = 60
        sp_service.clear_cache()
        calls = {"n": 0}

        class CountingSpotify(FakeSpotify):
            def current_user_top_artists(self, limit=20, offset=0, time_range="medium_term"):
                calls["n"] += 1
                return super().current_user_top_artists(limit, offset, time_range)

        fake = CountingSpotify()
        monkeypatch.setattr(sp_service, "get_client", lambda: fake)

        with app.test_request_context("/"):
            from flask import session

            session["user"] = {"id": "listener1"}
            data.get_top_artists("medium_term")
            data.get_top_artists("medium_term")
            assert calls["n"] == 1

            # A different time range is a different cache key.
            data.get_top_artists("short_term")
            assert calls["n"] == 2

        sp_service.clear_cache()

    def test_caches_are_scoped_per_user(self, app, monkeypatch):
        app.config["CACHE_TTL"] = 60
        sp_service.clear_cache()
        calls = {"n": 0}

        class CountingSpotify(FakeSpotify):
            def current_user_top_artists(self, limit=20, offset=0, time_range="medium_term"):
                calls["n"] += 1
                return super().current_user_top_artists(limit, offset, time_range)

        monkeypatch.setattr(sp_service, "get_client", lambda: CountingSpotify())

        for user_id in ("alice", "bob"):
            with app.test_request_context("/"):
                from flask import session

                session["user"] = {"id": user_id}
                data.get_top_artists("medium_term")

        assert calls["n"] == 2
        sp_service.clear_cache()

    def test_a_zero_ttl_disables_caching(self, app, monkeypatch):
        app.config["CACHE_TTL"] = 0
        calls = {"n": 0}

        class CountingSpotify(FakeSpotify):
            def current_user_top_artists(self, limit=20, offset=0, time_range="medium_term"):
                calls["n"] += 1
                return super().current_user_top_artists(limit, offset, time_range)

        monkeypatch.setattr(sp_service, "get_client", lambda: CountingSpotify())
        with app.test_request_context("/"):
            data.get_top_artists("medium_term")
            data.get_top_artists("medium_term")
        assert calls["n"] == 2


class TestShapedResults:
    def test_overview_bundles_everything_the_dashboard_needs(self, ctx):
        overview = data.get_overview("medium_term")
        assert overview["profile"]["name"] == "Test Listener"
        assert len(overview["artists"]) == 25
        assert len(overview["tracks"]) == 25
        assert len(overview["genres"]) <= 8
        assert overview["stats"]["track_count"] == 25

    def test_recently_played_drops_malformed_entries(self, app, monkeypatch):
        fake = FakeSpotify(
            recent=[
                {"track": make_track(1), "played_at": "2026-09-08T10:00:00Z"},
                {"played_at": "2026-09-08T09:00:00Z"},  # no track
            ]
        )
        monkeypatch.setattr(sp_service, "get_client", lambda: fake)
        with app.test_request_context("/"):
            plays = data.get_recently_played()
        assert len(plays) == 1
        assert plays[0]["name"] == "Track 1"

    def test_now_playing_is_none_when_idle(self, ctx):
        assert data.get_now_playing() is None

    def test_genres_come_from_the_artist_chart(self, app, monkeypatch):
        fake = FakeSpotify(
            artists=[
                make_artist(1, ["jazz"]),
                make_artist(2, ["jazz", "soul"]),
                make_artist(3, ["soul"]),
            ]
        )
        monkeypatch.setattr(sp_service, "get_client", lambda: fake)
        with app.test_request_context("/"):
            genres = data.get_top_genres("long_term")
        assert [g["name"] for g in genres] == ["jazz", "soul"]

    def test_playlist_creation_batches_over_100_uris(self, app, monkeypatch):
        fake = FakeSpotify()
        monkeypatch.setattr(sp_service, "get_client", lambda: fake)
        uris = [f"spotify:track:t{i}" for i in range(250)]
        with app.test_request_context("/"):
            result = data.create_playlist_from_tracks("Big", uris, "desc")
        assert result["track_count"] == 250
        assert [len(batch) for _, batch in fake.added_items] == [100, 100, 50]
