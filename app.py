"""Development entry point.

Production runs through ``wsgi:app`` under gunicorn; see the README.
"""
from __future__ import annotations

import os

try:  # optional: load a local .env during development
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - python-dotenv is optional
    pass

from spotifystats import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"},
    )
