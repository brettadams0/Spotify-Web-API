document.addEventListener('DOMContentLoaded', function() {
    // Artist filter
    const artistFilter = document.getElementById('artistFilter');
    artistFilter.addEventListener('input', function() {
        const filter = artistFilter.value.toLowerCase();
        const artistList = document.getElementById('artistList');
        const artists = artistList.getElementsByTagName('li');

        Array.from(artists).forEach(function(artist) {
            const artistName = artist.textContent.toLowerCase();
            if (artistName.includes(filter)) {
                artist.style.display = '';
            } else {
                artist.style.display = 'none';
            }
        });
    });

    // Track filter
    const trackFilter = document.getElementById('trackFilter');
    trackFilter.addEventListener('input', function() {
        const filter = trackFilter.value.toLowerCase();
        const trackList = document.getElementById('trackList');
        const tracks = trackList.getElementsByTagName('li');

        Array.from(tracks).forEach(function(track) {
            const trackName = track.textContent.toLowerCase();
            if (trackName.includes(filter)) {
                track.style.display = '';
            } else {
                track.style.display = 'none';
            }
        });
    });
});
