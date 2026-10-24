  // ---------------------------------------------------------------------------
  // Manual lyrics search
  // ---------------------------------------------------------------------------

  var searchInFlight = false;

  function openSearchModal() {
    closeSettings();
    closeOverflow();
    el.searchModal.hidden = false;
    el.searchArtist.value = AppState.track.artist || '';
    el.searchTitleInput.value = AppState.track.title || '';
    el.searchDuration.value = AppState.duration ? String(Math.round(AppState.duration)) : '';
    el.searchResults.replaceChildren(modalEmpty('search', 'Search local, LRCLIB and NetEase lyrics.'));
    loadLrcFolder();
    el.searchArtist.focus();
    el.searchArtist.select();
  }

  function closeSearchModal() { el.searchModal.hidden = true; }

  function normalizeSearchResults(result) {
    if (Array.isArray(result)) return result;
    if (result && Array.isArray(result.results)) return result.results;
    if (result && Array.isArray(result.items)) return result.items;
    return [];
  }

  function searchLyrics() {
    if (searchInFlight) return;
    var artist = el.searchArtist.value.trim();
    var title = el.searchTitleInput.value.trim();
    var duration = Number(el.searchDuration.value) || 0;
    if (!artist || !title) {
      showToast('Enter both an artist and a title.', { icon: 'info' });
      return;
    }
    if (!hasApi('search_lyrics')) {
      el.searchResults.replaceChildren(modalEmpty('alert', 'Manual lyrics search is unavailable in this build.'));
      return;
    }

    searchInFlight = true;
    el.btnSearchSubmit.disabled = true;
    el.searchResults.replaceChildren(modalEmpty('search', 'Searching providers…'));
    callApi('search_lyrics', artist, title, duration).then(function (result) {
      var items = normalizeSearchResults(result);
      el.btnSearchSubmit.disabled = false;
      searchInFlight = false;
      if (!items.length) {
        el.searchResults.replaceChildren(modalEmpty('search', 'No candidates found. Check the artist and title, or add a local LRC file.'));
        return;
      }
      renderSearchResults(items, artist, title, duration);
    }).catch(function () {
      searchInFlight = false;
      el.btnSearchSubmit.disabled = false;
      el.searchResults.replaceChildren(modalEmpty('alert', 'The lyrics search failed. Try again.'));
    });
  }

  function formatScore(score) {
    var value = Number(score);
    if (!isFinite(value)) return '';
    if (value <= 1) value = value * 100;
    return Math.round(value) + '%';
  }

  function renderSearchResults(items, artist, title, duration) {
    var fragment = document.createDocumentFragment();
    items.forEach(function (candidate) {
      var row = document.createElement('button');
      row.type = 'button';
      row.className = 'search-result';
      var main = document.createElement('span');
      main.className = 'result-main';
      var resultTitle = document.createElement('span');
      resultTitle.className = 'result-title';
      resultTitle.textContent = candidate.title || title;
      var meta = document.createElement('span');
      meta.className = 'result-meta';
      meta.textContent = [candidate.artist || artist, candidate.album, candidate.duration ? formatTime(candidate.duration) : '']
        .filter(Boolean).join(' · ');
      var badges = document.createElement('span');
      badges.className = 'result-badges';
      if (candidate.provider) {
        var provider = document.createElement('span');
        provider.className = 'badge provider-badge';
        provider.textContent = String(candidate.provider).toUpperCase();
        badges.appendChild(provider);
      }
      var sync = document.createElement('span');
      sync.className = 'badge' + (candidate.has_synced === false ? ' unsynced-badge' : '');
      sync.textContent = candidate.has_synced === false ? 'UNSYNCED' : 'SYNCED';
      badges.appendChild(sync);
      if (candidate.score !== undefined) {
        var score = document.createElement('span');
        score.className = 'result-score';
        score.textContent = formatScore(candidate.score);
        badges.appendChild(score);
      }
      main.appendChild(resultTitle);
      main.appendChild(meta);
      row.appendChild(main);
      row.appendChild(badges);

      row.addEventListener('click', function () {
        if (!hasApi('select_lyrics')) {
          showToast('Selecting lyrics is unavailable in this build.', { icon: 'alert', tone: 'danger' });
          return;
        }
        row.disabled = true;
        row.style.opacity = '0.6';
        callApi('select_lyrics', artist, title, duration, candidate).then(function (ok) {
          if (ok === false) {
            row.disabled = false;
            row.style.opacity = '';
            showToast('The provider did not accept this candidate.', { icon: 'alert', tone: 'danger' });
            return;
          }
          closeSearchModal();
          showToast('Lyrics updated from ' + (candidate.provider || 'provider'), { icon: 'check' });
          callApi('retry_lyrics');
        }).catch(function () {
          row.disabled = false;
          row.style.opacity = '';
          showToast('Could not select this candidate.', { icon: 'alert', tone: 'danger' });
        });
      });
      fragment.appendChild(row);
    });
    el.searchResults.replaceChildren(fragment);
  }

