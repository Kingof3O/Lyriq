  function setFullscreen(fullscreen, options) {
    var opts = options || {};
    var next = Boolean(fullscreen);
    if (next === AppState.isFullscreen) return;
    if (next && AppState.isMini) setMiniMode(false, { persist: false, backend: false });
    if (next && AppState.isSquare) setSquareMode(false, { persist: false, backend: false });
    AppState.isFullscreen = next;
    el.body.classList.toggle('mode-fullscreen', next);
    el.btnFullscreen.setAttribute('aria-pressed', String(next));
    el.btnSplitLayout.hidden = !next;
    if (!next) {
      el.body.classList.remove('chrome-hidden');
      clearTimeout(chromeTimer);
    } else {
      scheduleChromeHide();
    }
    if (opts.backend !== false) callApi('toggle_fullscreen');
    if (opts.persist !== false) persistSettings({ view_mode: next ? 'fullscreen' : 'card' });
    if (opts.announce) showToast(next ? 'Fullscreen' : 'Windowed', { icon: next ? 'expand' : 'collapse' });
    syncWindowUi();
  }

  function setSplit(enabled, options) {
    var opts = options || {};
    AppState.isSplit = Boolean(enabled);
    AppState.settings.split_layout = AppState.isSplit;
    el.body.classList.toggle('layout-split', AppState.isSplit);
    el.btnSplitLayout.setAttribute('aria-checked', String(AppState.isSplit));
    if (opts.persist !== false) persistSettings({ split_layout: AppState.isSplit });
    if (opts.announce) showToast(AppState.isSplit ? 'Split layout' : 'Centered layout', { icon: 'split' });
  }

  function syncWindowUi() {
    el.btnMini.classList.toggle('active', AppState.isMini);
    el.btnMini.setAttribute('aria-pressed', String(AppState.isMini));
    if (el.btnSquare) {
      el.btnSquare.classList.toggle('active', AppState.isSquare);
      el.btnSquare.setAttribute('aria-pressed', String(AppState.isSquare));
    }
    el.btnFullscreen.classList.toggle('active', AppState.isFullscreen);
    el.btnFullscreen.setAttribute('aria-pressed', String(AppState.isFullscreen));
    el.btnSplitLayout.hidden = !AppState.isFullscreen;
    el.btnMiniPin.setAttribute('aria-pressed', String(AppState.pinned));
    el.btnMiniPin.classList.toggle('active', AppState.pinned);
    if (el.btnSquarePin) {
      el.btnSquarePin.setAttribute('aria-pressed', String(AppState.pinned));
      el.btnSquarePin.classList.toggle('active', AppState.pinned);
    }
  }

  function scheduleChromeHide() {
    clearTimeout(chromeTimer);
    el.body.classList.remove('chrome-hidden');
    if (!AppState.isFullscreen) return;
    chromeTimer = setTimeout(function () {
      if (!AppState.isFullscreen || anyOverlayOpen()) return;
      var focused = document.activeElement;
      if (focused && (el.topbar.contains(focused) || el.playerDock.contains(focused))) return;
      if ((el.topbar.matches && el.topbar.matches(':hover')) || (el.playerDock.matches && el.playerDock.matches(':hover'))) return;
      el.body.classList.add('chrome-hidden');
    }, 3000);
  }

  function anyOverlayOpen() {
    return !el.settingsOverlay.hidden || !el.historyModal.hidden || !el.vocabModal.hidden ||
      !el.searchModal.hidden || !el.commandPalette.hidden || !el.lineContextMenu.hidden || !el.dictCard.hidden;
  }

  function applyWindowMode(mode, options) {
    var opts = options || {};
    if (mode === 'mini') {
      setSquareMode(false, { persist: false, backend: false });
      setMiniMode(true, { persist: false, backend: opts.backend !== false, announce: false });
    } else if (mode === 'square') {
      setMiniMode(false, { persist: false, backend: false });
      setFullscreen(false, { persist: false, backend: false });
      setSquareMode(true, { persist: false, backend: opts.backend !== false, announce: false });
    } else if (mode === 'fullscreen') {
      setMiniMode(false, { persist: false, backend: false });
      setSquareMode(false, { persist: false, backend: false });
      setFullscreen(true, { persist: false, backend: opts.backend !== false, announce: false });
    } else {
      setFullscreen(false, { persist: false, backend: opts.backend !== false });
      setMiniMode(false, { persist: false, backend: opts.backend !== false });
      setSquareMode(false, { persist: false, backend: opts.backend !== false });
      opts.persist = false;
    }
    if (AppState.settings.split_layout) setSplit(true, { persist: false });
  }

  window.applyWindowMode = applyWindowMode;

