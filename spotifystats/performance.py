"""Transfer-size and caching concerns, kept out of the app factory.

Two wins, both measured in tests:

* gzip on HTML, CSS, JS and JSON. These pages are text, so the saving is
  large and the cost is a few milliseconds of CPU. Done here rather than with
  a dependency because the rule is short and the behaviour is worth owning.
* Long-lived caching for static assets, made safe by stamping each URL with a
  hash of the file. A new build changes the URL, so a stale asset can never be
  served, and an unchanged one is never re-downloaded.
"""
from __future__ import annotations

import gzip
import hashlib
from pathlib import Path

from flask import Flask, request

#: Only compress bodies where the saving beats the CPU and header overhead.
MIN_COMPRESS_BYTES = 800

#: Ceiling on reading a streamed file into memory in order to compress it.
MAX_MATERIALISE_BYTES = 2 * 1024 * 1024

COMPRESSIBLE = {
    "text/html",
    "text/css",
    "text/javascript",
    "application/javascript",
    "application/json",
    "image/svg+xml",
    "application/manifest+json",
}

#: Immutable because the URL carries a content hash.
STATIC_MAX_AGE = 31536000  # one year

_hashes: dict[str, str] = {}


def asset_hash(static_folder: str, filename: str) -> str:
    """Return a short content hash for a static file, computed once per boot."""
    if filename in _hashes:
        return _hashes[filename]
    path = Path(static_folder) / filename
    try:
        digest = hashlib.blake2b(path.read_bytes(), digest_size=6).hexdigest()
    except OSError:
        digest = ""
    _hashes[filename] = digest
    return digest


def register(app: Flask) -> None:
    """Attach compression, caching, and the cache-busting URL helper."""
    static_folder = app.static_folder or ""

    @app.template_global()
    def asset(filename: str) -> str:
        """url_for('static', ...) plus a content hash, for cache busting."""
        from flask import url_for

        digest = asset_hash(static_folder, filename)
        return url_for("static", filename=filename, v=digest) if digest else url_for(
            "static", filename=filename
        )

    @app.after_request
    def _cache_static(response):
        if request.endpoint == "static":
            # A hashed URL can be cached forever; an unhashed one briefly.
            if request.args.get("v"):
                response.headers["Cache-Control"] = (
                    f"public, max-age={STATIC_MAX_AGE}, immutable"
                )
            else:
                response.headers.setdefault("Cache-Control", "public, max-age=3600")
        return response

    @app.after_request
    def _compress(response):
        if "gzip" not in request.headers.get("Accept-Encoding", "").lower():
            return response
        if response.status_code < 200 or response.status_code >= 300:
            return response
        if "Content-Encoding" in response.headers:
            return response
        if response.mimetype not in COMPRESSIBLE:
            return response

        if response.direct_passthrough:
            # Static files come back as a file wrapper, which get_data()
            # refuses to read. Materialising one is cheap at these sizes and
            # is what lets the stylesheet and script ship compressed too.
            if (response.content_length or 0) > MAX_MATERIALISE_BYTES:
                return response
            response.direct_passthrough = False

        body = response.get_data()
        if len(body) < MIN_COMPRESS_BYTES:
            return response

        packed = gzip.compress(body, compresslevel=6)
        if len(packed) >= len(body):
            return response

        response.set_data(packed)
        response.headers["Content-Encoding"] = "gzip"
        response.headers["Content-Length"] = str(len(packed))
        response.headers.add("Vary", "Accept-Encoding")
        return response
