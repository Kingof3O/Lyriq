  // ---------------------------------------------------------------------------
  // Lyrics rendering
  // ---------------------------------------------------------------------------

  function normalizeLine(line) {
    var time = Number(line && (line.time !== undefined ? line.time : line.timestamp));
    return {
      time: isFinite(time) ? time : -1,
      original: String((line && (line.original !== undefined ? line.original : line.text)) || ''),
      translation: String((line && line.translation) || ''),
      romaji: String((line && line.romaji) || '')
    };
  }

  function lineText(line) {
    if (!line) return '';
    return [line.original, line.translation].filter(Boolean).join('\n').trim();
  }

  function setLanguage(language) {
    var normalized = String(language || '').toLowerCase();
    AppState.language = normalized || 'unknown';
    var known = normalized && normalized !== 'unknown';
    var base = normalized.split('-')[0];
    var code = base.toUpperCase();
    if (base === 'fil') code = 'FIL';
    el.flagBadge.hidden = !known;
    el.flagBadge.textContent = code;
    el.flagBadge.title = known ? (LANG_NAMES[normalized] || normalized) : '';
    el.stageLang.hidden = !known;
    el.stageLang.textContent = code;
    updateRomanizationLabel(normalized);
  }

  function romanizationLabel(language) {
    var normalized = String(language || '').toLowerCase();
    if (normalized.indexOf('zh') === 0) return 'Pinyin';
    if (normalized.indexOf('ja') === 0) return 'Romaji';
    if (normalized.indexOf('ko') === 0) return 'Romaja';
    return 'Romanization';
  }

  function updateRomanizationLabel(language) {
    if (el.romajiSettingsLabel) {
      el.romajiSettingsLabel.textContent = 'Phonetics (' + romanizationLabel(language) + ')';
    }
  }

  function setProvider(provider, synced) {
    AppState.provider = String(provider || '').toUpperCase();
    AppState.isSynced = synced !== false;
    var showProvider = !!AppState.provider && AppState.provider !== 'UNSYNCED';
    el.providerBadge.hidden = !showProvider;
    el.providerBadge.textContent = AppState.provider;
    el.providerBadge.title = AppState.provider ? 'Lyrics provider: ' + AppState.provider : '';
    el.stageProvider.hidden = !showProvider;
    el.stageProvider.textContent = AppState.provider;
    el.syncBadge.hidden = AppState.isSynced;
    el.body.classList.toggle('lyrics-static', !AppState.isSynced);
    el.body.dataset.lyricsSynced = AppState.isSynced ? 'true' : 'false';
  }

  function showTranslationStatus(show) {
    clearTimeout(AppState.translationTimer);
    AppState.translationTimer = null;
    el.translationStatus.hidden = !show;
    if (show) {
      AppState.translationTimer = setTimeout(function () {
        el.translationStatus.hidden = true;
      }, 20000);
    }
  }

  function resetLyricsScroll() {
    AppState.userScrollUntil = 0;
    el.lyricsViewport.style.scrollBehavior = 'auto';
    el.lyricsViewport.scrollTop = 0;
    el.lyricsViewport.style.scrollBehavior = '';
  }

  function showSkeleton() {
    clearTimeout(AppState.skeletonTimer);
    setProvider('', true);
    setLanguage('unknown');
    showTranslationStatus(false);
    resetLyricsScroll();
    el.idleState.hidden = true;
    el.lyricsList.hidden = true;
    el.noLyricsState.hidden = true;
    el.skeletonState.hidden = false;
    hideInstrumental();
    AppState.skeletonTimer = setTimeout(function () {
      if (el.skeletonState.hidden) return;
      el.skeletonState.hidden = true;
      showError(
        isOnline() ? 'Still looking for lyrics' : 'You are offline',
        isOnline() ? 'The lyrics service did not answer in time. Retry or search manually.' : 'Lyrics need a network connection. Reconnect and retry.',
        !isOnline()
      );
    }, 20000);
  }

  function hideSkeleton() {
    clearTimeout(AppState.skeletonTimer);
    AppState.skeletonTimer = null;
    el.skeletonState.hidden = true;
  }

  function showError(title, message, offline) {
    hideSkeleton();
    showTranslationStatus(false);
    resetLyricsScroll();
    el.idleState.hidden = true;
    el.lyricsList.hidden = true;
    el.errorTitle.textContent = title || 'No lyrics found';
    el.errorMessage.textContent = message || 'This track has no lyrics in the library yet.';
    el.errorIcon.replaceChildren(icon(offline ? 'cloud-off' : 'search'));
    el.noLyricsState.hidden = false;
    hideInstrumental();
    clearSynchronizedState();
    AppState.lyrics = [];
    el.miniLyricsScroll.replaceChildren();
    el.miniOriginal.textContent = 'No lyrics';
    el.miniRomaji.textContent = '';
    el.miniTranslation.textContent = '';
  }

  function showIdle() {
    hideSkeleton();
    showTranslationStatus(false);
    resetLyricsScroll();
    el.idleState.hidden = false;
    el.lyricsList.hidden = true;
    el.noLyricsState.hidden = true;
    el.skeletonState.hidden = true;
    el.miniLyricsScroll.replaceChildren();
    setProvider('', true);
    setLanguage('unknown');
    hideInstrumental();
    if (AppState.hasTrack) setMiniFromLine(null);
  }

  function renderLyricsList() {
    var fragment = document.createDocumentFragment();
    var isTransOnly = AppState.lyricViewMode === 'trans-only';
    AppState.lyrics.forEach(function (line, index) {
      var lineEl = document.createElement('div');
      lineEl.className = 'lyric-line';
      if (line.time < 0) lineEl.classList.add('untimed');
      if (!line.translation || !line.translation.trim()) lineEl.classList.add('no-trans');
      lineEl.id = 'line-' + index;
      lineEl.dataset.index = String(index);
      lineEl.dataset.time = String(line.time);
      lineEl.setAttribute('role', 'listitem');

      var origRtl = isRtlText(line.original);
      var transRtl = isRtlText(line.translation);
      var lineRtl = isTransOnly ? (transRtl || (!line.translation && origRtl)) : origRtl;
      if (lineRtl) lineEl.classList.add('is-rtl');

      var original = document.createElement('div');
      original.className = 'line-original';
      original.id = 'orig-' + index;
      original.textContent = line.original;
      if (origRtl) {
        original.classList.add('is-rtl');
        original.dir = 'rtl';
      }

      var romaji = document.createElement('div');
      romaji.className = 'line-romaji';
      romaji.id = 'romaji-' + index;
      romaji.textContent = line.romaji;

      var translation = document.createElement('div');
      translation.className = 'line-translation';
      translation.id = 'trans-' + index;
      translation.textContent = line.translation;
      if (transRtl) {
        translation.classList.add('is-rtl');
        translation.dir = 'rtl';
      }

      lineEl.appendChild(original);
      lineEl.appendChild(romaji);
      lineEl.appendChild(translation);
      fragment.appendChild(lineEl);
    });
    el.lyricsList.replaceChildren(fragment);
    el.lyricsList.hidden = false;
  }

