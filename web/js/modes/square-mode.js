  function setSquareMode(square, options) {
    var opts = options || {};
    var next = Boolean(square);
    if (next === AppState.isSquare) {
      if (next && opts.force) refreshSquare();
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
      if (AppState.isMini) {
        if (AppState.isMiniExpanded) setMiniExpanded(false, { backend: true });
        AppState.isMini = false;
        el.body.classList.remove('mode-mini');
        el.miniBar.hidden = true;
      }
      AppState.isSquare = true;
      el.body.classList.add('mode-square');
      if (el.squareHeader) el.squareHeader.hidden = false;
      if (el.squareFooter) el.squareFooter.hidden = false;
      refreshSquare();
      if (opts.backend !== false) callApi('toggle_square_mode', true);
      if (opts.persist !== false) persistSettings({ view_mode: 'square' });
      if (opts.announce) showToast('Square mode', { icon: 'square' });
    } else {
      AppState.isSquare = false;
      el.body.classList.remove('mode-square');
      if (el.squareHeader) el.squareHeader.hidden = true;
      if (el.squareFooter) el.squareFooter.hidden = true;
      if (opts.backend !== false) callApi('toggle_square_mode', false);
      if (opts.persist !== false) persistSettings({ view_mode: 'card' });
      if (opts.announce) showToast('Full window', { icon: 'expand' });
    }
    syncWindowUi();
  }

  function refreshSquare() {
    if (el.squareTitle) {
      if (!AppState.hasTrack) {
        el.squareTitle.textContent = 'Connecting…';
      } else {
        el.squareTitle.textContent = (AppState.track.title || 'Playing') +
          (AppState.track.artist ? ' • ' + AppState.track.artist : '');
      }
    }
    if (el.squareViewModeText) {
      el.squareViewModeText.textContent = LYRIC_VIEW_LABELS[AppState.lyricViewMode] || 'DUAL';
    }
    if (el.btnSquarePin) {
      el.btnSquarePin.setAttribute('aria-pressed', String(AppState.pinned));
      el.btnSquarePin.classList.toggle('active', AppState.pinned);
    }
    if (AppState.activeIndex >= 0 && AppState.lyrics[AppState.activeIndex]) {
      var activeEl = $('line-' + AppState.activeIndex);
      if (activeEl) {
        activeEl.scrollIntoView({ behavior: 'auto', block: 'center' });
      }
    }
  }

  function cycleSquareSize() {
    var current = AppState.squareSize || Math.max(window.innerWidth, window.innerHeight);
    var presets = [320, 420, 520, 640];
    var next = presets[0];
    for (var i = 0; i < presets.length; i++) {
      if (current < presets[i] - 25) {
        next = presets[i];
        break;
      }
    }
    AppState.squareSize = next;
    callApi('set_square_size', next);
    showToast('Square size: ' + next + 'px', { icon: 'square' });
  }

  function initSquareResize() {
    var handle = el.squareResizeHandle;
    if (!handle) return;
    var isResizing = false;
    var startX = 0;
    var startY = 0;
    var startSize = 420;
    var pendingSize = 420;
    var rafId = null;

    function onMouseDown(e) {
      if (e.button !== 0) return;
      e.preventDefault();
      e.stopPropagation();
      isResizing = true;
      startX = e.screenX;
      startY = e.screenY;
      startSize = Math.max(window.innerWidth, window.innerHeight);
      pendingSize = startSize;
      handle.classList.add('is-resizing');
      el.body.classList.add('resizing-square');
      window.addEventListener('mousemove', onMouseMove);
      window.addEventListener('mouseup', onMouseUp);
    }

    function onMouseMove(e) {
      if (!isResizing) return;
      var dx = e.screenX - startX;
      var dy = e.screenY - startY;
      var delta = Math.abs(dx) > Math.abs(dy) ? dx : dy;
      var targetSize = Math.max(280, Math.min(900, Math.round(startSize + delta)));
      if (targetSize === pendingSize) return;
      pendingSize = targetSize;
      AppState.squareSize = pendingSize;
      if (!rafId) {
        rafId = requestAnimationFrame(function () {
          rafId = null;
          callApi('set_square_size', pendingSize);
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
      handle.classList.remove('is-resizing');
      el.body.classList.remove('resizing-square');
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      callApi('set_square_size', pendingSize);
    }

    function onDoubleClick(e) {
      e.preventDefault();
      e.stopPropagation();
      cycleSquareSize();
    }

    handle.addEventListener('mousedown', onMouseDown);
    handle.addEventListener('dblclick', onDoubleClick);
  }

