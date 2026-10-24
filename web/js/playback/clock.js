  // ---------------------------------------------------------------------------
  // Playback clock
  // ---------------------------------------------------------------------------

  function currentPositionMs() {
    var position = AppState.basePositionMs;
    if (AppState.isPlaying && !AppState.lowPower) {
      position += (performance.now() - AppState.baseTimestamp) * AppState.playbackRate;
    }
    if (AppState.duration > 0) position = Math.min(AppState.duration * 1000, position);
    return Math.max(0, position);
  }

  function currentPositionSeconds() { return currentPositionMs() / 1000; }

  function shouldAnimate() {
    return AppState.isPlaying && !document.hidden && !AppState.lowPower;
  }

  function stopFrame() {
    if (AppState.rafId !== null) {
      cancelAnimationFrame(AppState.rafId);
      AppState.rafId = null;
    }
  }

  function frameLoop() {
    AppState.rafId = null;
    if (!shouldAnimate()) return;
    renderPosition(currentPositionSeconds());
    AppState.rafId = requestAnimationFrame(frameLoop);
  }

  function ensureFrame() {
    if (AppState.rafId !== null) return;
    if (!shouldAnimate()) return;
    AppState.rafId = requestAnimationFrame(frameLoop);
  }

  function setPlaying(playing) {
    var next = Boolean(playing);
    if (AppState.isPlaying === next) {
      updatePlayIcons();
      return;
    }
    // Freeze the computed position before changing clock mode.
    var frozen = currentPositionSeconds();
    AppState.basePositionMs = frozen * 1000;
    AppState.baseTimestamp = performance.now();
    AppState.isPlaying = next;
    el.body.classList.toggle('is-playing', next);
    updatePlayIcons();
    if (next) ensureFrame();
    else {
      stopFrame();
      renderPosition(frozen);
    }
  }

  function updatePlayIcons() {
    var name = AppState.isPlaying ? '#icon-pause' : '#icon-play';
    var label = AppState.isPlaying ? 'Pause' : 'Play';
    el.playUse.setAttribute('href', name);
    el.miniPlayUse.setAttribute('href', name);
    if (el.squarePlayUse) el.squarePlayUse.setAttribute('href', name);
    el.btnPlayPause.setAttribute('aria-label', label);
    el.btnPlayPause.setAttribute('data-tooltip', label);
    el.btnMiniPlay.setAttribute('aria-label', label);
    el.btnMiniPlay.setAttribute('data-tooltip', label);
    el.btnMiniPlay.classList.toggle('active', AppState.isPlaying);
    if (el.btnSquarePlay) {
      el.btnSquarePlay.setAttribute('aria-label', label);
      el.btnSquarePlay.setAttribute('data-tooltip', label);
      el.btnSquarePlay.classList.toggle('active', AppState.isPlaying);
    }
    el.body.classList.toggle('is-playing', AppState.isPlaying);
  }

  function seekTo(seconds, isSeek) {
    var value = clamp(Number(seconds) || 0, 0, AppState.duration > 0 ? AppState.duration : 86400);
    AppState.basePositionMs = value * 1000;
    AppState.baseTimestamp = performance.now();
    AppState.userScrollUntil = 0;
    renderPosition(value);
    if (isSeek !== false) callApi('seek', value);
  }

