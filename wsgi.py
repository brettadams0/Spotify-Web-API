"""WSGI entry point used by gunicorn: ``gunicorn wsgi:app``."""
from spotifystats import create_app

app = create_app()
