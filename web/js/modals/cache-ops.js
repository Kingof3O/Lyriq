  // ---------------------------------------------------------------------------
  // Cache and local LRC folder
  // ---------------------------------------------------------------------------

  function refreshCacheStats() {
    if (!hasApi('get_cache_stats')) {
      el.cacheStats.replaceChildren(cacheStat('Status', 'Unavailable in this build'));
      return;
    }
    callApi('get_cache_stats').then(function (stats) {
      var data = stats || {};
      var counts = data.row_counts || {};
      el.cacheStats.replaceChildren(
        cacheStat('Database', (data.db_size_mb !== undefined ? data.db_size_mb + ' MB' : '—')),
        cacheStat('Lyrics', counts.lyrics_cache !== undefined ? counts.lyrics_cache : (data.lyrics_cache || 0)),
        cacheStat('Translations', counts.translation_cache !== undefined ? counts.translation_cache : (data.translation_cache || 0)),
        cacheStat('Thumbnails', counts.thumbnails !== undefined ? counts.thumbnails : (data.thumbnails || 0))
      );
    });
  }

  function cacheStat(label, value) {
    var row = document.createElement('div');
    var term = document.createElement('dt');
    term.textContent = label;
    var description = document.createElement('dd');
    description.textContent = String(value);
    row.appendChild(term);
    row.appendChild(description);
    return row;
  }

  function confirmClearCache() {
    if (!hasApi('clear_cache')) {
      showToast('Cache management is unavailable in this build.', { icon: 'database', tone: 'danger' });
      return;
    }
    showToast('Clear cached lyrics and translations? Favorites, history and vocabulary are kept.', {
      icon: 'trash',
      tone: 'danger',
      actionLabel: 'Clear cache',
      duration: 7000,
      onAction: function () {
        callApi('clear_cache').then(function () {
          showToast('Cache cleared', { icon: 'check' });
          refreshCacheStats();
        });
      }
    });
  }

  function loadLrcFolder() {
    if (!hasApi('get_lrc_folder')) {
      el.lrcFolderPath.textContent = 'Local LRC folder is unavailable in this build.';
      el.searchFolderPath.textContent = 'Local LRC folder unavailable';
      return;
    }
    callApi('get_lrc_folder').then(function (path) {
      var text = path ? String(path) : 'No LRC folder configured.';
      el.lrcFolderPath.textContent = text;
      el.searchFolderPath.textContent = text;
    });
  }

  function openLrcFolder() {
    if (!hasApi('open_lrc_folder')) {
      showToast('Opening the LRC folder is unavailable in this build.', { icon: 'folder-open', tone: 'danger' });
      return;
    }
    callApi('open_lrc_folder').then(function (ok) {
      if (ok === false) showToast('Could not open the LRC folder.', { icon: 'folder-open', tone: 'danger' });
    });
  }

