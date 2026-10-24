  window.updatePlaybackState = function (data) {
    if (!data) return;
    var positionMs;
    if (data.position_ms !== undefined && data.position_ms !== null) positionMs = Number(data.position_ms);
    else if (data.position !== undefined && data.position !== null) positionMs = Number(data.position) * 1000;
    if (isFinite(positionMs) && positionMs >= 0) {
      AppState.basePositionMs = positionMs;
      AppState.baseTimestamp = performance.now();
      }
    if (data.playback_rate !== undefined && data.playback_rate !== null) {
      var rate = Number(data.playback_rate);
      AppState.playbackRate = isFinite(rate) && rate > 0 ? clamp(rate, 0.25, 4) : 1;
    }
    if (data.duration_ms !== undefined && data.duration_ms !== null) {
      var duration = Number(data.duration_ms) / 1000;
      if (isFinite(duration) && duration >= 0) {
        AppState.duration = duration;
        AppState.track.duration = duration;
        el.totalTime.textContent = formatTime(duration);
      }
    }
    var playing = data.is_playing !== undefined ? Boolean(data.is_playing) : data.status === 4;
    setPlaying(playing);
    if (!AppState.isScrubbing) renderPosition(currentPositionSeconds());
  };

  window.updateLyrics = function (data) {
    if (editingState) finishLineEdit(false);
    closeLineContext();
    hideSkeleton();
    if (!data || !Array.isArray(data.lines) || data.lines.length === 0) {
      showError(
        isOnline() ? 'No lyrics found' : 'You are offline',
        isOnline()
          ? 'This track has no lyrics in the local, LRCLIB or NetEase libraries. Retry or search manually.'
          : 'Lyrics need a network connection. Reconnect, then retry.',
        !isOnline()
      );
      setProvider('', true);
      setLanguage('unknown');
      showTranslationStatus(false);
      return;
    }

    AppState.lyrics = data.lines.map(normalizeLine);
    AppState.activeIndex = -1;
    var synced = data.is_synced !== false;
    setProvider(data.provider || (synced ? '' : 'UNSYNCED'), synced);
    setLanguage(data.lang || 'unknown');
    renderLyricsList();
    showTranslationStatus(true);
    clearSynchronizedState();

    if (synced) {
      renderPosition(currentPositionSeconds());
      if (AppState.activeIndex < 0) setMiniFromLine(null);
    } else {
      hideInstrumental();
      setMiniUnsynced();
    }

    if (AppState.isMini && AppState.isMiniExpanded) buildMiniLyrics();
    updateOffsetDisplay();
  };

  window.updateTranslations = function (data) {
    if (!data || !Array.isArray(data.lines)) return;
    if (data.lang && data.lang !== 'unknown') setLanguage(data.lang);

    var isTransOnly = AppState.lyricViewMode === 'trans-only';
    data.lines.forEach(function (item, index) {
      if (index >= AppState.lyrics.length) return;
      var tr = String(item.translation || '').trim();
      AppState.lyrics[index].translation = String(item.translation || '');
      AppState.lyrics[index].romaji = String(item.romaji || '');
      var transRtl = isRtlText(tr);
      var origRtl = isRtlText(AppState.lyrics[index].original);

      var lineEl = $('line-' + index);
      if (lineEl) {
        lineEl.classList.toggle('no-trans', !tr);
        var lineRtl = isTransOnly ? (transRtl || (!tr && origRtl)) : origRtl;
        lineEl.classList.toggle('is-rtl', lineRtl);
      }
      var transEl = $('trans-' + index);
      if (transEl) {
        transEl.textContent = AppState.lyrics[index].translation;
        transEl.classList.toggle('is-rtl', transRtl);
        transEl.dir = transRtl ? 'rtl' : 'ltr';
      }
      var romajiEl = $('romaji-' + index);
      if (romajiEl) romajiEl.textContent = AppState.lyrics[index].romaji;
      var miniTrans = $('mini-trans-' + index);
      if (miniTrans) {
        miniTrans.textContent = AppState.lyrics[index].translation;
        miniTrans.classList.toggle('is-rtl', transRtl);
        miniTrans.dir = transRtl ? 'rtl' : 'ltr';
      }
      var miniItem = $('mini-line-' + index);
      if (miniItem) {
        miniItem.classList.toggle('no-trans', !tr);
        var miniRtl = isTransOnly ? (transRtl || (!tr && origRtl)) : origRtl;
        miniItem.classList.toggle('is-rtl', miniRtl);
      }
    });

    showTranslationStatus(false);

    if (AppState.activeIndex >= 0) {
      updateMiniLine(AppState.activeIndex);
      var activeNode = $('line-' + AppState.activeIndex);
      if (activeNode) setupActiveSublines(activeNode, AppState.activeIndex);
    } else if (!AppState.isSynced) {
      var first = AppState.lyrics.find(function (line) { return line.original; });
      if (first && (first.translation || first.romaji)) setMiniFromLine(first);
      else setMiniUnsynced();
    }
  };

  // Compatibility hook used by the backend and older callers.
  window.updatePosition = function (seconds, isSeek) {
    var value = Number(seconds);
    if (!isFinite(value)) return;
    if (isSeek) {
      AppState.basePositionMs = Math.max(0, value) * 1000;
      AppState.baseTimestamp = performance.now();
      }
    renderPosition(value);
  };

