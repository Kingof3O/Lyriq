  // ---------------------------------------------------------------------------
  // History and vocabulary
  // ---------------------------------------------------------------------------

  var historyData = [];
  var historyLoaded = false;
  var currentHistoryFilter = 'all';
  var vocabData = [];
  var vocabLoaded = false;

  function updateHistoryFilterUi() {
    var btnAll = $('btnHistoryAll');
    var btnLiked = $('btnHistoryLiked');
    if (btnAll) btnAll.classList.toggle('active', currentHistoryFilter === 'all');
    if (btnLiked) btnLiked.classList.toggle('active', currentHistoryFilter === 'liked');
    var title = $('historyTitle');
    if (title) title.textContent = currentHistoryFilter === 'liked' ? 'Liked songs' : 'Song history';
    if (el.historySearch) {
      el.historySearch.placeholder = currentHistoryFilter === 'liked' ? 'Search liked songs…' : 'Search songs…';
    }
  }

  function openHistory(filter) {
    if (filter === 'liked') currentHistoryFilter = 'liked';
    else if (filter === 'all') currentHistoryFilter = 'all';
    updateHistoryFilterUi();
    closeSettings();
    closeOverflow();
    historyLoaded = false;
    el.historyModal.hidden = false;
    el.historySearch.value = '';
    renderHistory();
    el.historyModal.querySelector('.modal').focus();
  }

  function closeHistory() { el.historyModal.hidden = true; }

  function renderHistory() {
    if (!historyLoaded) {
      el.historyList.replaceChildren(modalEmpty('history', 'Loading history…'));
      if (!hasApi('get_song_history')) {
        historyLoaded = true;
        el.historyList.replaceChildren(modalEmpty('history', 'Song history is unavailable in this build.'));
        return;
      }
      callApi('get_song_history').then(function (items) {
        historyData = Array.isArray(items) ? items : [];
        historyLoaded = true;
        renderHistory();
      });
      return;
    }
    var query = el.historySearch.value.trim().toLowerCase();
    var items = historyData.filter(function (item) {
      if (currentHistoryFilter === 'liked' && !item.is_favorite) return false;
      if (!query) return true;
      return [item.title, item.artist, item.album].join(' ').toLowerCase().indexOf(query) >= 0;
    });
    if (!items.length) {
      var emptyMsg = query ? 'No songs match this search.' : (currentHistoryFilter === 'liked' ? 'No liked songs yet. Click the heart icon on any song to add it here.' : 'No song history yet. Play something in Spotify.');
      el.historyList.replaceChildren(modalEmpty('history', emptyMsg));
      return;
    }
    var fragment = document.createDocumentFragment();
    items.forEach(function (item) {
      var row = document.createElement('button');
      row.type = 'button';
      row.className = 'row-item';
      appendThumb(row, item.thumbnail);
      var info = document.createElement('span');
      info.className = 'row-info';
      var title = document.createElement('span');
      title.className = 'row-title';
      title.textContent = item.title || 'Unknown title';
      var sub = document.createElement('span');
      sub.className = 'row-sub';
      sub.textContent = [item.artist, item.album].filter(Boolean).join(' · ') || 'Unknown artist';
      info.appendChild(title);
      info.appendChild(sub);
      row.appendChild(info);
      if (item.is_favorite) {
        var side = document.createElement('span');
        side.className = 'row-side';
        side.appendChild(icon('heart-filled'));
        row.appendChild(side);
      }
      row.addEventListener('click', function () { previewSong(item); });
      fragment.appendChild(row);
    });
    el.historyList.replaceChildren(fragment);
  }

  function appendThumb(parent, thumbnail) {
    if (thumbnail) {
      var image = document.createElement('img');
      image.className = 'row-thumb';
      image.alt = '';
      image.src = thumbnail;
      parent.appendChild(image);
      return;
    }
    var fallback = document.createElement('span');
    fallback.className = 'row-thumb row-thumb-fallback';
    fallback.appendChild(icon('music'));
    parent.appendChild(fallback);
  }

  function modalEmpty(iconName, message) {
    var wrap = document.createElement('div');
    wrap.className = 'modal-empty';
    wrap.appendChild(icon(iconName));
    var text = document.createElement('span');
    text.textContent = message;
    wrap.appendChild(text);
    return wrap;
  }

  function previewSong(item) {
    if (!item || !item.artist || !item.title) return;
    if (!hasApi('load_history_song')) {
      showToast('History preview is unavailable in this build.', { icon: 'alert', tone: 'danger' });
      return;
    }
    closeHistory();
    AppState.preview = { artist: item.artist, title: item.title };
    el.previewBanner.hidden = false;
    el.previewLabel.textContent = 'Preview: ' + item.title + ' — ' + item.artist;
    showToast('Previewing ' + item.title, { icon: 'history', duration: 2600 });
    showSkeleton();
    callApi('load_history_song', item.artist, item.title);
  }

  function backToLive() {
    AppState.preview = null;
    el.previewBanner.hidden = true;
    showSkeleton();
    callApi('retry_lyrics');
    showToast('Returning to live lyrics', { icon: 'arrow-left' });
  }


  window.openHistory = openHistory;
