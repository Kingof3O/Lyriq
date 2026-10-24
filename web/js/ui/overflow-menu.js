  // ---------------------------------------------------------------------------
  // Overflow menu
  // ---------------------------------------------------------------------------

  function toggleOverflow(force) {
    var next = typeof force === 'boolean' ? force : el.overflowMenu.hidden;
    el.overflowMenu.hidden = !next;
    el.btnOverflow.setAttribute('aria-expanded', String(next));
    if (next) syncMenuChecks();
  }

  function closeOverflow() {
    el.overflowMenu.hidden = true;
    el.btnOverflow.setAttribute('aria-expanded', 'false');
  }

  function syncMenuChecks() {
    el.menuPin.setAttribute('aria-checked', String(AppState.pinned));
    el.menuGhost.setAttribute('aria-checked', String(AppState.ghost));
    el.menuLowPower.setAttribute('aria-checked', String(AppState.lowPower));
    el.menuDiscord.setAttribute('aria-checked', String(AppState.discord));
    el.btnSplitLayout.setAttribute('aria-checked', String(AppState.isSplit));
    el.btnSplitLayout.hidden = !AppState.isFullscreen;
  }

