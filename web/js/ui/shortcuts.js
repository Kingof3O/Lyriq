  // ---------------------------------------------------------------------------
  // Interaction wiring: keyboard shortcuts and global window events
  // ---------------------------------------------------------------------------

  function wireShortcuts() {
    // Global keyboard
    document.addEventListener('keydown', function (event) {
      if (event.key === 'F11') {
        event.preventDefault();
        setFullscreen(!AppState.isFullscreen, { announce: true });
        return;
      }
      if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === 's') {
        event.preventDefault();
        setSquareMode(!AppState.isSquare, { announce: true });
        return;
      }
      if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === 'm') {
        event.preventDefault();
        setMiniMode(!AppState.isMini, { announce: true });
        return;
      }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        if (paletteState.open) closePalette();
        else openPalette();
        return;
      }
      if (event.key === 'Escape') {
        if (paletteState.open) { closePalette(); return; }
        if (!el.lineContextMenu.hidden) { closeLineContext(); return; }
        if (!el.overflowMenu.hidden) { closeOverflow(); return; }
        if (el.dictCard.hidden === false) { el.dictCard.hidden = true; return; }
        if (!el.searchModal.hidden) { closeSearchModal(); return; }
        if (!el.historyModal.hidden) { closeHistory(); return; }
        if (!el.vocabModal.hidden) { closeVocab(); return; }
        if (!el.settingsOverlay.hidden) { closeSettings(); return; }
        if (langSelectInstance && langSelectInstance.open) { langSelectInstance.close(); return; }
        if (sleepSelectInstance && sleepSelectInstance.open) { sleepSelectInstance.close(); return; }
        if (editingState) { finishLineEdit(false); return; }
        if (AppState.isFullscreen) setFullscreen(false, { announce: true });
      }
    });

    // Close transient UI on outside clicks
    document.addEventListener('pointerdown', function (event) {
      if (!el.lineContextMenu.hidden && !el.lineContextMenu.contains(event.target)) closeLineContext();
      if (!el.dictCard.hidden && !el.dictCard.contains(event.target) && !event.target.closest('.line-original')) {
        el.dictCard.hidden = true;
      }
      if (!el.overflowMenu.hidden && !el.overflowMenu.contains(event.target) && !el.btnOverflow.contains(event.target)) {
        closeOverflow();
      }
      if (!el.settingsOverlay.hidden && event.target === el.settingsOverlay) closeSettings();
      if (!event.target.closest || !event.target.closest('.select')) closeAllSelects(null);
      Array.prototype.forEach.call(document.querySelectorAll('[data-tooltip]'), function (node) {
        node.classList.remove('tip-above');
      });
    });

    // Fullscreen chrome auto-hide
    document.addEventListener('mousemove', function () {
      if (AppState.isFullscreen) scheduleChromeHide();
    });
    document.addEventListener('pointerdown', function () {
      if (AppState.isFullscreen) scheduleChromeHide();
    });

    // Visibility: pause the loop when hidden, re-sync on show.
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) {
        stopFrame();
      } else {
        renderPosition(currentPositionSeconds());
        ensureFrame();
      }
    });

    // Follow OS theme changes only in system mode.
    if (systemThemeQuery && systemThemeQuery.addEventListener) {
      systemThemeQuery.addEventListener('change', function () {
        if (AppState.themeChoice === 'system') applyTheme('system', { persist: false });
      });
    }

    // Keep fixed popovers in the viewport.
    window.addEventListener('resize', function () {
      if (!el.dictCard.hidden) el.dictCard.hidden = true;
      closeLineContext();
      if (AppState.activeIndex >= 0) {
        var activeNode = $('line-' + AppState.activeIndex);
        if (activeNode) setupActiveSublines(activeNode, AppState.activeIndex);
      }
    });

    initMiniResize();
    initSquareResize();
  }

  function handleWheelVolume(event) {
    event.preventDefault();
    var delta = event.deltaY < 0 ? 1 : -1;
    callApi('adjust_volume', delta);
    showToast(delta > 0 ? 'Volume up' : 'Volume down', { icon: 'volume', duration: 1500 });
  }

  function wireEvents() {
    wireButtonActions();
    wireScrubber();
    wireShortcuts();
  }
