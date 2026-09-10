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
| **Installable** | Add to home screen on iOS or Android; runs full-screen with an offline notice |
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

### Vercel

The repo carries a Vercel entrypoint too, so the same code deploys either way.
`pyproject.toml` points Vercel at `wsgi:app` — the identical callable gunicorn
serves on Render and in Docker — and `vercel.json` raises the function budget
to 60s, because loading the dashboard makes three sequential Spotify calls.

Import the repo at [vercel.com/new](https://vercel.com/new), then set
`SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REDIRECT_URI`,
`SECRET_KEY` and `SESSION_COOKIE_SECURE=true` under **Settings → Environment
Variables**.

**Which to pick.** Render runs one long-lived process, so the response cache in
`spotify.py` works as designed. Vercel runs the app as a serverless function,
where each instance holds its own cache — that costs a few more Spotify API
calls but nothing else, since the cache is a pure optimisation and no request
depends on it. The practical trade is the other way round: Render's free tier
sleeps after ~15 minutes and takes ~30s to wake, which is painful for an app
you open from your phone a few times a day. Vercel has no such sleep. For
phone-first use, prefer Vercel.

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

## Design and performance

The interface follows three rules borrowed from [Vercel's Geist](https://vercel.com/geist/colors)
and [Linear](https://linear.app):

1. **Every neutral has one job.** A ten-step ramp where 100–300 are surfaces,
   400–500 are borders, 900 is secondary text and 1000 is primary. A colour is
   never picked by eye.
2. **Spacing and radii come from a scale.** A 4px spacing base and exactly
   three radii — 6px controls, 12px cards, pill.
3. **Structure comes from hairline borders, not shadows,** and there is a
   single accent colour, reserved for the active nav item, the primary button,
   focus rings and now-playing.

Type is a system stack: SF on Apple platforms, Segoe UI on Windows, Roboto on
Android. All three are high-quality UI faces and none costs a font download,
which matters more here than a bespoke typeface would.

### Transfer size

Measured on `/dashboard` with a 25-item chart:

| | before | after |
|---|---|---|
| HTML | 26,389 B | 3,650 B |
| CSS | 23,942 B | 5,594 B |
| JS | 11,123 B | 3,695 B |
| **total** | **61,454 B** | **12,939 B** |

A 79% reduction, from four changes:

- **gzip** on HTML, CSS, JS and JSON (`spotifystats/performance.py`).
- **Immutable caching** on static assets, made safe by stamping each URL with
  a content hash, so a repeat visit transfers only the HTML.
- **`srcset` on every thumbnail**, so a phone fetches Spotify's 64px artwork
  for a 36px slot instead of the 640px file.
- **`content-visibility` on list rows**, so the browser skips layout for the
  rows below the fold on a 50-item chart.

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
  performance.py     gzip, immutable asset caching, cache-busted URLs
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
wsgi.py              production entry point (gunicorn, and Vercel's entrypoint)
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
API endpoint, compression and cache headers, `srcset` generation, and the
empty-state and error paths.

The UI is also checked in Chromium at 320, 390, 768, 1280 and 1920px for
horizontal overflow and console errors, plus a scripted interaction pass over
filtering, movement arrows, playlist export, now-playing, range switching and
keyboard focus order.

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
