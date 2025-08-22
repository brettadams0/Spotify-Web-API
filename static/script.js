document.addEventListener('DOMContentLoaded', function() {
    // Initialize the dashboard
    initializeDashboard();
    
    // Initialize charts
    initializeCharts();
    
    // Set up event listeners
    setupEventListeners();
    
    // Load initial data
    loadInitialData();
});

function initializeDashboard() {
    // Navigation functionality
    const navItems = document.querySelectorAll('.nav-item');
    const contentSections = document.querySelectorAll('.content-section');
    
    navItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Remove active class from all nav items and sections
            navItems.forEach(nav => nav.classList.remove('active'));
            contentSections.forEach(section => section.classList.remove('active'));
            
            // Add active class to clicked nav item
            this.classList.add('active');
            
            // Show corresponding section
            const targetSection = this.getAttribute('data-section');
            const section = document.getElementById(targetSection);
            if (section) {
                section.classList.add('active');
            }
        });
    });
    
    // Time range selector functionality
    const timeButtons = document.querySelectorAll('.time-btn');
    timeButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons
            timeButtons.forEach(btn => btn.classList.remove('active'));
            
            // Add active class to clicked button
            this.classList.add('active');
            
            // Update data based on time range
            const timeRange = this.getAttribute('data-range');
            updateDataForTimeRange(timeRange);
        });
    });
}

function initializeCharts() {
    // Artists Chart
    const artistsCtx = document.getElementById('artistsChart');
    if (artistsCtx) {
        const artistsData = getArtistsChartData();
        new Chart(artistsCtx, {
            type: 'doughnut',
            data: {
                labels: artistsData.labels,
                datasets: [{
                    data: artistsData.data,
                    backgroundColor: [
                        '#1DB954', '#1ed760', '#1fdf64', '#1ed760',
                        '#1DB954', '#1ed760', '#1fdf64', '#1ed760',
                        '#1DB954', '#1ed760'
                    ],
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#ffffff',
                            padding: 20,
                            usePointStyle: true
                        }
                    }
                }
            }
        });
    }
    
    // Tracks Chart
    const tracksCtx = document.getElementById('tracksChart');
    if (tracksCtx) {
        const tracksData = getTracksChartData();
        new Chart(tracksCtx, {
            type: 'bar',
            data: {
                labels: tracksData.labels,
                datasets: [{
                    label: 'Popularity',
                    data: tracksData.data,
                    backgroundColor: 'rgba(29, 185, 84, 0.8)',
                    borderColor: '#1DB954',
                    borderWidth: 2,
                    borderRadius: 8,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#ffffff'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#ffffff',
                            maxRotation: 45
                        }
                    }
                }
            }
        });
    }
    
    // Genres Chart
    const genresCtx = document.getElementById('genresChart');
    if (genresCtx) {
        const genresData = getGenresChartData();
        new Chart(genresCtx, {
            type: 'polarArea',
            data: {
                labels: genresData.labels,
                datasets: [{
                    data: genresData.data,
                    backgroundColor: [
                        'rgba(29, 185, 84, 0.8)',
                        'rgba(30, 215, 96, 0.8)',
                        'rgba(31, 223, 100, 0.8)',
                        'rgba(30, 215, 96, 0.8)',
                        'rgba(29, 185, 84, 0.8)',
                        'rgba(30, 215, 96, 0.8)',
                        'rgba(31, 223, 100, 0.8)',
                        'rgba(30, 215, 96, 0.8)',
                        'rgba(29, 185, 84, 0.8)',
                        'rgba(30, 215, 96, 0.8)'
                    ],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#ffffff',
                            padding: 20,
                            usePointStyle: true
                        }
                    }
                },
                scales: {
                    r: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#ffffff',
                            backdropColor: 'transparent'
                        }
                    }
                }
            }
        });
    }
}

function getArtistsChartData() {
    // Extract data from the DOM
    const artistCards = document.querySelectorAll('.artist-card');
    const labels = [];
    const data = [];
    
    artistCards.forEach((card, index) => {
        const artistName = card.querySelector('h3').textContent;
        const popularity = 100 - (index * 8); // Simulate popularity based on ranking
        
        labels.push(artistName);
        data.push(popularity);
    });
    
    return { labels, data };
}

function getTracksChartData() {
    // Extract data from the DOM
    const trackItems = document.querySelectorAll('.track-item');
    const labels = [];
    const data = [];
    
    trackItems.forEach((item, index) => {
        const trackName = item.querySelector('h3').textContent;
        const popularity = 100 - (index * 6); // Simulate popularity based on ranking
        
        labels.push(trackName);
        data.push(popularity);
    });
    
    return { labels, data };
}

function getGenresChartData() {
    // Extract data from the DOM
    const genreItems = document.querySelectorAll('.genre-item');
    const labels = [];
    const data = [];
    
    genreItems.forEach(item => {
        const genreName = item.querySelector('.genre-name').textContent;
        const genreCount = parseInt(item.querySelector('.genre-count').textContent);
        
        labels.push(genreName);
        data.push(genreCount);
    });
    
    return { labels, data };
}

function setupEventListeners() {
    // Search functionality
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            filterContent(searchTerm);
        });
    }
    
    // Hover effects for cards
    const cards = document.querySelectorAll('.stat-card, .artist-card, .track-item');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
    
    // Audio metric bars animation
    const metricBars = document.querySelectorAll('.metric-fill');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const bar = entry.target;
                const width = bar.style.width;
                bar.style.width = '0%';
                setTimeout(() => {
                    bar.style.width = width;
                }, 100);
            }
        });
    });
    
    metricBars.forEach(bar => observer.observe(bar));
}

function filterContent(searchTerm) {
    const artistCards = document.querySelectorAll('.artist-card');
    const trackItems = document.querySelectorAll('.track-item');
    
    // Filter artists
    artistCards.forEach(card => {
        const artistName = card.querySelector('h3').textContent.toLowerCase();
        const genres = Array.from(card.querySelectorAll('.genre-tag'))
            .map(tag => tag.textContent.toLowerCase());
        
        const matches = artistName.includes(searchTerm) || 
                       genres.some(genre => genre.includes(searchTerm));
        
        card.style.display = matches ? 'block' : 'none';
    });
    
    // Filter tracks
    trackItems.forEach(item => {
        const trackName = item.querySelector('h3').textContent.toLowerCase();
        const artistName = item.querySelector('p').textContent.toLowerCase();
        const albumName = item.querySelector('.album-name').textContent.toLowerCase();
        
        const matches = trackName.includes(searchTerm) || 
                       artistName.includes(searchTerm) || 
                       albumName.includes(searchTerm);
        
        item.style.display = matches ? 'flex' : 'none';
    });
}

function updateDataForTimeRange(timeRange) {
    // Show loading state
    showLoading();
    
    // Fetch new data from API
    fetch(`/api/audio-features/${timeRange}`)
        .then(response => response.json())
        .then(data => {
            updateAudioMetrics(data);
            hideLoading();
        })
        .catch(error => {
            console.error('Error fetching data:', error);
            hideLoading();
        });
}

function updateAudioMetrics(data) {
    // Update metric values and bars
    const metrics = ['energy', 'danceability', 'valence', 'acousticness', 'instrumentalness', 'tempo'];
    
    metrics.forEach(metric => {
        const metricCard = document.querySelector(`[data-metric="${metric}"]`);
        if (metricCard && data[`avg_${metric}`] !== undefined) {
            const valueElement = metricCard.querySelector('.metric-value');
            const barElement = metricCard.querySelector('.metric-fill');
            
            if (metric === 'tempo') {
                valueElement.textContent = `${Math.round(data[`avg_${metric}`])} BPM`;
                barElement.style.width = `${(data[`avg_${metric}`] / 200) * 100}%`;
            } else {
                valueElement.textContent = `${(data[`avg_${metric}`] * 100).toFixed(1)}%`;
                barElement.style.width = `${data[`avg_${metric}`] * 100}%`;
            }
        }
    });
    
    // Update insights
    if (data.mood) {
        const moodElement = document.querySelector('.insight-card:first-child .insight-value');
        if (moodElement) {
            moodElement.textContent = data.mood;
        }
    }
    
    if (data.dance_style) {
        const danceElement = document.querySelector('.insight-card:last-child .insight-value');
        if (danceElement) {
            danceElement.textContent = data.dance_style;
        }
    }
}

function showLoading() {
    const contentWrapper = document.querySelector('.content-wrapper');
    if (contentWrapper) {
        const loading = document.createElement('div');
        loading.className = 'loading';
        loading.innerHTML = '<div class="loading-spinner"></div>';
        contentWrapper.appendChild(loading);
    }
}

function hideLoading() {
    const loading = document.querySelector('.loading');
    if (loading) {
        loading.remove();
    }
}

function loadInitialData() {
    // Load recent activity
    fetch('/api/recent-activity')
        .then(response => response.json())
        .then(data => {
            updateRecentActivity(data);
        })
        .catch(error => {
            console.error('Error loading recent activity:', error);
        });
}

function updateRecentActivity(data) {
    const recentTracksContainer = document.querySelector('.recent-tracks');
    if (recentTracksContainer && data.items) {
        recentTracksContainer.innerHTML = '';
        
        data.items.slice(0, 10).forEach(item => {
            const trackElement = createRecentTrackElement(item);
            recentTracksContainer.appendChild(trackElement);
        });
    }
}

function createRecentTrackElement(item) {
    const trackDiv = document.createElement('div');
    trackDiv.className = 'recent-track';
    
    const track = item.track;
    const playedAt = new Date(item.played_at).toLocaleDateString();
    
    trackDiv.innerHTML = `
        <div class="track-image">
            <img src="${track.album.images[0]?.url || '/static/default-track.png'}" alt="${track.name}">
        </div>
        <div class="track-info">
            <h3>${track.name}</h3>
            <p>${track.artists[0].name}</p>
        </div>
        <div class="played-at">${playedAt}</div>
    `;
    
    return trackDiv;
}

// Utility functions
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

function formatDuration(ms) {
    const minutes = Math.floor(ms / 60000);
    const seconds = Math.floor((ms % 60000) / 1000);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

// Add smooth scrolling for navigation
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Add keyboard navigation
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        // Close any open modals or dropdowns
        const activeDropdowns = document.querySelectorAll('.dropdown.active');
        activeDropdowns.forEach(dropdown => dropdown.classList.remove('active'));
    }
});

// Add touch support for mobile
let touchStartX = 0;
let touchEndX = 0;

document.addEventListener('touchstart', function(e) {
    touchStartX = e.changedTouches[0].screenX;
});

document.addEventListener('touchend', function(e) {
    touchEndX = e.changedTouches[0].screenX;
    handleSwipe();
});

function handleSwipe() {
    const swipeThreshold = 50;
    const diff = touchStartX - touchEndX;
    
    if (Math.abs(diff) > swipeThreshold) {
        if (diff > 0) {
            // Swipe left - next section
            navigateToNextSection();
        } else {
            // Swipe right - previous section
            navigateToPreviousSection();
        }
    }
}

function navigateToNextSection() {
    const activeSection = document.querySelector('.content-section.active');
    const nextSection = activeSection.nextElementSibling;
    
    if (nextSection && nextSection.classList.contains('content-section')) {
        const nextNavItem = document.querySelector(`[data-section="${nextSection.id}"]`);
        if (nextNavItem) {
            nextNavItem.click();
        }
    }
}

function navigateToPreviousSection() {
    const activeSection = document.querySelector('.content-section.active');
    const prevSection = activeSection.previousElementSibling;
    
    if (prevSection && prevSection.classList.contains('content-section')) {
        const prevNavItem = document.querySelector(`[data-section="${prevSection.id}"]`);
        if (prevNavItem) {
            prevNavItem.click();
        }
    }
}
