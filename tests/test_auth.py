"""Tests for the OAuth flow and Spotify error translation."""
from __future__ import annotations

import time

import pytest
from spotipy.exceptions import SpotifyException

from spotifystats import spotify as sp_service
from spotifystats.config import Config, TestConfig
from spotifystats.spotify import SpotifyAuthRequired, SpotifyUnavailable


class TestLogin:
    def test_login_redirects_to_spotify_and_stores_state(self, client):
        response = client.get("/login")
        assert response.status_code == 302
        assert response.headers["Location"].startswith(
            "https://accounts.spotify.com/authorize"
        )
        with client.session_transaction() as session:
            assert session["oauth_state"]

    def test_the_state_parameter_is_in_the_authorize_url(self, client):
        client.get("/login")
        with client.session_transaction() as session:
            state = session["oauth_state"]
        response = client.get("/login")
        # A fresh state is minted per attempt, so it must differ.
        with client.session_transaction() as session:
            assert session["oauth_state"] != state
        assert "state=" in response.headers["Location"]

    def test_login_is_blocked_without_configured_credentials(self, app):
        app.config["SPOTIFY_CLIENT_ID"] = ""
        app.config["SPOTIFY_CLIENT_SECRET"] = ""
        response = app.test_client().get("/login", follow_redirects=True)
        assert b"no Spotify credentials configured" in response.data


class TestCallback:
    def test_a_mismatched_state_is_rejected(self, client):
        with client.session_transaction() as session:
            session["oauth_state"] = "expected"
        response = client.get("/callback?code=abc&state=attacker", follow_redirects=True)
        assert b"could not be verified" in response.data
        with client.session_transaction() as session:
            assert "token_info" not in session

    def test_a_missing_state_is_rejected(self, client):
        response = client.get("/callback?code=abc&state=whatever", follow_redirects=True)
        assert b"could not be verified" in response.data

    def test_a_missing_code_is_rejected(self, client):
        with client.session_transaction() as session:
            session["oauth_state"] = "s"
        response = client.get("/callback?state=s", follow_redirects=True)
        assert b"did not return an authorization code" in response.data

    def test_a_denied_consent_screen_is_reported(self, client):
        response = client.get("/callback?error=access_denied", follow_redirects=True)
        assert b"cancelled" in response.data

    def test_a_failed_token_exchange_is_reported(self, client, monkeypatch):
        class BrokenOAuth:
            def get_access_token(self, *args, **kwargs):
                raise RuntimeError("token endpoint down")

        monkeypatch.setattr(sp_service, "make_oauth", lambda state=None: BrokenOAuth())
        with client.session_transaction() as session:
            session["oauth_state"] = "s"
        response = client.get("/callback?code=abc&state=s", follow_redirects=True)
        assert b"Could not complete sign-in" in response.data

    def test_a_successful_exchange_lands_on_the_dashboard(self, client, monkeypatch):
        token = {
            "access_token": "fresh",
            "refresh_token": "r",
            "expires_at": int(time.time()) + 3600,
        }

        class WorkingOAuth:
            def get_access_token(self, code, as_dict=True, check_cache=True):
                from flask import session as flask_session

                flask_session["token_info"] = token
                return token["access_token"]

        monkeypatch.setattr(sp_service, "make_oauth", lambda state=None: WorkingOAuth())
        with client.session_transaction() as session:
            session["oauth_state"] = "s"

        response = client.get("/callback?code=abc&state=s")
        assert response.status_code == 302
        assert response.headers["Location"] == "/dashboard"
        with client.session_transaction() as session:
            assert session["token_info"]["access_token"] == "fresh"


class TestLogout:
    def test_logout_clears_the_session(self, signed_in):
        response = signed_in.post("/logout")
        assert response.status_code == 302
        with signed_in.session_transaction() as session:
            assert "token_info" not in session
        assert signed_in.get("/dashboard").status_code == 302


class TestTokenLifecycle:
    def test_a_soon_to_expire_token_is_refreshed(self, app, monkeypatch):
        refreshed = {
            "access_token": "new",
            "refresh_token": "r",
            "expires_at": int(time.time()) + 3600,
        }

        class RefreshingOAuth:
            def refresh_access_token(self, refresh_token):
                assert refresh_token == "r"
                return refreshed

        monkeypatch.setattr(sp_service, "make_oauth", lambda state=None: RefreshingOAuth())

        with app.test_request_context("/"):
            from flask import session

            session["token_info"] = {
                "access_token": "old",
                "refresh_token": "r",
                "expires_at": int(time.time()) + 5,
            }
            client = sp_service.get_client()
            assert client._auth == "new"

    def test_a_failed_refresh_clears_the_session(self, app, monkeypatch):
        class FailingOAuth:
            def refresh_access_token(self, refresh_token):
                raise SpotifyException(400, -1, "invalid_grant")

        monkeypatch.setattr(sp_service, "make_oauth", lambda state=None: FailingOAuth())

        with app.test_request_context("/"):
            from flask import session

            session["token_info"] = {
                "access_token": "old",
                "refresh_token": "r",
                "expires_at": int(time.time()) - 1,
            }
            with pytest.raises(SpotifyAuthRequired):
                sp_service.get_client()
            assert "token_info" not in session

    def test_no_token_raises(self, app):
        with app.test_request_context("/"):
            with pytest.raises(SpotifyAuthRequired):
                sp_service.get_client()


class TestErrorTranslation:
    def _raise(self, status, msg="boom"):
        def failing():
            raise SpotifyException(status, -1, msg)

        return failing


    def test_a_401_clears_the_token(self, app):
        with app.test_request_context("/"):
            from flask import session

            session["token_info"] = {"access_token": "x"}
            with pytest.raises(SpotifyAuthRequired):
                sp_service.call(self._raise(401))
            assert "token_info" not in session

    def test_a_403_explains_development_mode(self, app):
        with app.test_request_context("/"):
            with pytest.raises(SpotifyUnavailable) as exc:
                sp_service.call(self._raise(403))
            assert exc.value.status == 403
            assert "development" in str(exc.value)

    def test_a_429_mentions_rate_limiting(self, app):
        with app.test_request_context("/"):
            with pytest.raises(SpotifyUnavailable) as exc:
                sp_service.call(self._raise(429))
            assert "rate limiting" in str(exc.value)

    def test_a_network_failure_becomes_spotify_unavailable(self, app):
        def offline():
            raise ConnectionError("no route to host")

        with app.test_request_context("/"):
            with pytest.raises(SpotifyUnavailable) as exc:
                sp_service.call(offline)
            assert "Could not reach Spotify" in str(exc.value)

    def test_pages_render_a_friendly_error_when_spotify_fails(
        self, client, monkeypatch
    ):
        def boom():
            raise SpotifyUnavailable("Spotify is having a moment.", 502)

        monkeypatch.setattr("spotifystats.data.get_overview", lambda _range: boom())
        with client.session_transaction() as session:
            session["token_info"] = {
                "access_token": "t",
                "refresh_token": "r",
                "expires_at": int(time.time()) + 3600,
            }
        response = client.get("/dashboard")
        assert response.status_code == 502
        assert b"Spotify is having a moment." in response.data

    def test_the_api_returns_json_when_spotify_fails(self, client, monkeypatch):
        def boom(*args, **kwargs):
            raise SpotifyUnavailable("Spotify is having a moment.", 502)

        monkeypatch.setattr("spotifystats.data.get_now_playing", boom)
        with client.session_transaction() as session:
            session["token_info"] = {
                "access_token": "t",
                "refresh_token": "r",
                "expires_at": int(time.time()) + 3600,
            }
        response = client.get("/api/now-playing")
        assert response.status_code == 502
        assert response.get_json()["error"] == "spotify_unavailable"


class TestConfiguration:
    def test_a_secret_key_is_always_present(self):
        assert Config.SECRET_KEY
        assert TestConfig.SECRET_KEY == "test-secret-key"

    def test_session_cookies_are_locked_down(self, app):
        assert app.config["SESSION_COOKIE_HTTPONLY"] is True
        assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"

    def test_no_credentials_are_committed_in_the_source(self):
        from pathlib import Path

        source = Path("spotifystats/config.py").read_text()
        assert 'SPOTIFY_CLIENT_ID", ""' in source or 'SPOTIFY_CLIENT_ID"' in source
        assert "23b2a82501b04530ba24fa22bac9c3dd" not in source
