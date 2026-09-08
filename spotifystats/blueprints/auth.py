"""Spotify OAuth authorization-code flow."""
from __future__ import annotations

import logging
import secrets

from flask import (
    Blueprint,
    flash,
    redirect,
    request,
    session,
    url_for,
)

from .. import spotify as sp_service

log = logging.getLogger(__name__)

bp = Blueprint("auth", __name__)


@bp.route("/login")
def login():
    """Send the visitor to Spotify's consent screen."""
    if not sp_service.credentials_configured():
        flash(
            "This deployment has no Spotify credentials configured. "
            "Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET.",
            "error",
        )
        return redirect(url_for("pages.index"))

    # A random state parameter, checked on the way back, blocks CSRF against
    # the callback endpoint.
    state = secrets.token_urlsafe(24)
    session["oauth_state"] = state
    return redirect(sp_service.make_oauth(state=state).get_authorize_url())


@bp.route("/callback")
def callback():
    """Exchange the authorization code for tokens and start the session."""
    error = request.args.get("error")
    if error:
        flash(f"Spotify sign-in was cancelled ({error}).", "error")
        return redirect(url_for("pages.index"))

    expected_state = session.pop("oauth_state", None)
    received_state = request.args.get("state")
    if not expected_state or received_state != expected_state:
        flash("Sign-in could not be verified. Please try again.", "error")
        return redirect(url_for("pages.index"))

    code = request.args.get("code")
    if not code:
        flash("Spotify did not return an authorization code.", "error")
        return redirect(url_for("pages.index"))

    try:
        # as_dict=False returns the access token string; the full token dict is
        # written to the session by the cache handler as a side effect.
        oauth = sp_service.make_oauth(state=expected_state)
        oauth.get_access_token(code, as_dict=False, check_cache=False)
    except Exception as exc:  # spotipy raises several unrelated types here
        log.warning("Token exchange failed: %s", exc)
        flash("Could not complete sign-in with Spotify. Please try again.", "error")
        return redirect(url_for("pages.index"))

    session.permanent = True
    sp_service.clear_cache()

    try:
        session["user"] = {"id": sp_service.get_client().current_user().get("id")}
    except Exception:  # a missing profile is not worth failing the login over
        log.debug("Could not pre-load profile after login", exc_info=True)

    return redirect(url_for("pages.dashboard"))


@bp.route("/logout", methods=["GET", "POST"])
def logout():
    """Clear the session and return to the landing page."""
    sp_service.logout()
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("pages.index"))
