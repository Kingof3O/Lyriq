  // ---------------------------------------------------------------------------
  // Apply persisted settings
  // ---------------------------------------------------------------------------

  function applyAllSettings() {
    var settings = AppState.settings;
    applyTheme(settings.theme, { persist: false });
    setFontScale(settings.font_scale, { persist: false });
    setLyricsViewMode(settings.lyrics_view_mode, { persist: false });
    setSweep(settings.karaoke_sweep_enabled, { persist: false });
    setRomanization(settings.romanization_enabled, { persist: false });
    setWordLookup(settings.word_lookup_enabled, { persist: false });
    setLowPower(settings.low_power_mode, { persist: false });
    setPinned(settings.always_on_top, { persist: false, backend: false });
    setGhostMode(settings.ghost_mode, { persist: false, backend: false });
    setDiscord(settings.discord_rpc_enabled, { persist: false, backend: false });
    setSplit(settings.split_layout, { persist: false });
    if (langSelectInstance) langSelectInstance.setValue(settings.target_lang, false);
  }

  var backendInitialized = false;

  function initFromBackend() {
    if (backendInitialized) return;
    var api = getApi();
    if (!api) return;
    backendInitialized = true;
    var load = function (remote) {
      if (remote && typeof remote === 'object' && !Array.isArray(remote)) {
        var local = readLocalSettings();
        AppState.settings = mergeSettings(Object.assign({}, local, remote));
        writeLocalSettings(AppState.settings);
        applyAllSettings();
      }
      if (hasApi('set_target_language')) callApi('set_target_language', AppState.settings.target_lang);
      setDiscord(AppState.settings.discord_rpc_enabled, { persist: false, backend: true });
      setPinned(AppState.settings.always_on_top, { persist: false, backend: true });
      setGhostMode(AppState.settings.ghost_mode, { persist: false, backend: true });
      refreshStartupState();
      if (AppState.hasTrack) loadSongOffset(AppState.track.artist, AppState.track.title);
      setTimeout(function () { window.applyPersistedViewMode(); }, 200);
    };
    try {
      var result = api.get_settings();
      if (result && typeof result.then === 'function') result.then(load).catch(function () { load({}); });
      else load(result);
    } catch (err) {
      load({});
    }
  }

