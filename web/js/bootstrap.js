  // ---------------------------------------------------------------------------
  // Init and global hooks
  // ---------------------------------------------------------------------------

  function bootstrapUi() {
    loadInitialSettings();
    el.root.style.setProperty('--font-scale', String(AppState.settings.font_scale));
    initSelects();
    applyAllSettings();
    wireEvents();
    updateSliderFill(el.sliderFontScale);
    updatePlayIcons();
    updateFavoriteUi(false);
    updateOffsetDisplay();
    showIdle();
    syncWindowUi();
    refreshStartupState();
  }

  window.toggleGhostModeHotKey = function () {
    setGhostMode(!AppState.ghost, { announce: true });
  };

  window.toggleMiniModeHotKey = function () {
    setMiniMode(!AppState.isMini, { announce: true });
  };

  window.toggleSquareModeHotKey = function () {
    setSquareMode(!AppState.isSquare, { announce: true });
  };

  window.cycleViewMode = cycleViewMode;

  window.openSettings = function (tab) {
    openSettings(typeof tab === 'string' ? tab : undefined);
  };

  window.applyPersistedViewMode = function () {
    var mode = AppState.settings.view_mode || 'card';
    applyWindowMode(mode, { backend: false });
  };

  window.applyTheme = function (choice) { applyTheme(choice); };
  window.setTargetLanguage = setTargetLanguage;

  window.addEventListener('pywebviewready', initFromBackend);

  bootstrapUi();

  if (window.pywebview && window.pywebview.api) {
    setTimeout(initFromBackend, 0);
  }
