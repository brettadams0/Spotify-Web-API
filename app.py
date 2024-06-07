from flask import Flask, redirect, request, session, url_for, render_template
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import webbrowser
import threading
from collections import Counter

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SESSION_COOKIE_NAME'] = 'spotify-login-session'

# Spotify API credentials
SPOTIPY_CLIENT_ID = '23b2a82501b04530ba24fa22bac9c3dd'
SPOTIPY_CLIENT_SECRET = ''
SPOTIPY_REDIRECT_URI = 'http://localhost:5000/callback'

# Spotify OAuth
sp_oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                        client_secret=SPOTIPY_CLIENT_SECRET,
                        redirect_uri=SPOTIPY_REDIRECT_URI,
                        scope='user-top-read user-library-read playlist-read-private user-read-private user-read-email')

def get_token():
    token_info = session.get("token_info", None)
    if not token_info:
        return None

    now = int(time.time())
    is_expired = token_info['expires_at'] - now < 60

    if is_expired:
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])

    return token_info

def get_top_genres(top_artists):
    genres = []
    for artist in top_artists['items']:
        genres.extend(artist['genres'])
    genre_counts = Counter(genres)
    top_genres = genre_counts.most_common(10)
    return top_genres

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    session.clear()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session["token_info"] = token_info
    return redirect(url_for('stats'))

@app.route('/stats')
def stats():
    token_info = get_token()
    if not token_info:
        return redirect(url_for('login'))

    sp = spotipy.Spotify(auth=token_info['access_token'])
    
    time_range = request.args.get('time_range', 'short_term')
    section = request.args.get('section', 'profile')

    user_profile = sp.current_user()
    top_artists = sp.current_user_top_artists(limit=25, time_range=time_range)
    top_tracks = sp.current_user_top_tracks(limit=25, time_range=time_range)
    playlists = sp.current_user_playlists(limit=10)
    top_genres = get_top_genres(top_artists)
    
    return render_template('stats.html', user_profile=user_profile, top_artists=top_artists, top_tracks=top_tracks, playlists=playlists, top_genres=top_genres, time_range=time_range, section=section)

def open_browser():
    webbrowser.open_new('http://localhost:5000')

if __name__ == '__main__':
    threading.Timer(1, open_browser).start()
    app.run(debug=True)
