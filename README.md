# Spotify Stats - Modern Music Analytics Dashboard

## 🎵 Overview

Spotify Stats is a comprehensive, modern web application that provides detailed analytics and insights into your Spotify listening habits. Built with Flask and featuring a beautiful, responsive design, it offers everything a Spotify user would want from a stats website.

## ✨ Features

### 📊 Comprehensive Analytics
- **Top Artists & Tracks**: View your most-listened artists and tracks across different time periods (4 weeks, 3 months, all time)
- **Genre Analysis**: Discover your music genre preferences with visual charts and rankings
- **Audio Features**: Deep dive into energy, danceability, valence, acousticness, and more
- **Recent Activity**: Track your recent listening history and latest discoveries

### 🎨 Modern Design
- **Beautiful UI**: Sleek, modern interface with gradient backgrounds and glassmorphism effects
- **Responsive Design**: Perfect experience on desktop, tablet, and mobile devices
- **Interactive Charts**: Dynamic visualizations using Chart.js
- **Smooth Animations**: Engaging hover effects and transitions
- **Dark Theme**: Easy on the eyes with a sophisticated dark color scheme

### 📈 Advanced Metrics
- **Audio Analysis**: Energy, danceability, valence, acousticness, instrumentalness, tempo
- **Mood Insights**: Understand your music mood and dance style preferences
- **Key Distribution**: Musical key and mode analysis
- **Time Signatures**: Rhythm pattern analysis
- **Popularity Tracking**: Track popularity scores for artists and tracks

### 🔄 Real-time Features
- **Live Data**: Real-time updates from Spotify API
- **Recent Activity**: See what you've been listening to recently
- **Current Playback**: Integration with current Spotify playback state
- **Dynamic Updates**: Charts and metrics update based on time range selection

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- Spotify account
- Spotify Developer account

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd spotify-stats
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Spotify Developer credentials**
   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   - Create a new application
   - Get your Client ID and Client Secret
   - Add `http://localhost:5000/callback` to your Redirect URIs

4. **Configure environment variables**
   ```bash
   # In app.py, update these values:
   SPOTIPY_CLIENT_ID = 'your_client_id_here'
   SPOTIPY_CLIENT_SECRET = 'your_client_secret_here'
   SPOTIPY_REDIRECT_URI = 'http://localhost:5000/callback'
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Open your browser**
   - Navigate to `http://localhost:5000`
   - Click "Connect with Spotify"
   - Authorize the application

## 📱 Usage

### Dashboard Sections

1. **Overview**: Quick stats and summary charts
2. **Top Artists**: Detailed artist rankings with follower counts and genres
3. **Top Tracks**: Track listings with album art and duration
4. **Genres**: Genre distribution with interactive charts
5. **Audio Analysis**: Detailed audio feature breakdowns
6. **Recent Activity**: Your latest listening history

### Time Ranges
- **4 Weeks**: Recent listening habits
- **3 Months**: Medium-term preferences
- **All Time**: Long-term favorites

### Interactive Features
- **Hover Effects**: Cards lift and scale on hover
- **Smooth Navigation**: Seamless section transitions
- **Mobile Swipe**: Swipe gestures for mobile navigation
- **Search & Filter**: Find specific artists or tracks quickly

## 🛠️ Technical Details

### Backend
- **Framework**: Flask (Python)
- **API**: Spotify Web API via Spotipy
- **Authentication**: OAuth 2.0 with Spotify
- **Data Processing**: Audio feature analysis and statistics

### Frontend
- **Styling**: Modern CSS with gradients and glassmorphism
- **Charts**: Chart.js for interactive visualizations
- **Icons**: Font Awesome for beautiful icons
- **Responsive**: CSS Grid and Flexbox for layout

### API Endpoints
- `/`: Landing page
- `/login`: Spotify OAuth initiation
- `/callback`: OAuth callback handling
- `/dashboard`: Main analytics dashboard
- `/api/audio-features/<time_range>`: Audio analysis data
- `/api/recent-activity`: Recent listening activity

## 🎯 Key Metrics & Statistics

### Artist Analytics
- Top artists by popularity
- Follower counts
- Genre associations
- Artist ranking trends

### Track Analytics
- Most played tracks
- Track duration analysis
- Album associations
- Popularity scores

### Audio Features
- **Energy**: High energy vs. chill music preference
- **Danceability**: How danceable your music is
- **Valence**: Positivity/happiness of your music
- **Acousticness**: Acoustic vs. electronic preference
- **Instrumentalness**: Vocal vs. instrumental preference
- **Tempo**: Average BPM of your music

### Genre Insights
- Genre distribution charts
- Genre popularity rankings
- Cross-genre analysis
- Genre evolution over time

## 🔒 Privacy & Security

- **Data Privacy**: Your data is only used for generating insights
- **Secure Authentication**: OAuth 2.0 with Spotify
- **No Data Storage**: No personal data is stored on our servers
- **API Limits**: Respects Spotify API rate limits

## 🎨 Design Features

### Visual Elements
- **Gradient Backgrounds**: Beautiful color transitions
- **Glassmorphism**: Frosted glass effect on cards
- **Spotify Branding**: Official Spotify green (#1DB954)
- **Smooth Animations**: CSS transitions and keyframes
- **Responsive Grid**: Adaptive layouts for all screen sizes

### User Experience
- **Intuitive Navigation**: Clear section organization
- **Loading States**: Smooth loading animations
- **Error Handling**: Graceful error messages
- **Accessibility**: Keyboard navigation support

## 🔧 Customization

### Styling
- Modify `static/styles.css` for custom styling
- Update color schemes in CSS variables
- Customize animations and transitions

### Features
- Add new API endpoints in `app.py`
- Extend chart types in `static/script.js`
- Modify data processing functions

## 📊 Data Sources

All data is sourced from the official Spotify Web API:
- User profile information
- Top artists and tracks
- Audio features and analysis
- Recent listening activity
- Playlist information

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## 🆘 Support

If you encounter any issues:
1. Check the Spotify API status
2. Verify your credentials are correct
3. Ensure you have the required permissions
4. Check the browser console for errors

## 🎵 Enjoy Your Music Analytics!

Discover new insights about your listening habits and explore your musical journey with our comprehensive Spotify stats dashboard. Happy listening! 🎶
