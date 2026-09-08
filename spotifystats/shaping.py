"""Turn raw Spotify payloads into small, template-friendly dictionaries.

Keeping this separate from the HTTP layer means the shaping rules are pure
functions that can be tested without a network or a Flask context.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable


def pick_image(images: Iterable[dict[str, Any]] | None, minimum: int = 160) -> str | None:
    """Return the smallest image at least ``minimum`` px wide, else the largest.

    Spotify orders images widest-first. Picking a modestly sized one keeps
    grids light on mobile without looking soft on a retina display.
    """
    items = [img for img in (images or []) if img and img.get("url")]
    if not items:
        return None
    ordered = sorted(items, key=lambda img: img.get("width") or 0)
    for img in ordered:
        if (img.get("width") or 0) >= minimum:
            return img["url"]
    return ordered[-1]["url"]


def format_duration(ms: int | None) -> str:
    """Render a millisecond duration as m:ss (or h:mm:ss when long)."""
    if not ms or ms < 0:
        return "--:--"
    total = int(ms // 1000)
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def format_number(value: int | None) -> str:
    """Group thousands with commas; blank input becomes a dash."""
    if value is None:
        return "—"
    return f"{value:,}"


def parse_timestamp(raw: str | None) -> datetime | None:
    """Parse an ISO-8601 timestamp from Spotify into an aware datetime."""
    if not raw:
        return None
    text = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def relative_time(moment: datetime | None, *, now: datetime | None = None) -> str:
    """Describe how long ago ``moment`` was, in words."""
    if moment is None:
        return ""
    now = now or datetime.now(timezone.utc)
    seconds = int((now - moment).total_seconds())
    if seconds < 0:
        return "just now"
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hr ago"
    days = hours // 24
    if days == 1:
        return "yesterday"
    if days < 7:
        return f"{days} days ago"
    weeks = days // 7
    if weeks < 5:
        return f"{weeks} wk ago"
    months = days // 30
    if months < 12:
        return f"{months} mo ago"
    return f"{days // 365} yr ago"


def format_exact_time(moment: datetime | None) -> str:
    """Render an absolute UTC timestamp without platform-specific strftime flags."""
    if moment is None:
        return ""
    hour = moment.hour % 12 or 12
    meridiem = "AM" if moment.hour < 12 else "PM"
    return (
        f"{moment.strftime('%b')} {moment.day}, {moment.year} "
        f"at {hour}:{moment.minute:02d} {meridiem} UTC"
    )


def release_year(album: dict[str, Any] | None) -> int | None:
    """Extract a four-digit year from an album's release date."""
    date = (album or {}).get("release_date") or ""
    head = date[:4]
    return int(head) if head.isdigit() else None


def shape_artist(artist: dict[str, Any], rank: int | None = None) -> dict[str, Any]:
    """Reduce a Spotify artist object to what the templates need."""
    return {
        "rank": rank,
        "id": artist.get("id"),
        "name": artist.get("name") or "Unknown artist",
        "image": pick_image(artist.get("images")),
        "genres": artist.get("genres") or [],
        "popularity": artist.get("popularity"),
        "followers": (artist.get("followers") or {}).get("total"),
        "followers_label": format_number((artist.get("followers") or {}).get("total")),
        "url": (artist.get("external_urls") or {}).get("spotify"),
        "uri": artist.get("uri"),
    }


def shape_track(track: dict[str, Any], rank: int | None = None) -> dict[str, Any]:
    """Reduce a Spotify track object to what the templates need."""
    album = track.get("album") or {}
    artists = [a.get("name") for a in (track.get("artists") or []) if a.get("name")]
    return {
        "rank": rank,
        "id": track.get("id"),
        "name": track.get("name") or "Unknown track",
        "artists": artists,
        "artist_label": ", ".join(artists) or "Unknown artist",
        "album": album.get("name"),
        "image": pick_image(album.get("images")),
        "year": release_year(album),
        "duration": format_duration(track.get("duration_ms")),
        "duration_ms": track.get("duration_ms") or 0,
        "popularity": track.get("popularity"),
        "explicit": bool(track.get("explicit")),
        "url": (track.get("external_urls") or {}).get("spotify"),
        "uri": track.get("uri"),
    }


def shape_playlist(playlist: dict[str, Any]) -> dict[str, Any]:
    """Reduce a Spotify playlist object to what the templates need."""
    owner = playlist.get("owner") or {}
    return {
        "id": playlist.get("id"),
        "name": playlist.get("name") or "Untitled playlist",
        "image": pick_image(playlist.get("images")),
        "description": playlist.get("description") or "",
        "track_count": (playlist.get("tracks") or {}).get("total") or 0,
        "owner": owner.get("display_name") or owner.get("id") or "",
        "public": bool(playlist.get("public")),
        "collaborative": bool(playlist.get("collaborative")),
        "url": (playlist.get("external_urls") or {}).get("spotify"),
    }


def shape_recent(item: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any] | None:
    """Shape one entry from the recently-played feed, or None if unusable."""
    track = item.get("track")
    if not track:
        return None
    played_at = parse_timestamp(item.get("played_at"))
    shaped = shape_track(track)
    shaped["played_at"] = played_at
    shaped["played_at_iso"] = played_at.isoformat() if played_at else ""
    shaped["played_label"] = relative_time(played_at, now=now)
    shaped["played_exact"] = format_exact_time(played_at)
    return shaped


def shape_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Reduce the current-user object to what the templates need."""
    return {
        "id": profile.get("id"),
        "name": profile.get("display_name") or profile.get("id") or "Listener",
        "email": profile.get("email"),
        "country": profile.get("country"),
        "product": profile.get("product"),
        "followers": (profile.get("followers") or {}).get("total") or 0,
        "image": pick_image(profile.get("images"), minimum=200),
        "url": (profile.get("external_urls") or {}).get("spotify"),
    }


def aggregate_genres(artists: list[dict[str, Any]], limit: int = 25) -> list[dict[str, Any]]:
    """Rank genres across a list of shaped artists.

    Each genre is scored two ways: how many of your top artists carry it, and
    a rank-weighted score so a genre held by your #1 artist outranks one held
    by your #40. Ordering uses the weighted score; the count is what we show.
    """
    counts: Counter[str] = Counter()
    weights: defaultdict[str, float] = defaultdict(float)
    examples: defaultdict[str, list[str]] = defaultdict(list)
    total = len(artists) or 1

    for index, artist in enumerate(artists):
        weight = (total - index) / total
        for genre in artist.get("genres") or []:
            counts[genre] += 1
            weights[genre] += weight
            if len(examples[genre]) < 3:
                examples[genre].append(artist["name"])

    if not counts:
        return []

    ordered = sorted(counts, key=lambda g: (-weights[g], -counts[g], g))[:limit]
    top_count = max(counts[g] for g in ordered)

    return [
        {
            "rank": position,
            "name": genre,
            "count": counts[genre],
            "share": round(counts[genre] / total * 100),
            "bar": round(counts[genre] / top_count * 100),
            "artists": examples[genre],
        }
        for position, genre in enumerate(ordered, start=1)
    ]


def taste_profile(
    tracks: list[dict[str, Any]], artists: list[dict[str, Any]]
) -> dict[str, Any]:
    """Derive headline numbers from shaped top tracks and artists.

    Everything here comes from fields already present on the track and artist
    objects, so it needs no extra API calls and no deprecated endpoints.
    """
    popularities = [t["popularity"] for t in tracks if t.get("popularity") is not None]
    years = [t["year"] for t in tracks if t.get("year")]
    durations = [t["duration_ms"] for t in tracks if t.get("duration_ms")]
    genres = {g for a in artists for g in (a.get("genres") or [])}

    avg_popularity = round(sum(popularities) / len(popularities)) if popularities else None
    decade = None
    if years:
        decade = Counter((year // 10) * 10 for year in years).most_common(1)[0][0]

    return {
        "track_count": len(tracks),
        "artist_count": len(artists),
        "genre_count": len(genres),
        "avg_popularity": avg_popularity,
        # A high obscurity score means your favourites are less mainstream.
        "obscurity": (100 - avg_popularity) if avg_popularity is not None else None,
        "avg_year": round(sum(years) / len(years)) if years else None,
        "top_decade": f"{decade}s" if decade is not None else None,
        "avg_duration": format_duration(
            int(sum(durations) / len(durations)) if durations else None
        ),
        "total_duration": format_duration(sum(durations)) if durations else "--:--",
        "explicit_share": (
            round(sum(1 for t in tracks if t["explicit"]) / len(tracks) * 100)
            if tracks
            else 0
        ),
    }
