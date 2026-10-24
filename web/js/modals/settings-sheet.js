  // ---------------------------------------------------------------------------
  // Settings sheet
  // ---------------------------------------------------------------------------

  var lastSettingsTab = 'appearance';

  function openSettings(tab) {
    if (AppState.isMini) setMiniMode(false, { persist: false, backend: true });
    if (AppState.isSquare) setSquareMode(false, { persist: false, backend: true });
    closeOverflow();
    closeLineContext();
    setSettingsTab(tab || lastSettingsTab);
    el.settingsOverlay.hidden = false;
    refreshCacheStats();
    loadLrcFolder();
    el.settingsSheet.focus();
  }

  function closeSettings() {
    el.settingsOverlay.hidden = true;
  }

  function setSettingsTab(tab) {
    var valid = ['appearance', 'lyrics', 'translation', 'playback', 'shortcuts', 'data', 'about'];
    var next = valid.indexOf(tab) >= 0 ? tab : 'appearance';
    lastSettingsTab = next;
    valid.forEach(function (name) {
      var button = $('tab-' + name);
      var panel = $('panel-' + name);
      var active = name === next;
      if (button) {
        button.classList.toggle('is-active', active);
        button.setAttribute('aria-selected', String(active));
        button.tabIndex = active ? 0 : -1;
      }
      if (panel) panel.hidden = !active;
    });
    if (next === 'data') {
      refreshCacheStats();
      loadLrcFolder();
    }
    if (next === 'playback') refreshStartupState();
  }

