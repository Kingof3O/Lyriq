  // ---------------------------------------------------------------------------
  // Command palette
  // ---------------------------------------------------------------------------

  var paletteState = {
    open: false,
    active: 0,
    items: [],
    history: [],
    vocab: [],
    loadedAt: 0
  };

  function fuzzyScore(query, text) {
    var q = String(query || '').toLowerCase();
    var target = String(text || '').toLowerCase();
    if (!q) return 0;
    var index = 0;
    var score = 0;
    var last = -1;
    for (var i = 0; i < q.length; i++) {
      var found = target.indexOf(q[i], index);
      if (found < 0) return null;
      score += found === 0 ? 0 : (last >= 0 && found === last + 1 ? 0.5 : found - last);
      last = found;
      index = found + 1;
    }
    return score + target.length * 0.02;
  }

  function paletteCommands() {
    var commands = [
      { title: 'Open settings', sub: 'Preferences and tools', icon: 'settings', run: function () { openSettings('appearance'); } },
      { title: 'Search lyrics manually', sub: 'LRCLIB, NetEase and local LRC', icon: 'search', run: openSearchModal },
      { title: 'Song history', sub: 'Preview songs you played', icon: 'history', run: openHistory },
      { title: 'Vocabulary notebook', sub: 'Saved words and definitions', icon: 'book', run: function () { openVocab(''); } },
      { title: 'Toggle mini mode', sub: 'Ctrl+Shift+M', icon: 'pip', run: function () { setMiniMode(!AppState.isMini); } },
      { title: 'Mini mode: Cycle width', sub: '560px → 760px → 960px', icon: 'pip', run: function () { cycleMiniWidth(); } },
      { title: 'Toggle square mode', sub: 'Ctrl+Shift+S', icon: 'square', run: function () { setSquareMode(!AppState.isSquare); } },
      { title: 'Square mode: Cycle size', sub: '320px → 420px → 520px → 640px', icon: 'square', run: function () { cycleSquareSize(); } },
      { title: 'Toggle fullscreen', sub: 'F11', icon: 'expand', run: function () { setFullscreen(!AppState.isFullscreen); } },
      { title: 'Toggle always on top', sub: AppState.pinned ? 'On' : 'Off', icon: 'pin', run: function () { setPinned(!AppState.pinned); } },
      { title: 'Toggle ghost mode', sub: AppState.ghost ? 'On' : 'Off', icon: 'eye-off', run: function () { setGhostMode(!AppState.ghost); } },
      { title: 'Toggle low power', sub: AppState.lowPower ? 'On' : 'Off', icon: 'zap', run: function () { setLowPower(!AppState.lowPower); } },
      { title: 'Toggle Discord presence', sub: AppState.discord ? 'On' : 'Off', icon: 'headphones', run: function () { setDiscord(!AppState.discord); } },
      { title: 'Toggle karaoke sweep', sub: AppState.sweep ? 'On' : 'Off', icon: 'type', run: function () { setSweep(!AppState.sweep); } },
      { title: 'Toggle romanization', sub: AppState.romanization ? 'On' : 'Off', icon: 'globe', run: function () { setRomanization(!AppState.romanization); } },
      { title: 'Theme: System', icon: 'monitor', run: function () { applyTheme('system'); } },
      { title: 'Theme: Dark', icon: 'moon', run: function () { applyTheme('dark'); } },
      { title: 'Theme: Light', icon: 'sun', run: function () { applyTheme('light'); } },
      { title: 'Theme: OLED', icon: 'moon', run: function () { applyTheme('oled'); } },
      { title: 'View: Dual lyrics', sub: 'Original and translation', icon: 'captions', run: function () { setLyricsViewMode('both'); } },
      { title: 'View: Translation only', icon: 'captions', run: function () { setLyricsViewMode('trans-only'); } },
      { title: 'View: Original only', icon: 'captions', run: function () { setLyricsViewMode('orig-only'); } },
      { title: 'Sleep timer: 15 minutes', icon: 'timer', run: function () { setSleepTimer(15); } },
      { title: 'Sleep timer: 30 minutes', icon: 'timer', run: function () { setSleepTimer(30); } },
      { title: 'Sleep timer: 45 minutes', icon: 'timer', run: function () { setSleepTimer(45); } },
      { title: 'Sleep timer: 60 minutes', icon: 'timer', run: function () { setSleepTimer(60); } },
      { title: 'Cancel sleep timer', icon: 'timer', run: function () { setSleepTimer(0); } },
      { title: 'Export LRC', icon: 'file-text', run: exportLrc },
      { title: 'Export SRT', icon: 'captions', run: exportSrt },
      { title: 'Export poster HTML', icon: 'printer', run: exportPoster },
      { title: 'Copy all lyrics', icon: 'copy', run: copyAllLyrics },
      { title: 'Clear cache', icon: 'trash', run: confirmClearCache },
      { title: 'Open local LRC folder', icon: 'folder-open', run: openLrcFolder }
    ];
    if (AppState.isFullscreen) {
      commands.push({ title: 'Toggle split layout', sub: AppState.isSplit ? 'On' : 'Off', icon: 'split', run: function () { setSplit(!AppState.isSplit); } });
    }
    if (AppState.preview) {
      commands.unshift({ title: 'Back to live lyrics', icon: 'arrow-left', run: backToLive });
    }
    LANGS.forEach(function (entry) {
      commands.push({
        title: 'Translate into ' + entry[1],
        sub: entry[0].toUpperCase(),
        icon: 'globe',
        run: function () { setTargetLanguage(entry[0]); }
      });
    });
    return commands;
  }

  function openPalette() {
    closeOverflow();
    closeLineContext();
    paletteState.open = true;
    paletteState.active = 0;
    el.commandPalette.hidden = false;
    el.paletteInput.value = '';
    renderPalette();
    el.paletteInput.focus();
    loadPaletteLibrary();
  }

  function closePalette() {
    paletteState.open = false;
    el.commandPalette.hidden = true;
  }

  function loadPaletteLibrary() {
    if (Date.now() - paletteState.loadedAt < 15000) return;
    var pending = 0;
    if (!historyLoaded && hasApi('get_song_history')) {
      pending++;
      callApi('get_song_history').then(function (items) {
        paletteState.history = Array.isArray(items) ? items : [];
        historyData = paletteState.history;
        historyLoaded = true;
        paletteState.loadedAt = Date.now();
        if (paletteState.open) renderPalette();
      });
    } else {
      paletteState.history = historyData.slice();
    }
    if (!vocabLoaded && hasApi('get_vocab_words')) {
      pending++;
      callApi('get_vocab_words').then(function (words) {
        paletteState.vocab = Array.isArray(words) ? words : [];
        vocabData = paletteState.vocab;
        vocabLoaded = true;
        paletteState.loadedAt = Date.now();
        if (paletteState.open) renderPalette();
      });
    } else {
      paletteState.vocab = vocabData.slice();
    }
    if (pending === 0) paletteState.loadedAt = Date.now();
  }

  function paletteLibraryItems() {
    var items = [];
    paletteState.history.forEach(function (item) {
      items.push({
        title: item.title,
        sub: 'History · ' + (item.artist || ''),
        icon: 'history',
        run: function () { previewSong(item); }
      });
    });
    paletteState.history.forEach(function (item) {
      if (!item.is_favorite) return;
      items.push({
        title: item.title,
        sub: 'Favorite · ' + (item.artist || ''),
        icon: 'heart-filled',
        run: function () { previewSong(item); }
      });
    });
    paletteState.vocab.forEach(function (word) {
      items.push({
        title: word.word,
        sub: 'Vocabulary · ' + (word.meaning || ''),
        icon: 'bookmark',
        run: function () { openVocab(word.word); }
      });
    });
    return items;
  }

  function renderPalette() {
    var query = el.paletteInput.value.trim();
    var source = paletteCommands().concat(paletteLibraryItems());
    var scored = [];
    source.forEach(function (item) {
      var haystack = [item.title, item.sub, item.icon].join(' ');
      var score = fuzzyScore(query, haystack);
      if (score !== null) scored.push({ item: item, score: score });
    });
    scored.sort(function (a, b) { return a.score - b.score; });
    paletteState.items = scored.slice(0, 100).map(function (entry) { return entry.item; });
    paletteState.active = clamp(paletteState.active, 0, Math.max(0, paletteState.items.length - 1));

    if (!paletteState.items.length) {
      var empty = document.createElement('div');
      empty.className = 'palette-empty';
      empty.textContent = query ? 'No matches for “' + query + '”' : 'No commands available.';
      el.paletteList.replaceChildren(empty);
      return;
    }

    var fragment = document.createDocumentFragment();
    paletteState.items.forEach(function (item, index) {
      var button = document.createElement('button');
      button.type = 'button';
      button.className = 'palette-item' + (index === paletteState.active ? ' is-active' : '');
      button.setAttribute('role', 'option');
      button.setAttribute('aria-selected', String(index === paletteState.active));
      var iconWrap = document.createElement('span');
      iconWrap.className = 'palette-icon';
      iconWrap.appendChild(icon(item.icon || 'command'));
      var copy = document.createElement('span');
      copy.className = 'palette-copy';
      var title = document.createElement('span');
      title.className = 'palette-title';
      title.textContent = item.title;
      var sub = document.createElement('span');
      sub.className = 'palette-sub';
      sub.textContent = item.sub || '';
      copy.appendChild(title);
      if (item.sub) copy.appendChild(sub);
      button.appendChild(iconWrap);
      button.appendChild(copy);
      button.addEventListener('mouseenter', function () {
        paletteState.active = index;
        syncPaletteActive();
      });
      button.addEventListener('click', function () { runPaletteItem(item); });
      fragment.appendChild(button);
    });
    el.paletteList.replaceChildren(fragment);
    syncPaletteActive();
  }

  function syncPaletteActive() {
    var nodes = el.paletteList.querySelectorAll('.palette-item');
    Array.prototype.forEach.call(nodes, function (node, index) {
      node.classList.toggle('is-active', index === paletteState.active);
      node.setAttribute('aria-selected', String(index === paletteState.active));
    });
    var active = nodes[paletteState.active];
    if (active) active.scrollIntoView({ block: 'nearest' });
  }

  function runPaletteItem(item) {
    closePalette();
    if (!item || typeof item.run !== 'function') return;
    setTimeout(item.run, 0);
  }

