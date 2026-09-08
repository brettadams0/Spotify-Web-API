"""Unit tests for the pure payload-shaping helpers."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from spotifystats.shaping import (
    aggregate_genres,
    format_duration,
    format_exact_time,
    format_number,
    parse_timestamp,
    pick_image,
    relative_time,
    release_year,
    shape_playlist,
    shape_recent,
    shape_track,
    taste_profile,
)
from tests.conftest import make_artist, make_track


class TestPickImage:
    def test_prefers_smallest_image_above_the_threshold(self):
        images = [
            {"url": "big", "width": 640},
            {"url": "mid", "width": 300},
            {"url": "small", "width": 64},
        ]
        assert pick_image(images, minimum=160) == "mid"

    def test_falls_back_to_largest_when_all_are_small(self):
        images = [{"url": "a", "width": 64}, {"url": "b", "width": 120}]
        assert pick_image(images, minimum=300) == "b"

    @pytest.mark.parametrize("value", [None, [], [{}], [{"url": ""}]])
    def test_returns_none_without_a_usable_image(self, value):
        assert pick_image(value) is None


class TestFormatting:
    @pytest.mark.parametrize(
        "ms,expected",
        [
            (0, "--:--"),
            (None, "--:--"),
            (-5, "--:--"),
            (65000, "1:05"),
            (599000, "9:59"),
            (3661000, "1:01:01"),
        ],
    )
    def test_format_duration(self, ms, expected):
        assert format_duration(ms) == expected

    def test_format_number(self):
        assert format_number(1234567) == "1,234,567"
        assert format_number(None) == "—"

    def test_release_year(self):
        assert release_year({"release_date": "1997-03-14"}) == 1997
        assert release_year({"release_date": "1997"}) == 1997
        assert release_year({"release_date": ""}) is None
        assert release_year(None) is None

    def test_format_exact_time_uses_twelve_hour_clock(self):
        moment = datetime(2026, 9, 8, 0, 5, tzinfo=timezone.utc)
        assert format_exact_time(moment) == "Sep 8, 2026 at 12:05 AM UTC"
        noon = datetime(2026, 9, 8, 12, 30, tzinfo=timezone.utc)
        assert format_exact_time(noon) == "Sep 8, 2026 at 12:30 PM UTC"


class TestTimestamps:
    def test_parse_timestamp_handles_the_z_suffix(self):
        parsed = parse_timestamp("2026-09-08T10:15:00.000Z")
        assert parsed == datetime(2026, 9, 8, 10, 15, tzinfo=timezone.utc)

    def test_parse_timestamp_rejects_garbage(self):
        assert parse_timestamp("not a date") is None
        assert parse_timestamp(None) is None

    @pytest.mark.parametrize(
        "delta,expected",
        [
            (timedelta(seconds=10), "just now"),
            (timedelta(minutes=5), "5 min ago"),
            (timedelta(hours=3), "3 hr ago"),
            (timedelta(days=1), "yesterday"),
            (timedelta(days=3), "3 days ago"),
            (timedelta(days=14), "2 wk ago"),
            (timedelta(days=90), "3 mo ago"),
            (timedelta(days=800), "2 yr ago"),
        ],
    )
    def test_relative_time(self, delta, expected):
        now = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)
        assert relative_time(now - delta, now=now) == expected

    def test_relative_time_of_nothing_is_empty(self):
        assert relative_time(None) == ""


class TestShapers:
    def test_shape_track_flattens_the_payload(self):
        shaped = shape_track(make_track(1), rank=1)
        assert shaped["rank"] == 1
        assert shaped["name"] == "Track 1"
        assert shaped["artist_label"] == "Artist 1"
        assert shaped["duration"] == "3:01"
        assert shaped["year"] == 2011
        assert shaped["uri"] == "spotify:track:track1"

    def test_shape_track_survives_missing_fields(self):
        shaped = shape_track({})
        assert shaped["name"] == "Unknown track"
        assert shaped["artist_label"] == "Unknown artist"
        assert shaped["image"] is None
        assert shaped["duration"] == "--:--"

    def test_shape_recent_adds_timestamps(self):
        now = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)
        shaped = shape_recent(
            {"track": make_track(1), "played_at": "2026-09-08T09:00:00.000Z"}, now=now
        )
        assert shaped["played_label"] == "3 hr ago"
        assert shaped["played_at_iso"].startswith("2026-09-08T09:00")

    def test_shape_recent_skips_entries_without_a_track(self):
        assert shape_recent({"played_at": "2026-09-08T09:00:00.000Z"}) is None

    def test_shape_playlist(self):
        shaped = shape_playlist(
            {
                "id": "p1",
                "name": "Road trip",
                "tracks": {"total": 12},
                "owner": {"display_name": "Sam"},
            }
        )
        assert shaped["track_count"] == 12
        assert shaped["owner"] == "Sam"


class TestAggregateGenres:
    def test_ranks_by_rank_weighted_score(self):
        artists = [
            {"name": "A", "genres": ["indie rock"]},
            {"name": "B", "genres": ["indie rock", "shoegaze"]},
            {"name": "C", "genres": ["shoegaze"]},
            {"name": "D", "genres": ["shoegaze"]},
        ]
        genres = aggregate_genres(artists)
        # shoegaze appears on three artists and indie rock on two, but indie
        # rock is carried by the #1 and #2 artists, so it wins on weight.
        assert [g["name"] for g in genres] == ["indie rock", "shoegaze"]
        assert genres[0]["count"] == 2
        assert genres[1]["count"] == 3
        # The bar is scaled against the largest count in the chart.
        assert genres[1]["bar"] == 100
        assert genres[0]["bar"] == pytest.approx(67, abs=1)

    def test_records_example_artists_capped_at_three(self):
        artists = [{"name": f"A{i}", "genres": ["pop"]} for i in range(6)]
        genres = aggregate_genres(artists)
        assert genres[0]["artists"] == ["A0", "A1", "A2"]

    def test_respects_the_limit(self):
        artists = [{"name": f"A{i}", "genres": [f"genre{i}"]} for i in range(30)]
        assert len(aggregate_genres(artists, limit=5)) == 5

    def test_empty_input_gives_an_empty_chart(self):
        assert aggregate_genres([]) == []
        assert aggregate_genres([{"name": "A", "genres": []}]) == []


class TestTasteProfile:
    def test_derives_headline_numbers(self):
        tracks = [shape_track(make_track(i)) for i in range(1, 11)]
        artists = [
            {"name": "A", "genres": ["indie rock"]},
            {"name": "B", "genres": ["dream pop"]},
        ]
        profile = taste_profile(tracks, artists)
        assert profile["track_count"] == 10
        assert profile["genre_count"] == 2
        assert profile["obscurity"] == 100 - profile["avg_popularity"]
        assert profile["top_decade"] == "2010s"
        assert 0 <= profile["explicit_share"] <= 100

    def test_handles_an_empty_chart(self):
        profile = taste_profile([], [])
        assert profile["track_count"] == 0
        assert profile["avg_popularity"] is None
        assert profile["obscurity"] is None
        assert profile["explicit_share"] == 0
