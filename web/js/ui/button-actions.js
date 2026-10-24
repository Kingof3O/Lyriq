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
    el.sliderFontScale.addEventListener('mousedown', function (e) { e.stopPropagation(); });
    el.sliderFontScale.addEventListener('pointerdown', function (e) { e.stopPropagation(); });
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

    
    if (el.btnSquareBgToggle) el.btnSquareBgToggle.addEventListener('click', toggleSquareBg);
    if (el.btnLikedOpen) el.btnLikedOpen.addEventListener('click', function () { openHistory('liked'); });
    if (el.btnQueueOpen) el.btnQueueOpen.addEventListener('click', openQueue);
    if (el.btnHistoryAll) el.btnHistoryAll.addEventListener('click', function () { currentHistoryFilter = 'all'; updateHistoryFilterUi(); renderHistory(); });
    if (el.btnHistoryLiked) el.btnHistoryLiked.addEventListener('click', function () { currentHistoryFilter = 'liked'; updateHistoryFilterUi(); renderHistory(); });

    // History and vocabulary
    el.btnHistoryClose.addEventListener('click', closeHistory);
    el.historySearch.addEventListener('input', debounce(renderHistory, 120));
    el.historyModal.addEventListener('click', function (event) {
      if (event.target === el.historyModal) closeHistory();
    });
    el.btnVocabClose.addEventListener('click', closeVocab);
  }
