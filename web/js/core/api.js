  // ---------------------------------------------------------------------------
  // Settings persistence
  // ---------------------------------------------------------------------------

  var pendingSettings = {};
  var settingsFlushTimer = null;

  function readLocalSettings() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      var parsed = raw ? JSON.parse(raw) : {};
      return parsed && typeof parsed === 'object' ? parsed : {};
    } catch (err) {
      return {};
    }
  }

  function writeLocalSettings(settings) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(settings)); } catch (err) { /* ignore */ }
  }

  function mergeSettings(values) {
    var merged = {};
    Object.keys(DEFAULT_SETTINGS).forEach(function (key) { merged[key] = DEFAULT_SETTINGS[key]; });
    Object.keys(values || {}).forEach(function (key) { merged[key] = values[key]; });
    merged.theme = ['system', 'dark', 'light', 'oled'].indexOf(merged.theme) >= 0 ? merged.theme : 'system';
    merged.target_lang = LANG_NAMES[merged.target_lang] ? merged.target_lang : 'en';
    merged.view_mode = ['card', 'mini', 'square', 'fullscreen'].indexOf(merged.view_mode) >= 0 ? merged.view_mode : 'card';
    merged.lyrics_view_mode = LYRIC_VIEW_MODES.indexOf(merged.lyrics_view_mode) >= 0 ? merged.lyrics_view_mode : 'both';
    var scale = Number(merged.font_scale);
    merged.font_scale = isFinite(scale) ? clamp(scale, 0.85, 1.3) : 1;
    ['romanization_enabled', 'karaoke_sweep_enabled', 'ghost_mode', 'discord_rpc_enabled',
      'low_power_mode', 'always_on_top', 'word_lookup_enabled', 'split_layout'].forEach(function (key) {
      merged[key] = Boolean(merged[key]);
    });
    return merged;
  }

  function flushSettings() {
    clearTimeout(settingsFlushTimer);
    settingsFlushTimer = null;
    var patch = pendingSettings;
    pendingSettings = {};
    if (!patch || Object.keys(patch).length === 0) return;
    var api = getApi();
    if (api && typeof api.save_settings === 'function') {
      try {
        var result = api.save_settings(patch);
        if (result && typeof result.catch === 'function') result.catch(function () { /* ignore */ });
      } catch (err) { /* ignore */ }
    }
  }

  function persistSettings(patch, options) {
    var opts = options || {};
    Object.assign(AppState.settings, patch);
    writeLocalSettings(AppState.settings);
    Object.assign(pendingSettings, patch);
    clearTimeout(settingsFlushTimer);
    if (opts.debounce) {
      settingsFlushTimer = setTimeout(flushSettings, 250);
    } else {
      flushSettings();
    }
  }

  function loadInitialSettings() {
    AppState.settings = mergeSettings(readLocalSettings());
    AppState.themeChoice = AppState.settings.theme;
    AppState.fontScale = AppState.settings.font_scale;
  }

