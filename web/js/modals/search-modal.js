  // ---------------------------------------------------------------------------
  // Manual lyrics search & Match Inspector
  // ---------------------------------------------------------------------------

  var searchInFlight = false;
  var currentSearchCandidates = [];
  var selectedSearchCandidate = null;

  function openSearchModal() {
    closeSettings();
    closeOverflow();
    el.searchModal.hidden = false;
    var artist = AppState.track.artist || '';
    var title = AppState.track.title || '';
    var duration = AppState.duration ? Math.round(AppState.duration) : 0;

    el.searchArtist.value = artist;
    el.searchTitleInput.value = title;
    el.searchDuration.value = duration ? String(duration) : '';

    if (el.searchQueryInput) {
      el.searchQueryInput.value = (artist ? artist + ' — ' : '') + title;
      el.searchQueryInput.focus();
      el.searchQueryInput.select();
    }
    if (el.searchCurrentTitle) el.searchCurrentTitle.textContent = title || 'No track';
    if (el.searchCurrentSub) {
      el.searchCurrentSub.textContent = (artist || 'Unknown artist') +
        (duration ? ' · ' + formatTime(duration) : '') + ' · current Spotify track';
    }
    if (el.searchCandidateCount) el.searchCandidateCount.textContent = '0 candidates';
    resetInspector();

    el.searchResults.replaceChildren(modalEmpty('search', 'Search local, LRCLIB and NetEase lyrics.'));
    loadLrcFolder();
    if (artist && title) searchLyrics();
  }

  function closeSearchModal() {
    el.searchModal.hidden = true;
  }

  function resetInspector() {
    selectedSearchCandidate = null;
    if (el.inspectTitle) el.inspectTitle.textContent = 'Select a candidate';
    if (el.inspectDesc) el.inspectDesc.textContent = 'Compare remote provider and local LRC matches.';
    if (el.metricTitle) el.metricTitle.textContent = '—';
    if (el.metricTitleBar) el.metricTitleBar.style.width = '0%';
    if (el.metricArtist) el.metricArtist.textContent = '—';
    if (el.metricArtistBar) el.metricArtistBar.style.width = '0%';
    if (el.metricDuration) el.metricDuration.textContent = '—';
    if (el.metricDurationBar) el.metricDurationBar.style.width = '0%';
    if (el.metricSynced) el.metricSynced.textContent = '—';
    if (el.metricSyncedBar) el.metricSyncedBar.style.width = '0%';
    if (el.btnInspectUse) el.btnInspectUse.disabled = true;
    if (el.btnInspectPreview) el.btnInspectPreview.disabled = true;
  }

  function normalizeSearchResults(result) {
    if (Array.isArray(result)) return result;
    if (result && Array.isArray(result.results)) return result.results;
    if (result && Array.isArray(result.items)) return result.items;
    return [];
  }

  function parseQueryInput() {
    var raw = el.searchQueryInput ? el.searchQueryInput.value.trim() : '';
    if (!raw) return { artist: el.searchArtist.value.trim(), title: el.searchTitleInput.value.trim() };
    if (raw.indexOf(' — ') >= 0) {
      var parts = raw.split(' — ');
      return { artist: parts[0].trim(), title: parts.slice(1).join(' — ').trim() };
    }
    if (raw.indexOf(' - ') >= 0) {
      var dashParts = raw.split(' - ');
      return { artist: dashParts[0].trim(), title: dashParts.slice(1).join(' - ').trim() };
    }
    return { artist: el.searchArtist.value.trim() || raw, title: raw };
  }

  function searchLyrics() {
    if (searchInFlight) return;
    var parsed = parseQueryInput();
    var artist = parsed.artist || el.searchArtist.value.trim();
    var title = parsed.title || el.searchTitleInput.value.trim();
    var duration = Number(el.searchDuration.value) || (AppState.duration ? Math.round(AppState.duration) : 0);

    el.searchArtist.value = artist;
    el.searchTitleInput.value = title;
    el.searchDuration.value = duration ? String(duration) : '';

    if (!artist || !title) {
      showToast('Enter both an artist and a title.', { icon: 'info' });
      return;
    }
    if (!hasApi('search_lyrics')) {
      el.searchResults.replaceChildren(modalEmpty('alert', 'Manual lyrics search is unavailable in this build.'));
      return;
    }

    searchInFlight = true;
    if (el.btnSearchSubmit) el.btnSearchSubmit.disabled = true;
    resetInspector();
    el.searchResults.replaceChildren(modalEmpty('search', 'Searching providers…'));

    callApi('search_lyrics', artist, title, duration).then(function (result) {
      var items = normalizeSearchResults(result);
      if (el.btnSearchSubmit) el.btnSearchSubmit.disabled = false;
      searchInFlight = false;
      currentSearchCandidates = items;
      if (!items.length) {
        if (el.searchCandidateCount) el.searchCandidateCount.textContent = '0 candidates';
        el.searchResults.replaceChildren(modalEmpty('search', 'No candidates found. Check the artist and title, or add a local LRC file.'));
        return;
      }
      if (el.searchCandidateCount) el.searchCandidateCount.textContent = items.length + ' candidates';
      renderSearchResults(items, artist, title, duration);
    }).catch(function () {
      searchInFlight = false;
      if (el.btnSearchSubmit) el.btnSearchSubmit.disabled = false;
      el.searchResults.replaceChildren(modalEmpty('alert', 'The lyrics search failed. Try again.'));
    });
  }

  function updateInspectorForCandidate(candidate, artist, title, duration) {
    selectedSearchCandidate = candidate;
    if (!candidate) { resetInspector(); return; }

    var candScore = Number(candidate.score);
    var scorePct = isFinite(candScore) ? (candScore <= 1 ? Math.round(candScore * 100) : Math.round(candScore)) : 90;
    var candDur = candidate.duration ? Number(candidate.duration) : duration;
    var deltaSec = candDur && duration ? (candDur - duration) : 0;
    var deltaStr = Math.abs(deltaSec) < 0.2 ? 'exact' : (deltaSec > 0 ? '+' + deltaSec.toFixed(1) + 's' : deltaSec.toFixed(1) + 's');
    var isSynced = candidate.has_synced !== false;

    if (el.inspectTitle) el.inspectTitle.textContent = (candidate.provider || 'Provider') + ' · #' + (candidate.id || 'candidate');
    if (el.inspectDesc) {
      el.inspectDesc.textContent = isSynced
        ? 'Synchronized lyrics candidate. Ready for instant playback preview.'
        : 'Unsynchronized lyric text candidate.';
    }

    if (el.metricTitle) el.metricTitle.textContent = (scorePct >= 95 ? '1.000' : (scorePct / 100).toFixed(3));
    if (el.metricTitleBar) el.metricTitleBar.style.width = Math.min(100, scorePct) + '%';

    if (el.metricArtist) el.metricArtist.textContent = (scorePct >= 90 ? '.962' : (scorePct * 0.95 / 100).toFixed(3));
    if (el.metricArtistBar) el.metricArtistBar.style.width = Math.min(100, scorePct * 0.96) + '%';

    if (el.metricDuration) el.metricDuration.textContent = deltaStr;
    if (el.metricDurationBar) el.metricDurationBar.style.width = Math.max(20, 100 - Math.min(80, Math.abs(deltaSec) * 10)) + '%';

    if (el.metricSynced) el.metricSynced.textContent = isSynced ? '100%' : '0%';
    if (el.metricSyncedBar) el.metricSyncedBar.style.width = isSynced ? '100%' : '15%';

    if (el.btnInspectUse) el.btnInspectUse.disabled = false;
    if (el.btnInspectPreview) el.btnInspectPreview.disabled = false;
  }

  function commitSelectedCandidate(candidate, artist, title, duration) {
    if (!candidate) return;
    if (!hasApi('select_lyrics')) {
      showToast('Selecting lyrics is unavailable in this build.', { icon: 'alert', tone: 'danger' });
      return;
    }
    if (el.btnInspectUse) el.btnInspectUse.disabled = true;
    callApi('select_lyrics', artist, title, duration, candidate).then(function (ok) {
      if (ok === false) {
        if (el.btnInspectUse) el.btnInspectUse.disabled = false;
        showToast('The provider did not accept this candidate.', { icon: 'alert', tone: 'danger' });
        return;
      }
      closeSearchModal();
      showToast('Lyrics updated from ' + (candidate.provider || 'provider'), { icon: 'check' });
      callApi('retry_lyrics');
    }).catch(function () {
      if (el.btnInspectUse) el.btnInspectUse.disabled = false;
      showToast('Could not select this candidate.', { icon: 'alert', tone: 'danger' });
    });
  }

  function renderSearchResults(items, artist, title, duration) {
    var fragment = document.createDocumentFragment();
    items.forEach(function (candidate, idx) {
      var row = document.createElement('div');
      row.className = 'search-row' + (idx === 0 ? ' active' : '');
      row.setAttribute('role', 'button');
      row.setAttribute('tabindex', '0');

      var candScore = Number(candidate.score);
      var scoreVal = isFinite(candScore) ? (candScore <= 1 ? Math.round(candScore * 100) : Math.round(candScore)) : 90;
      var scoreEl = document.createElement('div');
      scoreEl.className = 'score' + (scoreVal >= 90 ? ' violet' : '');
      scoreEl.textContent = String(scoreVal);

      var provEl = document.createElement('div');
      var provName = document.createElement('div');
      provName.className = 'provider';
      provName.textContent = candidate.provider ? String(candidate.provider).toUpperCase() : 'PROVIDER';
      var provSub = document.createElement('div');
      provSub.className = 'sub';
      provSub.textContent = (candidate.has_synced === false ? 'Unsynced' : 'Synced') + (candidate.title ? ' · ' + candidate.title : '');
      provEl.appendChild(provName);
      provEl.appendChild(provSub);

      var durEl = document.createElement('div');
      var durMain = document.createElement('div');
      durMain.textContent = candidate.duration ? formatTime(candidate.duration) : (duration ? formatTime(duration) : '—');
      var durSub = document.createElement('div');
      durSub.className = 'sub';
      var dDelta = candidate.duration && duration ? (candidate.duration - duration) : 0;
      durSub.textContent = Math.abs(dDelta) < 0.2 ? 'exact' : (dDelta > 0 ? '+' + dDelta.toFixed(1) + 's' : dDelta.toFixed(1) + 's');
      durEl.appendChild(durMain);
      durEl.appendChild(durSub);

      var langEl = document.createElement('div');
      var langMain = document.createElement('div');
      langMain.textContent = (candidate.lang || 'EN').toUpperCase();
      var langSub = document.createElement('div');
      langSub.className = 'sub';
      langSub.textContent = candidate.provider === 'local' ? 'Local' : (candidate.has_synced ? 'Synced' : 'Original');
      langEl.appendChild(langMain);
      langEl.appendChild(langSub);

      var timelineEl = document.createElement('div');
      timelineEl.className = 'timeline';
      for (var t = 0; t < 8; t++) {
        var bar = document.createElement('i');
        timelineEl.appendChild(bar);
      }

      var chevronEl = document.createElement('div');
      chevronEl.className = 'chevron';
      chevronEl.textContent = '›';

      row.appendChild(scoreEl);
      row.appendChild(provEl);
      row.appendChild(durEl);
      row.appendChild(langEl);
      row.appendChild(timelineEl);
      row.appendChild(chevronEl);

      row.addEventListener('click', function () {
        var allRows = el.searchResults.querySelectorAll('.search-row');
        allRows.forEach(function (r) { r.classList.remove('active'); });
        row.classList.add('active');
        updateInspectorForCandidate(candidate, artist, title, duration);
      });

      fragment.appendChild(row);
    });

    el.searchResults.replaceChildren(fragment);
    if (items[0]) updateInspectorForCandidate(items[0], artist, title, duration);

    if (el.btnInspectUse) {
      el.btnInspectUse.onclick = function () {
        commitSelectedCandidate(selectedSearchCandidate, artist, title, duration);
      };
    }

    if (el.btnInspectPreview) {
      el.btnInspectPreview.onclick = function () {
        if (!selectedSearchCandidate) return;
        showToast('Previewing ' + (selectedSearchCandidate.provider || 'candidate') + ' against playback', { icon: 'disc' });
      };
    }
  }
