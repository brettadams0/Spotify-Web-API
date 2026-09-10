"""Guards on the deployment configuration.

These assert that the three deploy targets — Vercel, Render/Procfile and
Docker — all point at an entrypoint that actually exists and exposes a WSGI
callable. Without them, renaming a module fails at deploy time rather than in
CI, which is a much slower way to find out.
"""
from __future__ import annotations

import importlib
import json
import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _vercel_entrypoint() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    return data["tool"]["vercel"]["entrypoint"]


class TestVercel:
    def test_entrypoint_resolves_to_a_wsgi_callable(self):
        module_name, _, attr = _vercel_entrypoint().partition(":")
        app = getattr(importlib.import_module(module_name), attr)
        assert callable(app)

    def test_vercel_json_configures_the_declared_entrypoint(self):
        module_name = _vercel_entrypoint().partition(":")[0]
        functions = json.loads((ROOT / "vercel.json").read_text())["functions"]
        assert f"{module_name}.py" in functions, (
            f"vercel.json configures {list(functions)}, but pyproject.toml "
            f"declares the entrypoint as {module_name}.py"
        )

    def test_duration_allows_for_several_sequential_spotify_calls(self):
        """The dashboard makes three upstream calls, each able to take
        SPOTIFY_TIMEOUT seconds, so the function budget must exceed that."""
        from spotifystats.config import Config

        functions = json.loads((ROOT / "vercel.json").read_text())["functions"]
        budget = next(iter(functions.values()))["maxDuration"]
        assert budget >= Config.SPOTIFY_TIMEOUT * 3

    @pytest.mark.parametrize(
        "needed",
        [
            "templates/base.html",
            "static/css/app.css",
            "static/js/app.js",
            "spotifystats/__init__.py",
        ],
    )
    def test_runtime_files_are_not_excluded_from_the_bundle(self, needed):
        """Flask serves its own static files and templates, so excluding them
        would 404 the whole UI in production."""
        import fnmatch

        functions = json.loads((ROOT / "vercel.json").read_text())["functions"]
        patterns = next(iter(functions.values()))["excludeFiles"].strip("{}").split(",")
        matched = [p for p in patterns if fnmatch.fnmatch(needed, p)]
        assert not matched, f"{needed} would be excluded by {matched}"

    def test_python_version_is_pinned_and_matches_ci(self):
        pinned = (ROOT / ".python-version").read_text().strip()
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        assert pinned in workflow, (
            f".python-version pins {pinned}, which CI does not test"
        )


class TestOtherTargets:
    def test_procfile_and_docker_serve_the_same_callable(self):
        entry = _vercel_entrypoint().replace(":", ":")  # wsgi:app
        procfile = (ROOT / "Procfile").read_text()
        dockerfile = (ROOT / "Dockerfile").read_text()
        assert entry in procfile, f"Procfile does not serve {entry}"
        assert entry in dockerfile, f"Dockerfile does not serve {entry}"

    def test_every_target_binds_the_port_the_platform_provides(self):
        for name in ("Procfile", "render.yaml", "Dockerfile"):
            text = (ROOT / name).read_text()
            assert re.search(r"\$\{?PORT\}?", text), f"{name} hardcodes a port"
