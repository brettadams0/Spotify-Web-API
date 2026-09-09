/* Spotify Stats — progressive enhancement.
   Every page works without this file; it adds filtering, chart movement
   arrows, the now-playing widget, and playlist export. */
(function () {
  'use strict';

  /* ----------------------------------------------------------------------
     List filtering
     ---------------------------------------------------------------------- */

  function initFilters() {
    document.querySelectorAll('input[data-filter-target]').forEach(function (input) {
      var list = document.querySelector(input.dataset.filterTarget);
      if (!list) return;

      var rows = Array.prototype.slice.call(list.querySelectorAll('[data-search]'));
      var empty = document.querySelector('[data-no-results]');

      function apply() {
        var query = input.value.trim().toLowerCase();
        var shown = 0;

        rows.forEach(function (row) {
          var match = !query || row.dataset.search.indexOf(query) !== -1;
          // Tiles carry data-search on the anchor; hide the <li> around it.
          var target = row.tagName === 'A' ? row.parentElement || row : row;
          target.classList.toggle('is-hidden', !match);
          if (match) shown += 1;
        });

        list.hidden = shown === 0;
        if (empty) empty.hidden = shown !== 0;
      }

      input.addEventListener('input', apply);
      apply();
    });
  }

  /* ----------------------------------------------------------------------
     Chart movement since your last visit

     Rankings are snapshotted in this browser only — nothing is sent to a
     server. A snapshot is refreshed at most once every SNAPSHOT_MAX_AGE so
     that revisiting a page later the same day still shows real movement.
     ---------------------------------------------------------------------- */

  var SNAPSHOT_MAX_AGE = 12 * 60 * 60 * 1000;

  function readSnapshot(key) {
    try {
      var raw = window.localStorage.getItem(key);
      return raw ? JSON.parse(raw) : null;
    } catch (err) {
      return null;
    }
  }

  function writeSnapshot(key, ranks) {
    try {
      window.localStorage.setItem(key, JSON.stringify({ at: Date.now(), ranks: ranks }));
    } catch (err) {
      /* Private mode or a full quota: movement arrows are optional. */
    }
  }

  var DELTA_STATES = ['delta-up', 'delta-down', 'delta-new', 'delta-same'];

  function renderDelta(node, previous, current) {
    // classList, not className: on an artist tile the node also carries
    // .tile-delta, which is what positions it over the artwork. Overwriting
    // className would drop it and push the badge into the layout flow.
    DELTA_STATES.forEach(function (state) { node.classList.remove(state); });
    node.classList.add('delta');

    if (previous === undefined) {
      node.textContent = 'NEW';
      node.classList.add('delta-new');
      node.title = 'New to this chart';
    } else if (previous === current) {
      node.textContent = '–';
      node.classList.add('delta-same');
      node.title = 'No change since your last visit';
    } else {
      var move = previous - current;
      var up = move > 0;
      node.textContent = (up ? '▲' : '▼') + Math.abs(move);
      node.classList.add(up ? 'delta-up' : 'delta-down');
      node.title = 'Moved ' + (up ? 'up ' : 'down ') + Math.abs(move) +
        ' since your last visit';
    }
    node.hidden = false;
  }

  function initDeltas() {
    document.querySelectorAll('[data-chart][data-range]').forEach(function (list) {
      var key = 'spotifystats:' + list.dataset.chart + ':' + list.dataset.range;
      var snapshot = readSnapshot(key);
      var ranks = {};

      list.querySelectorAll('[data-id][data-rank]').forEach(function (item) {
        var id = item.dataset.id;
        var rank = parseInt(item.dataset.rank, 10);
        if (!id || isNaN(rank)) return;
        ranks[id] = rank;

        var badge = item.querySelector('[data-delta]');
        if (badge && snapshot && snapshot.ranks) {
          renderDelta(badge, snapshot.ranks[id], rank);
        }
      });

      if (!snapshot || Date.now() - (snapshot.at || 0) > SNAPSHOT_MAX_AGE) {
        writeSnapshot(key, ranks);
      }
    });
  }

  /* ----------------------------------------------------------------------
     Now playing
     ---------------------------------------------------------------------- */

  var NOW_PLAYING_INTERVAL = 30000;

  function initNowPlaying() {
    var box = document.getElementById('now-playing');
    if (!box) return;

    var art = document.getElementById('np-art');
    var title = document.getElementById('np-title');
    var artist = document.getElementById('np-artist');
    var link = document.getElementById('np-link');
    var timer = null;

    function poll() {
      fetch('/api/now-playing', { headers: { Accept: 'application/json' } })
        .then(function (res) { return res.ok ? res.json() : null; })
        .then(function (data) {
          if (!data || !data.playing) {
            box.hidden = true;
            return;
          }
          title.textContent = data.name || '';
          artist.textContent = data.artist || '';
          link.href = data.url || '#';
          if (data.image) {
            art.src = data.image;
            art.hidden = false;
          } else {
            art.hidden = true;
          }
          box.hidden = false;
        })
        .catch(function () { /* offline: leave the widget as it is */ });
    }

    function start() {
      if (timer) return;
      poll();
      timer = window.setInterval(poll, NOW_PLAYING_INTERVAL);
    }

    function stop() {
      window.clearInterval(timer);
      timer = null;
    }

    // Polling pauses while the tab is in the background to save battery.
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) stop(); else start();
    });
    if (!document.hidden) start();
  }

  /* ----------------------------------------------------------------------
     Save the current top-tracks chart as a playlist
     ---------------------------------------------------------------------- */

  function initPlaylistExport() {
    var button = document.getElementById('save-playlist');
    var result = document.getElementById('playlist-result');
    if (!button || !result) return;

    button.addEventListener('click', function () {
      var original = button.innerHTML;
      button.disabled = true;
      button.textContent = 'Saving…';
      result.hidden = true;

      fetch('/api/playlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({
          range: button.dataset.range,
          limit: parseInt(button.dataset.count, 10) || 50
        })
      })
        .then(function (res) {
          return res.json().then(function (body) {
            return { ok: res.ok, body: body };
          });
        })
        .then(function (payload) {
          result.innerHTML = '';
          var note = document.createElement('p');

          if (payload.ok) {
            note.className = 'flash flash-success';
            note.textContent = 'Saved "' + payload.body.name + '" with ' +
              payload.body.track_count + ' tracks. ';
            if (payload.body.url) {
              var open = document.createElement('a');
              open.href = payload.body.url;
              open.target = '_blank';
              open.rel = 'noopener';
              open.textContent = 'Open in Spotify ↗';
              note.appendChild(open);
            }
          } else {
            note.className = 'flash flash-error';
            note.textContent = payload.body && payload.body.detail
              ? payload.body.detail
              : 'Could not create the playlist. Please try again.';
          }

          result.appendChild(note);
          result.hidden = false;
        })
        .catch(function () {
          result.innerHTML =
            '<p class="flash flash-error">Could not reach the server. Check your connection.</p>';
          result.hidden = false;
        })
        .finally(function () {
          button.disabled = false;
          button.innerHTML = original;
        });
    });
  }

  /* ----------------------------------------------------------------------
     Localise the recently-played timestamps to the viewer's clock
     ---------------------------------------------------------------------- */

  function initLocalTimes() {
    var nodes = document.querySelectorAll('time[data-relative][datetime]');
    if (!nodes.length || typeof Intl === 'undefined') return;

    var format = new Intl.DateTimeFormat(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short'
    });

    nodes.forEach(function (node) {
      var when = new Date(node.getAttribute('datetime'));
      if (!isNaN(when.getTime())) node.title = format.format(when);
    });
  }

  /* ----------------------------------------------------------------------
     Artwork that fails to load

     A Spotify CDN URL can 404 or be blocked; hiding the broken <img> lets the
     placeholder background behind it show through instead of a broken icon.
     ---------------------------------------------------------------------- */

  // A 1x1 transparent GIF. Pointing a failed <img> at this loads successfully,
  // so the browser stops drawing its broken-image glyph and the placeholder
  // background painted by .is-broken shows through instead. Removing the src
  // is not enough — some browsers keep the glyph.
  var BLANK_PIXEL =
    'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';

  function markBroken(el) {
    if (!el || el.classList.contains('is-broken')) return;
    el.classList.add('is-broken');
    el.src = BLANK_PIXEL;
  }

  function initBrokenArt() {
    // Images can fail while the document is still parsing, before this
    // listener exists, so sweep the ones that already finished loading.
    document.querySelectorAll('img[src]').forEach(function (img) {
      if (img.complete && img.naturalWidth === 0) markBroken(img);
    });

    document.addEventListener('error', function (event) {
      if (event.target && event.target.tagName === 'IMG') markBroken(event.target);
    }, true); // capture: image errors do not bubble
  }

  /* ----------------------------------------------------------------------
     Offline shell
     ---------------------------------------------------------------------- */

  function initServiceWorker() {
    if (!('serviceWorker' in navigator) || location.protocol === 'http:') {
      // Service workers need HTTPS, except on localhost which reports http:
      if (!/^(localhost|127\.0\.0\.1)$/.test(location.hostname)) return;
    }
    navigator.serviceWorker.register('/sw.js').catch(function () {
      /* registration is best-effort */
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    initBrokenArt();
    initFilters();
    initDeltas();
    initNowPlaying();
    initPlaylistExport();
    initLocalTimes();
    initServiceWorker();
  });
})();
