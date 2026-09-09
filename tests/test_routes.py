"""End-to-end tests for the HTML pages."""
from __future__ import annotations

import time

import pytest

PROTECTED_PAGES = ["/dashboard", "/artists", "/tracks", "/genres", "/recent", "/playlists"]


class TestPublicPages:
    def test_landing_page_renders_a_login_link(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert b"Log in with Spotify" in response.data
        assert b'href="/login"' in response.data

    def test_health_check(self, client):
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.get_json()["status"] == "ok"

    def test_unknown_page_renders_the_error_template(self, client):
        response = client.get("/does-not-exist")
        assert response.status_code == 404
        assert b"404" in response.data

    def test_service_worker_is_served_from_the_root_scope(self, client):
        response = client.get("/sw.js")
        assert response.status_code == 200
        assert response.headers["Service-Worker-Allowed"] == "/"
        assert "javascript" in response.headers["Content-Type"]

    def test_manifest_is_valid_json(self, client):
        response = client.get("/static/manifest.webmanifest")
        assert response.status_code == 200

    def test_offline_page_renders(self, client):
        response = client.get("/offline")
        assert response.status_code == 200
        assert b"offline" in response.data.lower()

    def test_security_headers_are_present(self, client):
        response = client.get("/")
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "default-src 'self'" in response.headers["Content-Security-Policy"]
        # Inline scripts must stay blocked.
        assert "script-src 'self'" in response.headers["Content-Security-Policy"]


class TestAccessControl:
    @pytest.mark.parametrize("path", PROTECTED_PAGES)
    def test_signed_out_visitors_are_redirected(self, client, path):
        response = client.get(path)
        assert response.status_code == 302
        assert response.headers["Location"].startswith("/")

    def test_landing_page_redirects_when_already_signed_in(self, signed_in):
        response = signed_in.get("/")
        assert response.status_code == 302
        assert response.headers["Location"] == "/dashboard"

    def test_expired_token_without_a_refresh_token_is_not_authenticated(self, client):
        with client.session_transaction() as session:
            session["token_info"] = {
                "access_token": "stale",
                "expires_at": int(time.time()) - 10,
            }
        assert client.get("/dashboard").status_code == 302


class TestSignedInPages:
    def test_dashboard_shows_the_profile_and_charts(self, signed_in):
        response = signed_in.get("/dashboard")
        body = response.get_data(as_text=True)
        assert response.status_code == 200
        assert "Test Listener" in body
        assert "Top artists" in body
        assert "Top tracks" in body
        assert "Artist 1" in body
        assert "Track 1" in body

    def test_artists_page_lists_the_full_chart(self, signed_in):
        body = signed_in.get("/artists").get_data(as_text=True)
        assert "Top artists" in body
        assert "Artist 25" in body
        assert 'data-chart="artists"' in body

    def test_tracks_page_offers_playlist_export(self, signed_in):
        body = signed_in.get("/tracks").get_data(as_text=True)
        assert "Save as playlist" in body
        assert 'id="save-playlist"' in body

    def test_genres_page_ranks_genres(self, signed_in):
        body = signed_in.get("/genres").get_data(as_text=True)
        assert "indie rock" in body
        assert "genre-fill" in body

    def test_recent_page_shows_timestamps(self, signed_in):
        body = signed_in.get("/recent").get_data(as_text=True)
        assert "Recently played" in body
        assert "<time datetime=" in body

    def test_playlists_page_lists_playlists(self, signed_in):
        body = signed_in.get("/playlists").get_data(as_text=True)
        assert "Playlist 1" in body
        assert "10 tracks" in body

    @pytest.mark.parametrize("time_range", ["short_term", "medium_term", "long_term"])
    def test_every_time_range_is_accepted(self, signed_in, time_range):
        response = signed_in.get(f"/tracks?range={time_range}")
        assert response.status_code == 200
        assert f'range={time_range}' in response.get_data(as_text=True)

    def test_an_unknown_time_range_falls_back_to_the_default(self, signed_in):
        response = signed_in.get("/tracks?range=nonsense")
        assert response.status_code == 200
        assert "Last 6 months" in response.get_data(as_text=True)

    def test_every_page_renders_the_navigation(self, signed_in):
        for path in PROTECTED_PAGES:
            body = signed_in.get(path).get_data(as_text=True)
            assert 'class="tabbar"' in body, path
            assert 'href="/recent"' in body, path


class TestRefresh:
    def test_refresh_returns_to_a_relative_next_path(self, signed_in):
        response = signed_in.get("/refresh?next=/tracks")
        assert response.status_code == 302
        assert response.headers["Location"] == "/tracks"

    @pytest.mark.parametrize(
        "target", ["https://evil.example.com", "//evil.example.com", "javascript:alert(1)"]
    )
    def test_refresh_refuses_to_redirect_off_site(self, signed_in, target):
        response = signed_in.get("/refresh", query_string={"next": target})
        assert response.headers["Location"] == "/dashboard"


class TestEmptyStates:
    def test_a_listener_with_no_history_sees_an_empty_state(
        self, client, monkeypatch, fake_spotify
    ):
        fake_spotify._artists = []
        fake_spotify._tracks = []
        with client.session_transaction() as session:
            session["token_info"] = {
                "access_token": "t",
                "refresh_token": "r",
                "expires_at": int(time.time()) + 3600,
            }
        body = client.get("/dashboard").get_data(as_text=True)
        assert "Nothing here yet" in body
