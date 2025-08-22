from flask import Flask, redirect, request, session, url_for, render_template, jsonify
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import webbrowser
import threading
from collections import Counter
import json
from datetime import datetime, timedelta
import statistics

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SESSION_COOKIE_NAME'] = 'spotify-login-session'

# Spotify API credentials
SPOTIPY_CLIENT_ID = '23b2a82501b04530ba24fa22bac9c3dd'
SPOTIPY_CLIENT_SECRET = ''
SPOTIPY_REDIRECT_URI = 'http://localhost:5000/callback'

# Spotify OAuth with expanded scope
sp_oauth = SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                        client_secret=SPOTIPY_CLIENT_SECRET,
                        redirect_uri=SPOTIPY_REDIRECT_URI,
                        scope='user-top-read user-library-read playlist-read-private user-read-private user-read-email user-read-recently-played user-read-playback-state user-read-currently-playing')

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
    top_genres = genre_counts.most_common(15)
    return top_genres

def get_audio_features(sp, track_ids):
    """Get audio features for tracks"""
    features = []
    for i in range(0, len(track_ids), 100):
        batch = track_ids[i:i+100]
        batch_features = sp.audio_features(batch)
        features.extend([f for f in batch_features if f])
    return features

def analyze_audio_features(features):
    """Analyze audio features and return insights"""
    if not features:
        return {}
    
    analysis = {
        'avg_energy': statistics.mean([f['energy'] for f in features if f]),
        'avg_danceability': statistics.mean([f['danceability'] for f in features if f]),
        'avg_valence': statistics.mean([f['valence'] for f in features if f]),
        'avg_tempo': statistics.mean([f['tempo'] for f in features if f]),
        'avg_acousticness': statistics.mean([f['acousticness'] for f in features if f]),
        'avg_instrumentalness': statistics.mean([f['instrumentalness'] for f in features if f]),
        'avg_loudness': statistics.mean([f['loudness'] for f in features if f]),
        'avg_speechiness': statistics.mean([f['speechiness'] for f in features if f]),
        'key_distribution': Counter([f['key'] for f in features if f and f['key'] != -1]),
        'mode_distribution': Counter([f['mode'] for f in features if f]),
        'time_signature_distribution': Counter([f['time_signature'] for f in features if f])
    }
    
    # Add insights
    analysis['mood'] = 'Energetic' if analysis['avg_energy'] > 0.7 else 'Chill' if analysis['avg_energy'] < 0.3 else 'Balanced'
    analysis['dance_style'] = 'High Energy' if analysis['avg_danceability'] > 0.7 else 'Low Energy' if analysis['avg_danceability'] < 0.3 else 'Moderate'
    
    return analysis

def get_recent_activity(sp):
    """Get recently played tracks"""
    try:
        recent = sp.current_user_recently_played(limit=50)
        return recent
    except:
        return {'items': []}

def get_current_playback(sp):
    """Get current playback state"""
    try:
        current = sp.current_playback()
        return current
    except:
        return None

def get_user_playlists_detailed(sp):
    """Get detailed playlist information"""
    try:
        playlists = sp.current_user_playlists(limit=50)
        detailed_playlists = []
        
        for playlist in playlists['items']:
            try:
                tracks = sp.playlist_tracks(playlist['id'], limit=100)
                playlist['track_count'] = tracks['total']
                playlist['tracks'] = tracks['items']
                detailed_playlists.append(playlist)
            except:
                playlist['track_count'] = 0
                playlist['tracks'] = []
                detailed_playlists.append(playlist)
        
        return detailed_playlists
    except:
        return []

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
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    token_info = get_token()
    if not token_info:
        return redirect(url_for('login'))

    sp = spotipy.Spotify(auth=token_info['access_token'])
    
    # Get comprehensive data
    user_profile = sp.current_user()
    top_artists_short = sp.current_user_top_artists(limit=10, time_range='short_term')
    top_artists_medium = sp.current_user_top_artists(limit=10, time_range='medium_term')
    top_artists_long = sp.current_user_top_artists(limit=10, time_range='long_term')
    
    top_tracks_short = sp.current_user_top_tracks(limit=10, time_range='short_term')
    top_tracks_medium = sp.current_user_top_tracks(limit=10, time_range='medium_term')
    top_tracks_long = sp.current_user_top_tracks(limit=10, time_range='long_term')
    
    # Get audio features for analysis
    track_ids = [track['id'] for track in top_tracks_long['items']]
    audio_features = get_audio_features(sp, track_ids)
    audio_analysis = analyze_audio_features(audio_features)
    
    # Get recent activity
    recent_activity = get_recent_activity(sp)
    current_playback = get_current_playback(sp)
    
    # Get top genres
    top_genres = get_top_genres(top_artists_long)
    
    return render_template('dashboard.html', 
                         user_profile=user_profile,
                         top_artists_short=top_artists_short,
                         top_artists_medium=top_artists_medium,
                         top_artists_long=top_artists_long,
                         top_tracks_short=top_tracks_short,
                         top_tracks_medium=top_tracks_medium,
                         top_tracks_long=top_tracks_long,
                         audio_analysis=audio_analysis,
                         recent_activity=recent_activity,
                         current_playback=current_playback,
                         top_genres=top_genres)

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

@app.route('/api/audio-features/<time_range>')
def api_audio_features(time_range):
    token_info = get_token()
    if not token_info:
        return jsonify({'error': 'Not authenticated'}), 401

    sp = spotipy.Spotify(auth=token_info['access_token'])
    top_tracks = sp.current_user_top_tracks(limit=50, time_range=time_range)
    track_ids = [track['id'] for track in top_tracks['items']]
    audio_features = get_audio_features(sp, track_ids)
    analysis = analyze_audio_features(audio_features)
    
    return jsonify(analysis)

@app.route('/api/recent-activity')
def api_recent_activity():
    token_info = get_token()
    if not token_info:
        return jsonify({'error': 'Not authenticated'}), 401

    sp = spotipy.Spotify(auth=token_info['access_token'])
    recent = get_recent_activity(sp)
    
    return jsonify(recent)

def open_browser():
    webbrowser.open_new('http://localhost:5000')

if __name__ == '__main__':
    threading.Timer(1, open_browser).start()
    app.run(debug=True)
