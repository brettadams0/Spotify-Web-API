"""Small JSON API used by the front end for polling and playlist export."""
from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from .. import data
from .. import spotify as sp_service
from ..spotify import TIME_RANGES, normalise_time_range

bp = Blueprint("api", __name__, url_prefix="/api")

MAX_PLAYLIST_TRACKS = 100
MAX_PLAYLIST_NAME = 100


def _require_auth():
    """Return a 401 response when the caller is not signed in, else None."""
    if not sp_service.is_authenticated():
        return jsonify({"error": "not_authenticated"}), 401
    return None


@bp.get("/now-playing")
def now_playing():
    """What the user is listening to right now, polled by the header widget."""
    guard = _require_auth()
    if guard:
        return guard
    track = data.get_now_playing()
    if not track:
        return jsonify({"playing": False})
    return jsonify(
        {
            "playing": track["is_playing"],
            "name": track["name"],
            "artist": track["artist_label"],
            "album": track["album"],
            "image": track["image"],
            "url": track["url"],
            "progress_ms": track["progress_ms"],
            "duration_ms": track["duration_ms"],
        }
    )


@bp.get("/top/<kind>")
def top(kind: str):
    """Top artists, tracks, or genres as JSON.

    The front end uses this to compare a chart against the snapshot it stored
    on your last visit, which is what powers the movement arrows.
    """
    guard = _require_auth()
    if guard:
        return guard
    if kind not in {"artists", "tracks", "genres"}:
        return jsonify({"error": "unknown_kind"}), 404

    time_range = normalise_time_range(request.args.get("range"))
    if kind == "artists":
        items = [
            {"id": a["id"], "rank": a["rank"], "name": a["name"]}
            for a in data.get_top_artists(time_range)
        ]
    elif kind == "tracks":
        items = [
            {"id": t["id"], "rank": t["rank"], "name": t["name"]}
            for t in data.get_top_tracks(time_range)
        ]
    else:
        items = [
            {"id": g["name"], "rank": g["rank"], "name": g["name"]}
            for g in data.get_top_genres(time_range)
        ]

    return jsonify({"kind": kind, "range": time_range, "items": items})


@bp.post("/playlist")
def create_playlist():
    """Save the current top-tracks chart to the user's account as a playlist."""
    guard = _require_auth()
    if guard:
        return guard

    payload = request.get_json(silent=True) or {}
    time_range = normalise_time_range(payload.get("range"))
    try:
        limit = int(payload.get("limit", 50))
    except (TypeError, ValueError):
        limit = 50
    limit = max(1, min(limit, MAX_PLAYLIST_TRACKS))

    tracks = data.get_top_tracks(time_range, limit=limit)
    uris = [t["uri"] for t in tracks if t.get("uri")]
    if not uris:
        return jsonify({"error": "no_tracks"}), 400

    label = TIME_RANGES[time_range].lower()
    stamp = datetime.now(timezone.utc).strftime("%b %Y")
    name = (payload.get("name") or f"My Top {len(uris)} · {stamp}")[:MAX_PLAYLIST_NAME]
    description = f"My top {len(uris)} tracks ({label}), captured with Spotify Stats."

    result = data.create_playlist_from_tracks(
        name=name,
        track_uris=uris,
        description=description,
        public=bool(payload.get("public", False)),
    )
    return jsonify(result), 201
