"""Tests for compression, asset caching, and image payload shaping."""
from __future__ import annotations

import gzip

import pytest

from spotifystats.performance import MIN_COMPRESS_BYTES
from spotifystats.shaping import image_srcset, shape_artist, shape_track
from tests.conftest import make_artist, make_track


class TestCompression:
    def test_html_is_gzipped_for_clients_that_accept_it(self, signed_in):
        response = signed_in.get("/dashboard", headers={"Accept-Encoding": "gzip"})
        assert response.headers["Content-Encoding"] == "gzip"
        assert "Accept-Encoding" in response.headers["Vary"]
        # The body must still decode to the real page.
        body = gzip.decompress(response.get_data()).decode()
        assert "Top tracks" in body

    def test_a_client_that_does_not_accept_gzip_gets_plain_bytes(self, signed_in):
        response = signed_in.get("/dashboard", headers={"Accept-Encoding": "identity"})
        assert "Content-Encoding" not in response.headers
        assert b"Top tracks" in response.get_data()

    def test_compression_meaningfully_shrinks_a_page(self, signed_in):
        raw = signed_in.get("/tracks", headers={"Accept-Encoding": "identity"})
        packed = signed_in.get("/tracks", headers={"Accept-Encoding": "gzip"})
        assert len(packed.get_data()) < len(raw.get_data()) / 2

    def test_static_css_is_compressed_despite_being_a_file_response(self, client):
        response = client.get("/static/css/app.css", headers={"Accept-Encoding": "gzip"})
        assert response.headers["Content-Encoding"] == "gzip"
        assert b"--accent" in gzip.decompress(response.get_data())

    def test_already_compressed_images_are_left_alone(self, client):
        response = client.get(
            "/static/icons/icon-512.png", headers={"Accept-Encoding": "gzip"}
        )
        assert "Content-Encoding" not in response.headers

    def test_tiny_bodies_are_not_worth_compressing(self, client):
        response = client.get("/healthz", headers={"Accept-Encoding": "gzip"})
        assert len(response.get_data()) < MIN_COMPRESS_BYTES
        assert "Content-Encoding" not in response.headers

    def test_a_redirect_is_not_compressed(self, signed_in):
        response = signed_in.get("/", headers={"Accept-Encoding": "gzip"})
        assert response.status_code == 302
        assert "Content-Encoding" not in response.headers


class TestAssetCaching:
    def test_a_hashed_url_is_cached_immutably(self, client):
        response = client.get("/static/css/app.css?v=deadbeef")
        assert "immutable" in response.headers["Cache-Control"]
        assert "max-age=31536000" in response.headers["Cache-Control"]

    def test_an_unhashed_url_gets_only_a_short_cache(self, client):
        response = client.get("/static/css/app.css")
        assert "immutable" not in response.headers["Cache-Control"]

    def test_pages_reference_assets_with_a_content_hash(self, signed_in):
        body = signed_in.get("/dashboard", headers={"Accept-Encoding": "identity"})
        text = body.get_data(as_text=True)
        assert "/static/css/app.css?v=" in text
        assert "/static/js/app.js?v=" in text

    def test_the_hash_tracks_file_content(self, app, tmp_path):
        from spotifystats import performance

        performance._hashes.clear()
        target = tmp_path / "probe.css"
        target.write_text("a{}")
        first = performance.asset_hash(str(tmp_path), "probe.css")

        performance._hashes.clear()
        target.write_text("b{}")
        second = performance.asset_hash(str(tmp_path), "probe.css")

        assert first and second and first != second

    def test_a_missing_asset_degrades_to_an_unhashed_url(self, app):
        from spotifystats import performance

        performance._hashes.clear()
        assert performance.asset_hash("/nonexistent", "nope.css") == ""
        with app.test_request_context("/"):
            assert "?v=" not in app.jinja_env.globals["asset"]("nope.css")


class TestImagePayload:
    def test_srcset_lists_every_size_smallest_first(self):
        images = [
            {"url": "big", "width": 640},
            {"url": "mid", "width": 300},
            {"url": "small", "width": 64},
        ]
        assert image_srcset(images) == "small 64w, mid 300w, big 640w"

    def test_srcset_drops_duplicate_widths(self):
        images = [{"url": "a", "width": 300}, {"url": "b", "width": 300}]
        assert image_srcset(images) == "a 300w"

    @pytest.mark.parametrize(
        "images", [None, [], [{"url": "x"}], [{"width": 100}], [{}]]
    )
    def test_srcset_is_empty_without_usable_entries(self, images):
        assert image_srcset(images) == ""

    def test_shaped_objects_carry_a_srcset(self):
        assert shape_track(make_track(1))["srcset"].count("w,") == 1
        assert shape_artist(make_artist(1))["srcset"].count("w,") == 1

    def test_thumbnails_declare_a_render_size_so_the_browser_picks_small(
        self, signed_in
    ):
        body = signed_in.get(
            "/tracks", headers={"Accept-Encoding": "identity"}
        ).get_data(as_text=True)
        assert 'sizes="36px"' in body
        assert "srcset=" in body

    def test_the_cdn_connection_is_warmed_early(self, signed_in):
        body = signed_in.get(
            "/dashboard", headers={"Accept-Encoding": "identity"}
        ).get_data(as_text=True)
        assert 'rel="preconnect" href="https://i.scdn.co"' in body


class TestRenderCost:
    def test_long_lists_skip_offscreen_layout(self, client):
        css = client.get(
            "/static/css/app.css", headers={"Accept-Encoding": "identity"}
        ).get_data(as_text=True)
        # content-visibility lets the browser skip laying out rows nobody sees.
        assert "content-visibility: auto" in css
        assert "contain-intrinsic-size" in css

    def test_no_backdrop_filter_remains(self, client):
        css = client.get(
            "/static/css/app.css", headers={"Accept-Encoding": "identity"}
        ).get_data(as_text=True)
        # backdrop-filter forces a repaint of everything behind it on scroll.
        assert "backdrop-filter" not in css


class TestBrokenArtwork:
    def test_the_fallback_clears_srcset_before_swapping_src(self, client):
        """srcset takes precedence over src, so it must be removed first."""
        js = client.get(
            "/static/js/app.js", headers={"Accept-Encoding": "identity"}
        ).get_data(as_text=True)
        marker = js[js.index("function markBroken") : js.index("function initBrokenArt")]
        assert "removeAttribute('srcset')" in marker
        assert marker.index("removeAttribute('srcset')") < marker.index("el.src =")
