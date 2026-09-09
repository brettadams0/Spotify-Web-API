"""Spotify Stats — a Flask app for exploring your own listening history."""
from __future__ import annotations

import logging
import os

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

from . import performance
from .config import Config
from .spotify import SpotifyAuthRequired, SpotifyUnavailable

__version__ = "2.0.0"


def _wants_json() -> bool:
    """True when the caller is the JSON API or an XHR."""
    return request.path.startswith("/api/") or (
        request.accept_mimetypes["application/json"]
        > request.accept_mimetypes["text/html"]
    )


def create_app(config_object: type[Config] | None = None) -> Flask:
    """Build and configure the application."""
    app = Flask(
        __name__,
        template_folder=os.path.join(os.pardir, "templates"),
        static_folder=os.path.join(os.pardir, "static"),
    )
    app.config.from_object(config_object or Config)

    logging.basicConfig(
        level=logging.DEBUG if app.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    from .blueprints import api, auth, pages

    app.register_blueprint(pages.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(api.bp)

    performance.register(app)
    _register_error_handlers(app)
    _register_security_headers(app)
    _register_template_filters(app)

    @app.route("/healthz")
    def healthz():
        """Liveness probe for the hosting platform."""
        return jsonify({"status": "ok", "version": __version__})

    @app.route("/sw.js")
    def service_worker():
        """Serve the worker from the root so its scope covers the whole app."""
        response = app.send_static_file("sw.js")
        response.headers["Content-Type"] = "text/javascript"
        response.headers["Service-Worker-Allowed"] = "/"
        response.headers["Cache-Control"] = "no-cache"
        return response

    @app.route("/offline")
    def offline():
        """Cached by the service worker and shown when the network is gone."""
        return render_template(
            "error.html",
            code="Offline",
            message=(
                "You are offline. Spotify Stats needs a connection to read "
                "your listening data."
            ),
        )

    return app


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(SpotifyAuthRequired)
    def _auth_required(_exc: SpotifyAuthRequired):
        if _wants_json():
            return jsonify({"error": "not_authenticated"}), 401
        flash("Your Spotify session expired. Please sign in again.", "error")
        return redirect(url_for("pages.index"))

    @app.errorhandler(SpotifyUnavailable)
    def _spotify_unavailable(exc: SpotifyUnavailable):
        message = str(exc)
        if _wants_json():
            return jsonify({"error": "spotify_unavailable", "detail": message}), 502
        return (
            render_template("error.html", code="Spotify hiccup", message=message),
            502,
        )

    @app.errorhandler(404)
    def _not_found(_exc):
        if _wants_json():
            return jsonify({"error": "not_found"}), 404
        return (
            render_template(
                "error.html",
                code="404",
                message="That page does not exist.",
            ),
            404,
        )

    @app.errorhandler(500)
    def _server_error(exc):
        app.logger.exception("Unhandled error: %s", exc)
        if _wants_json():
            return jsonify({"error": "server_error"}), 500
        return (
            render_template(
                "error.html",
                code="500",
                message="Something went wrong on our side.",
            ),
            500,
        )


def _register_security_headers(app: Flask) -> None:
    @app.after_request
    def _headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            # Album art, artist photos and avatars are served from Spotify's
            # CDNs; a Facebook-linked avatar comes from platform-lookaside.
            "img-src 'self' https://*.scdn.co https://*.spotifycdn.com "
            "https://platform-lookaside.fbsbx.com data:; "
            # Inline style attributes drive the genre bar widths; inline
            # scripts stay blocked.
            "style-src 'self' 'unsafe-inline'; script-src 'self'; "
            "connect-src 'self'; frame-ancestors 'none'; "
            "form-action 'self' https://accounts.spotify.com; base-uri 'self'",
        )
        return response


def _register_template_filters(app: Flask) -> None:
    from .shaping import format_number

    app.jinja_env.filters["number"] = format_number
