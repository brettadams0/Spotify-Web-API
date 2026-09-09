"""HTML pages: the landing screen and the six signed-in views."""
from __future__ import annotations

from functools import wraps

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from .. import data
from .. import spotify as sp_service
from ..spotify import TIME_RANGES, normalise_time_range

bp = Blueprint("pages", __name__)


def login_required(view):
    """Bounce signed-out visitors to the landing page."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if not sp_service.is_authenticated():
            return redirect(url_for("pages.index", next=request.path))
        return view(*args, **kwargs)

    return wrapper


@bp.app_context_processor
def inject_globals():
    """Values every template needs."""
    return {
        "time_ranges": TIME_RANGES,
        "signed_in": sp_service.is_authenticated(),
        "credentials_configured": sp_service.credentials_configured(),
        "current_endpoint": request.endpoint,
    }


def _range_from_query() -> str:
    return normalise_time_range(request.args.get("range"))


@bp.route("/")
def index():
    """Landing page, or straight to the dashboard when already signed in."""
    if sp_service.is_authenticated():
        return redirect(url_for("pages.dashboard"))
    return render_template("index.html")


@bp.route("/dashboard")
@login_required
def dashboard():
    """Overview: profile, headline numbers, and the top of each chart."""
    time_range = _range_from_query()
    overview = data.get_overview(time_range)
    return render_template(
        "dashboard.html",
        time_range=time_range,
        profile=overview["profile"],
        stats=overview["stats"],
        artists=overview["artists"][:10],
        tracks=overview["tracks"][:10],
        artist_total=len(overview["artists"]),
        track_total=len(overview["tracks"]),
        genres=overview["genres"],
    )


@bp.route("/artists")
@login_required
def artists():
    """Full top-artists chart."""
    time_range = _range_from_query()
    return render_template(
        "artists.html",
        time_range=time_range,
        artists=data.get_top_artists(time_range),
    )


@bp.route("/tracks")
@login_required
def tracks():
    """Full top-tracks chart, with playlist export."""
    time_range = _range_from_query()
    tracks = data.get_top_tracks(time_range)
    explicit = (
        round(sum(1 for t in tracks if t["explicit"]) / len(tracks) * 100)
        if tracks
        else 0
    )
    return render_template(
        "tracks.html",
        time_range=time_range,
        tracks=tracks,
        explicit_share=explicit,
    )


@bp.route("/genres")
@login_required
def genres():
    """Genres ranked across the user's top artists."""
    time_range = _range_from_query()
    return render_template(
        "genres.html",
        time_range=time_range,
        genres=data.get_top_genres(time_range),
    )


@bp.route("/recent")
@login_required
def recent():
    """Recently played tracks with timestamps."""
    return render_template("recent.html", plays=data.get_recently_played())


@bp.route("/playlists")
@login_required
def playlists():
    """The user's own playlists."""
    return render_template("playlists.html", playlists=data.get_playlists())


@bp.route("/refresh")
@login_required
def refresh():
    """Drop cached Spotify responses and return to the page you came from."""
    sp_service.clear_cache()
    flash("Stats refreshed from Spotify.", "success")
    target = request.args.get("next", "")
    # Only follow same-origin relative paths, never an absolute URL.
    if target.startswith("/") and not target.startswith("//"):
        return redirect(target)
    return redirect(url_for("pages.dashboard"))
