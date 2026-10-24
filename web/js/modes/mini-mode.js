  // ---------------------------------------------------------------------------
  // Window modes: card, mini, fullscreen, split
  // ---------------------------------------------------------------------------

  var chromeTimer = null;

  function setMiniMode(mini, options) {
    var opts = options || {};
    var next = Boolean(mini);
    if (next === AppState.isMini) {
      if (next && opts.force) refreshMini();
      return;
    }
    if (next) {
      if (AppState.isFullscreen) {
        AppState.isFullscreen = false;
        el.body.classList.remove('mode-fullscreen', 'chrome-hidden', 'layout-split');
        el.btnFullscreen.setAttribute('aria-pressed', 'false');
        callApi('toggle_fullscreen');
        clearTimeout(chromeTimer);
      }
      if (AppState.isSquare) {
        AppState.isSquare = false;
        el.body.classList.remove('mode-square');
      }
      AppState.isMini = true;
      el.body.classList.add('mode-mini');
      el.miniBar.hidden = false;
      el.miniBar.classList.add('pywebview-drag-region');
      refreshMini();
      if (opts.backend !== false) callApi('toggle_mini_mode', true);
      if (opts.persist !== false) persistSettings({ view_mode: 'mini' });
    } else {
      if (AppState.isMiniExpanded) setMiniExpanded(false, { backend: true });
      AppState.isMini = false;
      el.body.classList.remove('mode-mini');
      el.miniBar.hidden = true;
      if (opts.backend !== false) callApi('toggle_mini_mode', false);
      if (opts.persist !== false) persistSettings({ view_mode: 'card' });
      if (opts.announce) showToast('Full window', { icon: 'expand' });
    }
    syncWindowUi();
  }

  function refreshMini() {
    updateMiniArtwork(AppState.track.thumbnail);
    if (!AppState.isSynced && AppState.lyrics.length) {
      setMiniUnsynced();
    } else {
      el.miniOriginal.textContent = AppState.hasTrack ? (AppState.track.title || 'Instrumental') : 'Connecting…';
      el.miniRomaji.textContent = AppState.track.artist || '';
      el.miniTranslation.textContent = AppState.track.album || '';
      if (AppState.activeIndex >= 0 && AppState.lyrics[AppState.activeIndex]) updateMiniLine(AppState.activeIndex);
    }
    if (AppState.isMiniExpanded) buildMiniLyrics();
  }

  function setMiniExpanded(expanded, options) {
    var opts = options || {};
    var next = Boolean(expanded);
    if (!AppState.isMini) return;
    AppState.isMiniExpanded = next;
    el.body.classList.toggle('mini-expanded', next);
    el.miniDrawer.hidden = !next;
    el.btnMiniLyrics.setAttribute('aria-pressed', String(next));
    el.btnMiniLyrics.setAttribute('aria-label', next ? 'Hide lyrics' : 'Show lyrics');
    el.btnMiniLyrics.setAttribute('data-tooltip', next ? 'Hide lyrics' : 'Show lyrics');
    el.miniLyricsUse.setAttribute('href', next ? '#icon-chevron-down' : '#icon-chevron-up');
    if (next) {
      buildMiniLyrics();
      if (AppState.activeIndex >= 0) {
        var active = $('mini-line-' + AppState.activeIndex);
        if (active) active.scrollIntoView({ behavior: 'auto', block: 'center' });
      }
    }
    if (opts.backend !== false) callApi('toggle_mini_expand', next);
  }

  function cycleMiniWidth() {
    var current = window.innerWidth;
    var presets = [560, 760, 960];
    var next = presets[0];
    for (var i = 0; i < presets.length; i++) {
      if (current < presets[i] - 30) {
        next = presets[i];
        break;
      }
    }
    callApi('set_mini_width', next).then(function () {
      showToast('Mini width: ' + next + 'px', { icon: 'pip' });
    });
  }

  function initMiniResize() {
    var left = el.miniResizeLeft;
    var right = el.miniResizeRight;
    if (!left || !right) return;

    var isResizing = false;
    var startX = 0;
    var startWidth = 560;
    var currentHandle = null;
    var rafId = null;
    var pendingWidth = 560;

    function onMouseDown(e) {
      if (e.button !== 0) return;
      e.preventDefault();
      e.stopPropagation();
      isResizing = true;
      currentHandle = this;
      startX = e.screenX;
      startWidth = window.innerWidth;
      pendingWidth = startWidth;
      currentHandle.classList.add('is-resizing');
      el.body.classList.add('resizing-mini');
      window.addEventListener('mousemove', onMouseMove, { passive: true });
      window.addEventListener('mouseup', onMouseUp);
    }

    function onMouseMove(e) {
      if (!isResizing) return;
      var dx = e.screenX - startX;
      var targetWidth = currentHandle === right
        ? startWidth + dx
        : startWidth - dx;
      targetWidth = Math.max(420, Math.min(1400, Math.round(targetWidth)));
      if (targetWidth === pendingWidth) return;
      pendingWidth = targetWidth;
      if (!rafId) {
        rafId = requestAnimationFrame(function () {
          rafId = null;
          callApi('set_mini_width', pendingWidth);
        });
      }
    }

    function onMouseUp(e) {
      if (!isResizing) return;
      isResizing = false;
      if (rafId) {
        cancelAnimationFrame(rafId);
        rafId = null;
      }
      if (currentHandle) currentHandle.classList.remove('is-resizing');
      el.body.classList.remove('resizing-mini');
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      callApi('set_mini_width', pendingWidth);
    }

    function onDoubleClick(e) {
      e.preventDefault();
      e.stopPropagation();
      cycleMiniWidth();
    }

    right.addEventListener('mousedown', onMouseDown);
    left.addEventListener('mousedown', onMouseDown);
    right.addEventListener('dblclick', onDoubleClick);
    left.addEventListener('dblclick', onDoubleClick);
  }

