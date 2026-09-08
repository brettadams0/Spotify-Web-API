# Spotify Stats

A web app for exploring your own Spotify listening history: top artists, tracks
and genres across three time ranges, your recent plays with timestamps, and
one-tap export of any chart to a real playlist on your account.

Built with Flask and [Spotipy](https://spotipy.readthedocs.io/). It installs as
a Progressive Web App, so on a phone or tablet you can add it to your home
screen and it runs full-screen like a native app — no app store, one codebase.

---

## Features

| | |
|---|---|
| **Top artists** | Your full top 50, with movement since your last visit |
| **Top tracks** | Your full top 50, with album, year and length |
| **Top genres** | Ranked across your top artists, weighted so a genre held by your #1 artist outranks one held by your #40 |
| **Recently played** | Your last 50 plays, each with its exact timestamp shown in your local time |
| **Playlists** | Every playlist on your account |
| **Taste profile** | Obscurity score, average release year and decade, average track length, explicit share |
| **Now playing** | A live widget that polls while the tab is visible |
| **Save as playlist** | Push the current top-tracks chart straight to your Spotify account |
| **Time ranges** | Last 4 weeks, last 6 months, all time — on every chart |

### Movement arrows

Chart positions are snapshotted in **your browser's `localStorage`**, never on a
server, and compared on your next visit. A snapshot refreshes at most once every
12 hours so that revisiting a page later the same day still shows real movement.
Clearing site data resets it.

### A note on the Spotify API

On 27 November 2024 Spotify
[restricted several endpoints](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api)
for newly registered apps: audio features, audio analysis, recommendations,
related artists, and featured/editorial playlists. This app deliberately uses
**none** of them, so a freshly created Spotify app will work. That is also why
there are no "danceability"/"energy" charts — that data is no longer available
to new apps.

---

## Quick start

**1. Create a Spotify app.** Go to the
[Spotify Developer Dashboard](https://developer.spotify.com/dashboard), create
an app, and add this Redirect URI exactly:

```
http://127.0.0.1:5000/callback
```

Copy the Client ID and Client Secret.

**2. Install and configure.**

```bash
git clone https://github.com/brettadams0/Spotify-Web-API.git
cd Spotify-Web-API

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
```

Fill in `.env`:

```ini
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:5000/callback
SECRET_KEY=<python -c "import secrets; print(secrets.token_hex(32))">
```

**3. Run it.**

```bash
python app.py
```

Open <http://127.0.0.1:5000> and sign in.

> While your Spotify app is in development mode, only accounts you add under
> **User Management** in the dashboard can log in. Anyone else gets a 403.

---

## Deploying

The app is a standard WSGI application (`wsgi:app`) with no database, so it runs
anywhere. Whichever host you pick, you must:

1. Set `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SECRET_KEY`, and
   `SESSION_COOKIE_SECURE=true`.
2. Set `SPOTIFY_REDIRECT_URI` to `https://your-domain/callback` **and** add that
   exact URI to your Spotify app's settings.

### Render

`render.yaml` is a ready blueprint — point Render at the repo, then fill in the
three secret values it prompts for.

### Docker

```bash
docker build -t spotify-stats .
docker run -p 8000:8000 --env-file .env spotify-stats
```

### Fly.io / Railway / Heroku

The `Procfile` covers all three:

```
web: gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 60
```

### Installing it as an app

Once deployed over HTTPS, open the site on a phone and choose **Add to Home
Screen** (iOS Safari) or **Install app** (Android Chrome). It gets its own icon,
launches full-screen, and shows an offline notice instead of a browser error
when the connection drops.

---

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `SPOTIFY_CLIENT_ID` | — | From the Spotify dashboard. Required. |
| `SPOTIFY_CLIENT_SECRET` | — | From the Spotify dashboard. Required. |
| `SPOTIFY_REDIRECT_URI` | `http://127.0.0.1:5000/callback` | Must match the dashboard exactly. |
| `SECRET_KEY` | random per boot | Signs the session cookie. Set it in production, or every restart logs everyone out. |
| `SESSION_COOKIE_SECURE` | `false` | Set `true` when serving over HTTPS. |
| `CACHE_TTL` | `120` | Seconds an upstream Spotify response may be reused. `0` disables caching. |
| `SPOTIFY_TIMEOUT` | `10` | Request timeout, in seconds. |
| `PORT` | `5000` | Dev server port. |
| `FLASK_DEBUG` | `false` | Dev server debug mode. |

---

## Project layout

```
spotifystats/
  __init__.py        app factory, error handlers, security headers
  config.py          environment-driven configuration
  spotify.py         OAuth, token refresh, per-user response cache
  shaping.py         pure functions that turn API payloads into view models
  data.py            fetch-and-shape helpers used by the views
  blueprints/
    auth.py          /login, /callback, /logout
    pages.py         the six HTML pages
    api.py           /api/now-playing, /api/top/<kind>, /api/playlist
templates/           Jinja templates; partials/ holds rows, tiles and icons
static/
  css/app.css        the whole design system
  js/app.js          filtering, movement arrows, now playing, export
  sw.js              service worker (offline shell)
  manifest.webmanifest
tests/               pytest suite, no network required
wsgi.py              production entry point
app.py               development entry point
```

---

## Testing

```bash
pip install -r requirements-dev.txt
pytest
```

The suite runs entirely against a fake Spotify client, so it needs no
credentials and no network. It covers payload shaping, genre ranking, paging
past Spotify's 50-item cap, per-user caching, the OAuth state check, token
refresh and refresh failure, the redirect guard on `/refresh`, every page and
API endpoint, and the empty-state and error paths.

---

## Privacy

Your listening data is read live from Spotify on each request and rendered
straight to the page. Nothing is written to a database — there isn't one. The
only things stored are your Spotify token in a signed, HTTP-only session cookie,
and the chart snapshots that power the movement arrows, which stay in your own
browser. Signing out clears both.

---

## License

MIT — see [LICENSE](LICENSE).

Not affiliated with or endorsed by Spotify AB.
