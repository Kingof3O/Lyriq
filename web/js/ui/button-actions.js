  // ---------------------------------------------------------------------------
  // Interaction wiring
  // ---------------------------------------------------------------------------

  function wireButtonActions() {
    // Playback
    el.btnPlayPause.addEventListener('click', function () { callApi('play_pause'); });
    el.btnMiniPlay.addEventListener('click', function () { callApi('play_pause'); });
    el.btnSquarePlay && el.btnSquarePlay.addEventListener('click', function () { callApi('play_pause'); });
    el.btnPrev.addEventListener('click', function () { callApi('prev_track'); });
    el.btnSquarePrev && el.btnSquarePrev.addEventListener('click', function () { callApi('prev_track'); });
    el.btnNext.addEventListener('click', function () { callApi('next_track'); });
    el.btnMiniNext.addEventListener('click', function () { callApi('next_track'); });
    el.btnSquareNext && el.btnSquareNext.addEventListener('click', function () { callApi('next_track'); });
    el.btnHeart.addEventListener('click', toggleFavorite);
    el.btnMiniOpen.addEventListener('click', function () { setMiniMode(false, { announce: true }); });
    el.btnMiniSquare && el.btnMiniSquare.addEventListener('click', function () { setMiniMode(false, { persist: false, backend: false }); setSquareMode(true, { announce: true }); });
    el.btnMiniLyrics.addEventListener('click', function () { setMiniExpanded(!AppState.isMiniExpanded); });
    el.btnMiniPin.addEventListener('click', function () { setPinned(!AppState.pinned, { announce: true }); });
    el.btnMiniClose.addEventListener('click', function () { callApi('close'); });

    // Square mode controls
    el.btnSquare && el.btnSquare.addEventListener('click', function () { setSquareMode(!AppState.isSquare, { announce: true }); });
    el.btnSquareExpand && el.btnSquareExpand.addEventListener('click', function () { setSquareMode(false, { announce: true }); });
    el.btnSquareClose && el.btnSquareClose.addEventListener('click', function () { callApi('close'); });
    el.btnSquarePin && el.btnSquarePin.addEventListener('click', function () { setPinned(!AppState.pinned, { announce: true }); });
    el.btnSquareViewMode && el.btnSquareViewMode.addEventListener('click', cycleViewMode);
    el.btnSquareToMini && el.btnSquareToMini.addEventListener('click', function () { setSquareMode(false, { persist: false, backend: false }); setMiniMode(true, { announce: true }); });
    el.btnSquareToCard && el.btnSquareToCard.addEventListener('click', function () { setSquareMode(false, { announce: true }); });

    // Volume wheel: album art and dock, discoverable via the volume button.
    el.npArtWrap.addEventListener('wheel', handleWheelVolume, { passive: false });
    el.miniArtWrap.addEventListener('wheel', handleWheelVolume, { passive: false });
    el.playerDock.addEventListener('wheel', handleWheelVolume, { passive: false });
    el.btnVolume.addEventListener('click', function () {
      showToast('Scroll over the album art or player to change Windows volume.', { icon: 'volume', duration: 4200 });
    });

    // Window controls
    el.btnMin.addEventListener('click', function () { callApi('minimize'); });
    el.btnClose.addEventListener('click', function () { callApi('close'); });
    el.btnMini.addEventListener('click', function () { setMiniMode(true, { announce: true }); });
    el.btnFullscreen.addEventListener('click', function () { setFullscreen(!AppState.isFullscreen, { announce: true }); });
    el.btnSettings.addEventListener('click', function () { openSettings('appearance'); });
    el.btnOverflow.addEventListener('click', function (event) {
      event.stopPropagation();
      toggleOverflow();
    });
    el.btnSettingsClose.addEventListener('click', closeSettings);
    el.settingsOverlay.addEventListener('click', function (event) {
      if (event.target === el.settingsOverlay) closeSettings();
    });
    el.btnOffsetChip.addEventListener('click', function () { openSettings('lyrics'); });
    el.btnViewMode.addEventListener('click', cycleViewMode);

    // Settings sheet tabs
    Array.prototype.forEach.call(document.querySelectorAll('.sheet-tab'), function (tab) {
      tab.addEventListener('click', function () { setSettingsTab(tab.dataset.tab); });
      tab.addEventListener('keydown', function (event) {
        var tabs = Array.prototype.slice.call(document.querySelectorAll('.sheet-tab'));
        var index = tabs.indexOf(tab);
        if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
          event.preventDefault();
          var next = tabs[(index + (event.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length];
          setSettingsTab(next.dataset.tab);
          next.focus();
        }
      });
    });

    // Theme and lyrics view segmented controls
    Array.prototype.forEach.call(el.themeGroup.querySelectorAll('[data-theme-choice]'), function (button) {
      button.addEventListener('click', function () { applyTheme(button.dataset.themeChoice); });
    });
    Array.prototype.forEach.call(el.viewModeGroup.querySelectorAll('[data-lyrics-mode]'), function (button) {
      button.addEventListener('click', function () { setLyricsViewMode(button.dataset.lyricsMode, { announce: true }); });
    });

    // Switches
    toggleSwitch(el.checkLowPower, function (enabled) { setLowPower(enabled, { announce: true }); });
    toggleSwitch(el.checkRomaji, function (enabled) { setRomanization(enabled); });
    toggleSwitch(el.checkSweep, function (enabled) { setSweep(enabled); });
    toggleSwitch(el.checkLearner, function (enabled) { setWordLookup(enabled); });
    toggleSwitch(el.checkDiscord, function (enabled) { setDiscord(enabled, { announce: true }); });
    toggleSwitch(el.checkPin, function (enabled) { setPinned(enabled, { announce: true }); });
    toggleSwitch(el.checkGhost, function (enabled) { setGhostMode(enabled, { announce: true }); });
    toggleSwitch(el.checkStartup, toggleStartup);

    // Slider and offset
    el.sliderFontScale.addEventListener('input', function () { setFontScale(Number(el.sliderFontScale.value) / 100); });
    el.btnNudgeMinus.addEventListener('click', function () { nudgeOffset(-0.2); });
    el.btnNudgePlus.addEventListener('click', function () { nudgeOffset(0.2); });
    el.btnNudgeReset.addEventListener('click', resetOffset);

    // Sleep timer badge
    el.sleepTimerBadge.addEventListener('click', promptSleepTimerCancel);
    el.sleepTimerBadge.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        promptSleepTimerCancel();
      }
    });

    // Overflow menu
    el.menuSearchLyrics.addEventListener('click', function () { closeOverflow(); openSearchModal(); });
    el.menuPalette.addEventListener('click', function () { closeOverflow(); openPalette(); });
    el.menuPin.addEventListener('click', function () { setPinned(!AppState.pinned, { announce: true }); syncMenuChecks(); });
    el.menuGhost.addEventListener('click', function () { setGhostMode(!AppState.ghost, { announce: true }); syncMenuChecks(); });
    el.menuLowPower.addEventListener('click', function () { setLowPower(!AppState.lowPower, { announce: true }); syncMenuChecks(); });
    el.menuDiscord.addEventListener('click', function () { setDiscord(!AppState.discord, { announce: true }); syncMenuChecks(); });
    el.btnSplitLayout.addEventListener('click', function () { setSplit(!AppState.isSplit, { announce: true }); syncMenuChecks(); });
    el.menuHistory.addEventListener('click', function () { closeOverflow(); openHistory(); });
    el.menuVocab.addEventListener('click', function () { closeOverflow(); openVocab(''); });
    el.menuExportLrc.addEventListener('click', function () { closeOverflow(); exportLrc(); });
    el.menuExportSrt.addEventListener('click', function () { closeOverflow(); exportSrt(); });
    el.menuExportSheet.addEventListener('click', function () { closeOverflow(); exportPoster(); });
    el.menuOpenLrc.addEventListener('click', function () { closeOverflow(); openLrcFolder(); });

    // Data actions
    el.btnRefreshCache.addEventListener('click', refreshCacheStats);
    el.btnClearCache.addEventListener('click', confirmClearCache);
    el.btnOpenLrcFolder.addEventListener('click', openLrcFolder);
    el.btnSettingsSearchLyrics.addEventListener('click', openSearchModal);
    el.btnSettingsHistory.addEventListener('click', openHistory);
    el.btnSettingsVocab.addEventListener('click', function () { openVocab(''); });
    el.btnExportLrc.addEventListener('click', exportLrc);
    el.btnExportSrt.addEventListener('click', exportSrt);
    el.btnExportSheet.addEventListener('click', exportPoster);
    el.btnCopyLine.addEventListener('click', copyCurrentLine);
    el.btnCopyAll.addEventListener('click', copyAllLyrics);
    el.searchFolderPath.addEventListener('click', openLrcFolder);

    // History and vocabulary
    el.btnHistoryClose.addEventListener('click', closeHistory);
    el.historySearch.addEventListener('input', debounce(renderHistory, 120));
    el.historyModal.addEventListener('click', function (event) {
      if (event.target === el.historyModal) closeHistory();
    });
    el.btnVocabClose.addEventListener('click', closeVocab);
    el.vocabSearch.addEventListener('input', debounce(renderVocab, 120));
    el.vocabModal.addEventListener('click', function (event) {
      if (event.target === el.vocabModal) closeVocab();
    });
    el.btnExportVocab.addEventListener('click', function () {
      callApi('export_vocab_csv').then(function (message) {
        showToast(message || 'Vocabulary exported to Desktop', { icon: 'download' });
      });
    });
    el.btnBackToLive.addEventListener('click', backToLive);

    // Search modal
    el.btnSearchClose.addEventListener('click', closeSearchModal);
    el.searchModal.addEventListener('click', function (event) {
      if (event.target === el.searchModal) closeSearchModal();
    });
    el.searchForm.addEventListener('submit', function (event) {
      event.preventDefault();
      searchLyrics();
    });
    el.btnSearchOpenFolder.addEventListener('click', openLrcFolder);
    el.btnSearchLyrics.addEventListener('click', openSearchModal);
    el.btnRetry.addEventListener('click', function () {
      showSkeleton();
      callApi('retry_lyrics');
    });

    // Dictionary
    el.btnDictClose.addEventListener('click', function () { el.dictCard.hidden = true; });
    el.btnDictSpeak.addEventListener('click', function () { speakWord(dictState.word, dictState.language); });
    el.btnDictCopy.addEventListener('click', function () {
      var text = dictState.word + (dictState.romaji ? ' (' + dictState.romaji + ')' : '') + ': ' + dictState.meaning;
      copyText(text).then(function () { showToast('Word copied', { icon: 'copy' }); });
    });
    el.btnDictSave.addEventListener('click', function () {
      if (!dictState.word) return;
      if (!hasApi('save_vocab_word')) {
        showToast('Vocabulary is unavailable in this build.', { icon: 'alert', tone: 'danger' });
        return;
      }
      callApi('save_vocab_word', dictState.word, dictState.romaji, dictState.meaning, dictState.language, AppState.track.title)
        .then(function (ok) {
          if (ok === false) {
            showToast('Could not save this word.', { icon: 'alert', tone: 'danger' });
            return;
          }
          el.btnDictSave.classList.add('active');
          vocabLoaded = false;
          showToast('Saved “' + dictState.word + '”', { icon: 'bookmark' });
        });
    });

    // Command palette
    el.paletteInput.addEventListener('input', function () {
      paletteState.active = 0;
      renderPalette();
    });
    el.paletteInput.addEventListener('keydown', function (event) {
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        paletteState.active = Math.min(paletteState.items.length - 1, paletteState.active + 1);
        syncPaletteActive();
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        paletteState.active = Math.max(0, paletteState.active - 1);
        syncPaletteActive();
      } else if (event.key === 'Enter') {
        event.preventDefault();
        if (paletteState.items[paletteState.active]) runPaletteItem(paletteState.items[paletteState.active]);
      } else if (event.key === 'Escape') {
        event.preventDefault();
        event.stopPropagation();
        closePalette();
      }
    });
    el.commandPalette.addEventListener('click', function (event) {
      if (event.target === el.commandPalette) closePalette();
    });

    // Lyric interactions (delegated)
    el.lyricsViewport.addEventListener('wheel', function () {
      AppState.userScrollUntil = Date.now() + 2600;
    }, { passive: true });
    el.lyricsViewport.addEventListener('touchmove', function () {
      AppState.userScrollUntil = Date.now() + 2600;
    }, { passive: true });
    el.lyricsList.addEventListener('click', function (event) {
      if (editingState) return;
      var lineEl = event.target.closest('.lyric-line');
      if (!lineEl || event.target.isContentEditable) return;
      var selection = window.getSelection();
      if (selection && !selection.isCollapsed && selection.toString().trim()) return;
      var index = Number(lineEl.dataset.index);
      var line = AppState.lyrics[index];
      if (line && line.time >= 0) seekTo(Math.max(0, line.time - AppState.offset), true);
    });
    el.lyricsList.addEventListener('contextmenu', function (event) {
      if (editingState) return;
      var lineEl = event.target.closest('.lyric-line');
      if (!lineEl) return;
      event.preventDefault();
      openLineContext(Number(lineEl.dataset.index), event.clientX, event.clientY);
    });
    el.lyricsList.addEventListener('dblclick', function (event) {
      if (editingState) return;
      var original = event.target.closest('.line-original');
      if (!original) return;
      event.stopPropagation();
      var selection = window.getSelection();
      var word = selection ? selection.toString().trim() : '';
      if (!word) word = original.textContent.trim();
      if (word) triggerWordLookup(word, event.clientX, event.clientY);
    });
    el.ctxCopy.addEventListener('click', copyContextLine);
    el.ctxEdit.addEventListener('click', editContextLine);
  }
