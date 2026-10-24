/* ============================================================================
   Spotify Realtime Lyrics - application state, rendering and IPC
   Modular source files live under web/js/ - DO NOT EDIT MANUALLY
   ========================================================================== */
(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // Constants
  // ---------------------------------------------------------------------------

  var STORAGE_KEY = 'lyrics.settings.v3';
  var LANGS = [
    ['en', 'English'], ['es', 'Spanish'], ['fr', 'French'], ['de', 'German'],
    ['it', 'Italian'], ['pt', 'Portuguese'], ['ru', 'Russian'], ['ja', 'Japanese'],
    ['ko', 'Korean'], ['zh', 'Chinese'], ['ar', 'Arabic'], ['hi', 'Hindi'],
    ['tr', 'Turkish'], ['vi', 'Vietnamese'], ['th', 'Thai'], ['id', 'Indonesian'],
    ['nl', 'Dutch'], ['pl', 'Polish'], ['uk', 'Ukrainian'], ['sv', 'Swedish'],
    ['da', 'Danish'], ['fi', 'Finnish'], ['no', 'Norwegian'], ['cs', 'Czech'],
    ['el', 'Greek'], ['he', 'Hebrew'], ['ms', 'Malay'], ['fil', 'Filipino'],
    ['bn', 'Bengali'], ['fa', 'Persian']
  ];
  var LANG_NAMES = {};
  LANGS.forEach(function (entry) { LANG_NAMES[entry[0]] = entry[1]; });

  var DEFAULT_SETTINGS = {
    theme: 'system',
    target_lang: 'en',
    romanization_enabled: true,
    karaoke_sweep_enabled: true,
    view_mode: 'card',
    ghost_mode: false,
    discord_rpc_enabled: true,
    low_power_mode: false,
    font_scale: 1.0,
    always_on_top: false,
    lyrics_view_mode: 'both',
    word_lookup_enabled: true,
    split_layout: false
  };

  var LYRIC_VIEW_MODES = ['both', 'trans-only', 'orig-only'];
  var LYRIC_VIEW_LABELS = { 'both': 'DUAL', 'trans-only': 'TRANSLATION', 'orig-only': 'ORIGINAL' };

  // ---------------------------------------------------------------------------
  // Central state
  // ---------------------------------------------------------------------------

  var AppState = {
    track: { title: '', artist: '', album: '', thumbnail: '', duration: 0 },
    lyrics: [],
    activeIndex: -1,
    isPlaying: false,
    basePositionMs: 0,
    baseTimestamp: 0,
    playbackRate: 1,
    duration: 0,
    isSynced: true,
    provider: '',
    language: 'unknown',
    settings: {},
    offset: 0,
    lyricViewMode: 'both',
    themeChoice: 'system',
    resolvedTheme: 'dark',
    lowPower: false,
    fontScale: 1,
    favorite: false,
    wordLookup: true,
    sweep: true,
    romanization: true,
    isMini: false,
    isMiniExpanded: false,
    isSquare: false,
    squareSize: 420,
    isFullscreen: false,
    isSplit: false,
    pinned: false,
    ghost: false,
    discord: true,
    hasTrack: false,
    preview: null,
    accentRgb: [138, 180, 248],
    lastThumbnail: '',
    skeletonTimer: null,
    translationTimer: null,
    userScrollUntil: 0,
    rafId: null,
    isScrubbing: false
  };

  // ---------------------------------------------------------------------------
  // DOM
  // ---------------------------------------------------------------------------

  function $(id) { return document.getElementById(id); }

  var el = {
    body: document.body,
    root: document.documentElement,
    backdrop: $('albumBackdrop'),
    topbar: $('topbar'),
    trackCard: $('trackCard'),
    npArtWrap: $('npArtWrap'),
    trackArtwork: $('trackArtwork'),
    trackDisc: $('trackDisc'),
    trackTitle: $('trackTitle'),
    trackArtist: $('trackArtist'),
    trackAlbum: $('trackAlbum'),
    subSep: $('subSep'),
    btnHeart: $('btnHeart'),
    heartUse: $('heartUse'),
    flagBadge: $('flagBadge'),
    providerBadge: $('providerBadge'),
    syncBadge: $('syncBadge'),
    ghostBadge: $('ghostBadge'),
    sleepTimerBadge: $('sleepTimerBadge'),
    sleepTimerText: $('sleepTimerText'),
    translationStatus: $('translationStatus'),
    btnMini: $('btnMini'),
    btnSquare: $('btnSquare'),
    btnFullscreen: $('btnFullscreen'),
    btnSettings: $('btnSettings'),
    btnOverflow: $('btnOverflow'),
    btnMin: $('btnMin'),
    btnClose: $('btnClose'),
    btnSplitLayout: $('btnSplitLayout'),
    menuPin: $('menuPin'),
    menuGhost: $('menuGhost'),
    menuLowPower: $('menuLowPower'),
    menuDiscord: $('menuDiscord'),
    overflowMenu: $('overflowMenu'),
    menuSearchLyrics: $('menuSearchLyrics'),
    menuPalette: $('menuPalette'),
    menuExportLrc: $('menuExportLrc'),
    menuExportSrt: $('menuExportSrt'),
    menuExportSheet: $('menuExportSheet'),
    menuOpenLrc: $('menuOpenLrc'),
    menuHistory: $('btnHistoryOpen'),
    menuVocab: $('btnVocabOpen'),
    stageArtwork: $('stageArtwork'),
    stageDisc: $('stageDisc'),
    stageTitle: $('stageTitle'),
    stageArtist: $('stageArtist'),
    stageAlbum: $('stageAlbum'),
    stageLang: $('stageLang'),
    stageProvider: $('stageProvider'),
    previewBanner: $('previewBanner'),
    previewLabel: $('previewLabel'),
    btnBackToLive: $('btnBackToLive'),
    instrumentalPill: $('instrumentalPill'),
    instrumentalText: $('instrumentalText'),
    lyricsViewport: $('lyricsViewport'),
    idleState: $('idleState'),
    skeletonState: $('skeletonState'),
    lyricsList: $('lyricsList'),
    noLyricsState: $('noLyricsState'),
    errorIcon: $('errorIcon'),
    errorTitle: $('errorTitle'),
    errorMessage: $('errorMessage'),
    btnRetry: $('btnRetry'),
    btnSearchLyrics: $('btnSearchLyrics'),
    currentTime: $('currentTime'),
    totalTime: $('totalTime'),
    scrubTrack: $('scrubTrack'),
    scrubFill: $('scrubFill'),
    scrubHandle: $('scrubHandle'),
    playerDock: $('playerDock'),
    btnPlayPause: $('btnPlayPause'),
    playUse: $('playUse'),
    btnPrev: $('btnPrev'),
    btnNext: $('btnNext'),
    btnVolume: $('btnVolume'),
    dockVolume: $('dockVolume'),
    sliderVolume: $('sliderVolume'),
    volumeLabel: $('volumeLabel'),
    btnViewMode: $('btnViewMode'),
    viewModeText: $('viewModeText'),
    dockOffset: $('dockOffset'),
    btnOffsetChip: $('btnOffsetChip'),
    // Mini
    miniBar: $('miniBar'),
    miniResizeLeft: $('miniResizeLeft'),
    miniResizeRight: $('miniResizeRight'),
    miniArtWrap: $('miniArtWrap'),
    miniArtwork: $('miniArtwork'),
    miniDisc: $('miniDisc'),
    miniOriginal: $('miniOriginal'),
    miniRomaji: $('miniRomaji'),
    miniTranslation: $('miniTranslation'),
    miniProgressFill: $('miniProgressFill'),
    btnMiniPlay: $('btnMiniPlay'),
    miniPlayUse: $('miniPlayUse'),
    btnMiniNext: $('btnMiniNext'),
    btnMiniLyrics: $('btnMiniLyrics'),
    miniLyricsUse: $('miniLyricsUse'),
    btnMiniOpen: $('btnMiniOpen'),
    btnMiniPin: $('btnMiniPin'),
    btnMiniClose: $('btnMiniClose'),
    btnMiniSquare: $('btnMiniSquare'),
    miniDrawer: $('miniDrawer'),
    miniLyricsScroll: $('miniLyricsScroll'),
    // Square mode
    squareHeader: $('squareHeader'),
    squareTitle: $('squareTitle'),
    btnSquarePin: $('btnSquarePin'),
    btnSquareExpand: $('btnSquareExpand'),
    btnSquareClose: $('btnSquareClose'),
    btnSquareBgToggle: $('btnSquareBgToggle'),
    btnHistoryAll: $('btnHistoryAll'),
    btnHistoryLiked: $('btnHistoryLiked'),
    squareFooter: $('squareFooter'),
    squareScrubTrack: $('squareScrubTrack'),
    squareScrubFill: $('squareScrubFill'),
    squareTime: $('squareTime'),
    btnSquareViewMode: $('btnSquareViewMode'),
    squareViewModeText: $('squareViewModeText'),
    btnSquarePrev: $('btnSquarePrev'),
    btnSquarePlay: $('btnSquarePlay'),
    squarePlayUse: $('squarePlayUse'),
    btnSquareNext: $('btnSquareNext'),
    btnSquareToMini: $('btnSquareToMini'),
    btnSquareToCard: $('btnSquareToCard'),
    squareResizeHandle: $('squareResizeHandle'),
    // Settings
    settingsOverlay: $('settingsOverlay'),
    settingsSheet: $('settingsSheet'),
    btnSettingsClose: $('btnSettingsClose'),
    themeGroup: $('themeGroup'),
    viewModeGroup: $('viewModeGroup'),
    sliderFontScale: $('sliderFontScale'),
    fontScaleVal: $('fontScaleVal'),
    checkLowPower: $('checkLowPower'),
    checkRomaji: $('checkRomaji'),
    checkSweep: $('checkSweep'),
    checkLearner: $('checkLearner'),
    checkDiscord: $('checkDiscord'),
    checkPin: $('checkPin'),
    checkGhost: $('checkGhost'),
    checkStartup: $('checkStartup'),
    startupHelp: $('startupHelp'),
    langSelect: $('langSelect'),
    sleepSelect: $('sleepSelect'),
    offsetSongLabel: $('offsetSongLabel'),
    nudgeOffsetVal: $('nudgeOffsetVal'),
    btnNudgeMinus: $('btnNudgeMinus'),
    btnNudgePlus: $('btnNudgePlus'),
    btnNudgeReset: $('btnNudgeReset'),
    romajiSettingsLabel: $('romajiSettingsLabel'),
    cacheStats: $('cacheStats'),
    btnRefreshCache: $('btnRefreshCache'),
    btnClearCache: $('btnClearCache'),
    lrcFolderPath: $('lrcFolderPath'),
    btnOpenLrcFolder: $('btnOpenLrcFolder'),
    btnSettingsSearchLyrics: $('btnSettingsSearchLyrics'),
    btnSettingsHistory: $('btnSettingsHistory'),
    btnSettingsVocab: $('btnSettingsVocab'),
    btnExportLrc: $('btnExportLrc'),
    btnExportSrt: $('btnExportSrt'),
    btnExportSheet: $('btnExportSheet'),
    btnCopyLine: $('btnCopyLine'),
    btnCopyAll: $('btnCopyAll'),
    // Modals
    btnLikedOpen: $('btnLikedOpen'),
    btnQueueOpen: $('btnQueueOpen'),
    queueModal: $('queueModal'),
    btnQueueClose: $('btnQueueClose'),
    btnQueueRefresh: $('btnQueueRefresh'),
    queueList: $('queueList'),
    inputDiscordClientId: $('inputDiscordClientId'),
    inputSpotifyToken: $('inputSpotifyToken'),
    btnSaveSpotifyToken: $('btnSaveSpotifyToken'),
    btnOpenSpotifyDev: $('btnOpenSpotifyDev'),
    historyModal: $('historyModal'),
    btnHistoryClose: $('btnHistoryClose'),
    historySearch: $('historySearch'),
    historyList: $('historyList'),
    vocabModal: $('vocabModal'),
    btnVocabClose: $('btnVocabClose'),
    vocabSearch: $('vocabSearch'),
    vocabList: $('vocabList'),
    btnExportVocab: $('btnExportVocab'),
    searchModal: $('searchModal'),
    btnSearchClose: $('btnSearchClose'),
    searchForm: $('searchLyricsForm'),
    searchArtist: $('searchArtist'),
    searchTitleInput: $('searchTitleInput'),
    searchDuration: $('searchDuration'),
    btnSearchSubmit: $('btnSearchSubmit'),
    searchResults: $('searchResults'),
    searchFolderPath: $('searchFolderPath'),
    btnSearchOpenFolder: $('btnSearchOpenFolder'),
    commandPalette: $('commandPalette'),
    paletteInput: $('paletteInput'),
    paletteList: $('paletteList'),
    lineContextMenu: $('lineContextMenu'),
    ctxCopy: $('ctxCopy'),
    ctxEdit: $('ctxEdit'),
    dictCard: $('dictCard'),
    dictWord: $('dictWord'),
    dictRomaji: $('dictRomaji'),
    dictMeaning: $('dictMeaning'),
    dictLang: $('dictLang'),
    btnDictSpeak: $('btnDictSpeak'),
    btnDictSave: $('btnDictSave'),
    btnDictCopy: $('btnDictCopy'),
    btnDictClose: $('btnDictClose'),
    viewModeBadge: $('viewModeBadge'),
    romajiBadge: $('romajiBadge'),
    stageMeta: $('stageMeta'),
    stageActions: $('stageActions'),
    scrollRail: $('scrollRail'),
    scrollRailThumb: $('scrollRailThumb'),
    cornerNote: $('cornerNote'),
    btnDockPin: $('btnDockPin'),
    btnDockMini: $('btnDockMini'),
    studyLens: $('studyLens'),
    btnStudyLensClose: $('btnStudyLensClose'),
    studyWord: $('studyWord'),
    studyPron: $('studyPron'),
    studyChips: $('studyChips'),
    studyLangChip: $('studyLangChip'),
    studyTypeChip: $('studyTypeChip'),
    studyDef: $('studyDef'),
    studyNote: $('studyNote'),
    studyQuote: $('studyQuote'),
    studyQuoteOriginal: $('studyQuoteOriginal'),
    studyQuoteTrans: $('studyQuoteTrans'),
    btnStudyCopy: $('btnStudyCopy'),
    btnStudySave: $('btnStudySave'),
    searchQueryInput: $('searchQueryInput'),
    searchCurrentTitle: $('searchCurrentTitle'),
    searchCurrentSub: $('searchCurrentSub'),
    searchCandidateCount: $('searchCandidateCount'),
    inspectTitle: $('inspectTitle'),
    inspectDesc: $('inspectDesc'),
    metricTitle: $('metricTitle'),
    metricTitleBar: $('metricTitleBar'),
    metricArtist: $('metricArtist'),
    metricArtistBar: $('metricArtistBar'),
    metricDuration: $('metricDuration'),
    metricDurationBar: $('metricDurationBar'),
    metricSynced: $('metricSynced'),
    metricSyncedBar: $('metricSyncedBar'),
    btnInspectUse: $('btnInspectUse'),
    btnInspectPreview: $('btnInspectPreview'),
    appearancePreview: $('appearancePreview'),
    specimenOriginal: $('specimenOriginal'),
    specimenTrans: $('specimenTrans'),
    toastContainer: $('toastContainer')
  };

  // ---------------------------------------------------------------------------
  // Utilities
  // ---------------------------------------------------------------------------

  function clamp(value, min, max) { return Math.min(max, Math.max(min, value)); }

  var RTL_REGEX = /[\u0590-\u08FF\uFB1D-\uFDFF\uFE70-\uFEFC]/;
  function isRtlText(value) {
    if (!value || typeof value !== 'string') return false;
    return RTL_REGEX.test(value);
  }

  function formatTime(seconds) {
    var value = Number(seconds);
    if (!isFinite(value) || value < 0) return '0:00';
    var mins = Math.floor(value / 60);
    var secs = Math.floor(value % 60);
    return mins + ':' + (secs < 10 ? '0' : '') + secs;
  }

  function formatSrtTime(seconds) {
    var value = Math.max(0, Number(seconds) || 0);
    var hrs = Math.floor(value / 3600);
    var mins = Math.floor((value % 3600) / 60);
    var secs = Math.floor(value % 60);
    var ms = Math.floor((value % 1) * 1000);
    return String(hrs).padStart(2, '0') + ':' + String(mins).padStart(2, '0') + ':' +
      String(secs).padStart(2, '0') + ',' + String(ms).padStart(3, '0');
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function getApi() { return (window.pywebview && window.pywebview.api) || null; }

  function hasApi(name) {
    var api = getApi();
    return !!(api && typeof api[name] === 'function');
  }

  function callApi(name) {
    var api = getApi();
    if (!api || typeof api[name] !== 'function') return Promise.resolve(undefined);
    var args = Array.prototype.slice.call(arguments, 1);
    try {
      return Promise.resolve(api[name].apply(api, args));
    } catch (err) {
      return Promise.resolve(undefined);
    }
  }

  function debounce(fn, wait) {
    var timer = null;
    return function () {
      var args = arguments;
      var self = this;
      clearTimeout(timer);
      timer = setTimeout(function () { fn.apply(self, args); }, wait);
    };
  }

  function icon(name, extraClass) {
    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'icon' + (extraClass ? ' ' + extraClass : ''));
    svg.setAttribute('aria-hidden', 'true');
    var use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
    use.setAttribute('href', '#icon-' + name);
    svg.appendChild(use);
    return svg;
  }

  function copyText(text) {
    var value = String(text == null ? '' : text);
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(value).catch(function () {
        return legacyCopy(value);
      });
    }
    return Promise.resolve(legacyCopy(value));
  }

  function legacyCopy(value) {
    try {
      var area = document.createElement('textarea');
      area.value = value;
      area.setAttribute('readonly', '');
      area.style.position = 'fixed';
      area.style.opacity = '0';
      document.body.appendChild(area);
      area.select();
      document.execCommand('copy');
      document.body.removeChild(area);
      return true;
    } catch (err) {
      return false;
    }
  }

  function prefersReducedMotion() {
    return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }

  function isOnline() { return navigator.onLine !== false; }

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

  // ---------------------------------------------------------------------------
  // Theme, accent and backdrop
  // ---------------------------------------------------------------------------

  var systemThemeQuery = window.matchMedia ? window.matchMedia('(prefers-color-scheme: light)') : null;

  function resolveTheme(choice) {
    if (choice === 'system' || choice === 'auto') {
      return systemThemeQuery && systemThemeQuery.matches ? 'light' : 'dark';
    }
    return choice === 'light' || choice === 'oled' ? choice : 'dark';
  }

  function applyTheme(choice, options) {
    var opts = options || {};
    var next = ['system', 'dark', 'light', 'oled'].indexOf(choice) >= 0 ? choice : 'system';
    AppState.themeChoice = next;
    AppState.settings.theme = next;
    AppState.resolvedTheme = resolveTheme(next);
    el.body.dataset.theme = AppState.resolvedTheme;
    el.body.dataset.themeChoice = next;
    Array.prototype.forEach.call(el.themeGroup.querySelectorAll('[data-theme-choice]'), function (button) {
      button.setAttribute('aria-pressed', String(button.dataset.themeChoice === next));
      button.classList.toggle('is-active', button.dataset.themeChoice === next);
    });
    applyAccentFromRgb(AppState.accentRgb[0], AppState.accentRgb[1], AppState.accentRgb[2]);
    if (opts.persist !== false) persistSettings({ theme: next });
  }

  function mixChannel(value, target, amount) {
    return Math.round(value + (target - value) * amount);
  }

  function ensureAccentLuma(rgb) {
    var r = rgb[0], g = rgb[1], b = rgb[2];
    var luma = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
    var light = AppState.resolvedTheme === 'light';
    var min = light ? 0.28 : 0.58;
    var max = light ? 0.46 : 0.82;
    if (luma < min) {
      var amount = (min - luma) / Math.max(0.001, 1 - luma);
      r = mixChannel(r, 255, amount);
      g = mixChannel(g, 255, amount);
      b = mixChannel(b, 255, amount);
    } else if (luma > max) {
      var darken = (luma - max) / Math.max(0.001, luma);
      r = mixChannel(r, 0, darken);
      g = mixChannel(g, 0, darken);
      b = mixChannel(b, 0, darken);
    }
    return [r, g, b];
  }

  function applyAccentFromRgb(r, g, b) {
    var adjusted = ensureAccentLuma([r, g, b]);
    AppState.accentRgb = adjusted;
    var luma = (0.2126 * adjusted[0] + 0.7152 * adjusted[1] + 0.0722 * adjusted[2]) / 255;
    var contrast = luma > 0.58 ? '#0a0d12' : '#ffffff';
    el.root.style.setProperty('--accent-color', 'rgb(' + adjusted.join(', ') + ')');
    el.root.style.setProperty('--accent-text', 'rgb(' + adjusted.join(', ') + ')');
    el.root.style.setProperty('--accent-contrast', contrast);
    el.root.style.setProperty('--accent-soft', 'rgba(' + adjusted.join(', ') + ', 0.13)');
    el.root.style.setProperty('--accent-glow', 'rgba(' + adjusted.join(', ') + ', 0.32)');
  }

  function resetAccent() {
    applyAccentFromRgb(138, 180, 248);
  }

  function extractAccent(image) {
    try {
      var canvas = document.createElement('canvas');
      canvas.width = 16;
      canvas.height = 16;
      var ctx = canvas.getContext('2d', { willReadFrequently: true });
      if (!ctx) return;
      ctx.drawImage(image, 0, 0, 16, 16);
      var data = ctx.getImageData(0, 0, 16, 16).data;
      var best = null;
      var bestScore = -1;
      for (var i = 0; i < data.length; i += 4) {
        var r = data[i], g = data[i + 1], b = data[i + 2], a = data[i + 3];
        if (a < 180) continue;
        var max = Math.max(r, g, b), min = Math.min(r, g, b);
        var light = (max + min) / 510;
        if (light < 0.12 || light > 0.9) continue;
        var sat = max === min ? 0 : (max - min) / (max <= 127 ? max + min : 510 - max - min);
        if (sat < 0.16) continue;
        var score = sat * (1 - Math.abs(light - 0.56)) + (max - min) / 512;
        if (score > bestScore) {
          bestScore = score;
          best = [r, g, b];
        }
      }
      if (best) applyAccentFromRgb(best[0], best[1], best[2]);
      else resetAccent();
    } catch (err) {
      resetAccent();
    }
  }

  function updateAlbumBackdrop(image) {
    try {
      var canvas = document.createElement('canvas');
      canvas.width = 32;
      canvas.height = 32;
      var ctx = canvas.getContext('2d');
      if (!ctx) return;
      ctx.drawImage(image, 0, 0, 32, 32);
      var dataUrl = canvas.toDataURL('image/jpeg', 0.55);
      el.backdrop.style.backgroundImage = 'url("' + dataUrl + '")';
    } catch (err) {
      // Cross-origin art cannot be sampled; keep the previous still backdrop.
    }
  }

  function setTrackImage(thumbnail) {
    var hasImage = !!thumbnail;
    el.trackArtwork.hidden = !hasImage;
    el.trackDisc.hidden = hasImage;
    el.stageArtwork.hidden = !hasImage;
    el.stageDisc.hidden = hasImage;
    el.miniArtwork.hidden = !hasImage;
    el.miniDisc.hidden = hasImage;

    if (!hasImage) {
      el.trackArtwork.removeAttribute('src');
      el.stageArtwork.removeAttribute('src');
      el.miniArtwork.removeAttribute('src');
      el.backdrop.style.backgroundImage = 'none';
      resetAccent();
      AppState.lastThumbnail = '';
      return;
    }

    if (thumbnail === AppState.lastThumbnail) return;
    AppState.lastThumbnail = thumbnail;
    el.trackArtwork.src = thumbnail;
    el.stageArtwork.src = thumbnail;
    el.miniArtwork.src = thumbnail;

    var loader = new Image();
    loader.onload = function () {
      extractAccent(loader);
      updateAlbumBackdrop(loader);
    };
    loader.onerror = function () { resetAccent(); };
    loader.src = thumbnail;
  }

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

  // ---------------------------------------------------------------------------
  // Position rendering / lyrics synchronisation
  // ---------------------------------------------------------------------------

  function renderPosition(seconds) {
    var value = Number(seconds);
    if (!isFinite(value)) return;
    var display = clamp(value, 0, AppState.duration > 0 ? AppState.duration : 86400);
    el.currentTime.textContent = formatTime(display);
    var progress = AppState.duration > 0 ? clamp(display / AppState.duration, 0, 1) : 0;
    el.scrubFill.style.width = (progress * 100) + '%';
    el.scrubHandle.style.left = (progress * 100) + '%';
    el.miniProgressFill.style.width = (progress * 100) + '%';
    if (el.squareScrubFill) el.squareScrubFill.style.width = (progress * 100) + '%';
    if (el.squareTime) el.squareTime.textContent = formatTime(display);
    el.scrubTrack.setAttribute('aria-valuemax', String(Math.round(AppState.duration || 0)));
    el.scrubTrack.setAttribute('aria-valuenow', String(Math.round(display)));
    el.scrubTrack.setAttribute('aria-valuetext', formatTime(display) + ' of ' + formatTime(AppState.duration));

    if (!AppState.lyrics.length || !AppState.isSynced) {
      if (!AppState.isSynced) hideInstrumental();
      return;
    }

    var adjusted = display + AppState.offset;
    var newIndex = findLineIndex(adjusted + 0.12);
    if (newIndex !== AppState.activeIndex) setActiveIndex(newIndex, true);
    else if (newIndex >= 0) updateSweep(newIndex, adjusted);
    updateInstrumental(newIndex, adjusted);
  }

  function findLineIndex(seconds) {
    var low = 0, high = AppState.lyrics.length - 1, result = -1;
    while (low <= high) {
      var mid = (low + high) >> 1;
      var time = AppState.lyrics[mid].time;
      if (time >= 0 && time <= seconds) {
        result = mid;
        low = mid + 1;
      } else {
        high = mid - 1;
      }
    }
    return result;
  }

  function setActiveIndex(index, allowScroll) {
    var previous = AppState.activeIndex;
    if (previous === index) return;

    if (previous >= 0) {
      var prevEl = $('line-' + previous);
      if (prevEl) {
        prevEl.classList.remove('active');
        prevEl.style.removeProperty('--line-progress');
        clearSublines(prevEl);
      }
      var prevMini = $('mini-line-' + previous);
      if (prevMini) prevMini.classList.remove('active');
    }

    AppState.activeIndex = index;

    if (index >= 0) {
      var activeEl = $('line-' + index);
      if (activeEl) {
        activeEl.classList.add('active');
        setupActiveSublines(activeEl, index);
        if (allowScroll !== false && Date.now() > AppState.userScrollUntil && !AppState.isMini) {
          var cRect = el.lyricsViewport.getBoundingClientRect();
          var lRect = activeEl.getBoundingClientRect();
          var offset = lRect.top - cRect.top + el.lyricsViewport.scrollTop;
          var targetScroll = Math.max(0, offset - (cRect.height * 0.44));
          if (previous < 0 || prefersReducedMotion() || AppState.lowPower) {
            el.lyricsViewport.style.scrollBehavior = 'auto';
            el.lyricsViewport.scrollTop = targetScroll;
            el.lyricsViewport.style.scrollBehavior = '';
          } else {
            el.lyricsViewport.scrollTo({
              top: targetScroll,
              behavior: 'smooth'
            });
          }
          if (window.scrollY !== 0) window.scrollTo(0, 0);
          if (document.documentElement.scrollTop !== 0) document.documentElement.scrollTop = 0;
          if (document.body.scrollTop !== 0) document.body.scrollTop = 0;
        }
        updateSweep(index, currentPositionSeconds() + AppState.offset);
      }
      var activeMini = $('mini-line-' + index);
      if (activeMini) {
        activeMini.classList.add('active');
        if (AppState.isMiniExpanded) {
          activeMini.scrollIntoView({ behavior: 'auto', block: 'center' });
        }
      }
      updateMiniLine(index);
    }

    markNeighborhood(index);
  }

  function markNeighborhood(index) {
    var all = el.lyricsList.querySelectorAll('.lyric-line.near');
    Array.prototype.forEach.call(all, function (node) { node.classList.remove('near'); });
    if (index < 0) return;
    for (var i = Math.max(0, index - 2); i <= Math.min(AppState.lyrics.length - 1, index + 2); i++) {
      var node = $('line-' + i);
      if (node) node.classList.add('near');
    }
  }

  function clearSublines(lineEl) {
    if (!lineEl) return;
    var targets = lineEl.querySelectorAll('.has-sublines');
    Array.prototype.forEach.call(targets, function (target) {
      target.classList.remove('has-sublines');
      if (target._originalText !== undefined) {
        target.textContent = target._originalText;
        delete target._originalText;
      }
      delete target._sublines;
    });
  }

  function getActiveLyricTarget(activeEl, line) {
    if (!activeEl || !line) return null;
    if (AppState.lyricViewMode === 'trans-only') {
      if (line.translation && line.translation.trim()) {
        return { el: activeEl.querySelector('.line-translation'), text: line.translation };
      }
      return { el: activeEl.querySelector('.line-original'), text: line.original };
    }
    return { el: activeEl.querySelector('.line-original'), text: line.original };
  }

  function measureVisualLines(targetEl, words) {
    if (!words || words.length <= 1) return words ? [words.join(' ')] : [];
    var fragment = document.createDocumentFragment();
    var spans = [];
    for (var w = 0; w < words.length; w++) {
      var s = document.createElement('span');
      s.textContent = (w > 0 ? ' ' : '') + words[w];
      fragment.appendChild(s);
      spans.push(s);
    }
    targetEl.replaceChildren(fragment);

    var firstRect = spans[0].getBoundingClientRect();
    var lastRect = spans[spans.length - 1].getBoundingClientRect();
    if (Math.abs(lastRect.top - firstRect.top) < 8) {
      return [words.join(' ')];
    }

    var lines = [];
    var currentGroup = [];
    var currentTop = firstRect.top;

    for (var i = 0; i < spans.length; i++) {
      var r = spans[i].getBoundingClientRect();
      if (Math.abs(r.top - currentTop) > 8) {
        if (currentGroup.length) lines.push(currentGroup.join('').trim());
        currentGroup = [spans[i].textContent.trim()];
        currentTop = r.top;
      } else {
        currentGroup.push(spans[i].textContent);
      }
    }
    if (currentGroup.length) {
      lines.push(currentGroup.join('').trim());
    }
    return lines;
  }

  function setupActiveSublines(activeEl, index) {
    if (!activeEl) return;
    clearSublines(activeEl);
    if (!AppState.sweep) return;
    if (editingState && editingState.index === index) return;

    var line = AppState.lyrics[index];
    var target = getActiveLyricTarget(activeEl, line);
    if (!target || !target.el) return;

    var targetEl = target.el;
    var rawText = String(target.text || targetEl.textContent || '').trim();
    if (!rawText) return;
    targetEl._originalText = rawText;

    var isRtl = isRtlText(rawText);
    var explicitLines = rawText.split(/\r?\n/).map(function (s) { return s.trim(); }).filter(Boolean);
    var visualLines = [];

    if (explicitLines.length > 1) {
      for (var e = 0; e < explicitLines.length; e++) {
        var subWords = explicitLines[e].split(/\s+/).filter(Boolean);
        if (subWords.length > 1) {
          var wrapped = measureVisualLines(targetEl, subWords);
          visualLines.push.apply(visualLines, wrapped);
        } else if (subWords.length === 1) {
          visualLines.push(subWords[0]);
        }
      }
    } else {
      var words = rawText.split(/\s+/).filter(Boolean);
      if (words.length > 1) {
        visualLines = measureVisualLines(targetEl, words);
      }
    }

    if (visualLines.length > 1) {
      var totalChars = 0;
      var lengths = visualLines.map(function (str) {
        var len = Math.max(1, str.length);
        totalChars += len;
        return len;
      });

      var sublines = [];
      var accumulated = 0;
      var fragment = document.createDocumentFragment();

      for (var i = 0; i < visualLines.length; i++) {
        var span = document.createElement('span');
        span.className = 'lyric-subline';
        if (isRtl) {
          span.classList.add('is-rtl');
          span.dir = 'rtl';
        }
        span.textContent = visualLines[i];
        fragment.appendChild(span);

        var startNorm = accumulated / totalChars;
        accumulated += lengths[i];
        var endNorm = accumulated / totalChars;

        sublines.push({
          el: span,
          start: startNorm,
          end: endNorm
        });
      }

      targetEl.replaceChildren(fragment);
      targetEl.classList.add('has-sublines');
      targetEl._sublines = sublines;
    } else {
      targetEl.textContent = rawText;
    }
  }

  function updateSweep(index, adjustedSeconds) {
    if (!AppState.sweep || !AppState.isSynced || index < 0) return;
    var line = AppState.lyrics[index];
    if (!line || line.time < 0) return;
    var nextTime = index + 1 < AppState.lyrics.length ? AppState.lyrics[index + 1].time : line.time + 4;
    if (!(nextTime > line.time)) nextTime = line.time + 4;
    var duration = Math.max(0.6, nextTime - line.time);
    var pNorm = clamp((adjustedSeconds - line.time) / duration, 0, 1);
    var node = $('line-' + index);
    if (!node) return;

    var targetWithSublines = node.querySelector('.has-sublines');
    if (targetWithSublines && targetWithSublines._sublines && targetWithSublines._sublines.length > 1) {
      node.style.removeProperty('--line-progress');
      var sublines = targetWithSublines._sublines;
      for (var i = 0; i < sublines.length; i++) {
        var sub = sublines[i];
        var subProgress = 0;
        if (pNorm <= sub.start) {
          subProgress = 0;
        } else if (pNorm >= sub.end) {
          subProgress = 100;
        } else {
          subProgress = ((pNorm - sub.start) / (sub.end - sub.start)) * 100;
        }
        sub.el.style.setProperty('--line-progress', subProgress.toFixed(2) + '%');
      }
    } else {
      node.style.setProperty('--line-progress', (pNorm * 100).toFixed(2) + '%');
    }
  }

  function hideInstrumental() {
    if (el.instrumentalPill) el.instrumentalPill.hidden = true;
  }

  function updateInstrumental(index, adjustedSeconds) {
    if (!AppState.isSynced || index < 0 || index + 1 >= AppState.lyrics.length) {
      hideInstrumental();
      return;
    }
    var current = AppState.lyrics[index];
    var next = AppState.lyrics[index + 1];
    if (!current || !next || current.time < 0 || next.time < 0) {
      hideInstrumental();
      return;
    }
    var gap = next.time - adjustedSeconds;
    var sinceLine = adjustedSeconds - current.time;
    if (gap > 6 && sinceLine > 2.5) {
      el.instrumentalPill.hidden = false;
      el.instrumentalText.textContent = 'Instrumental · ' + Math.ceil(gap) + 's';
    } else {
      hideInstrumental();
    }
  }

  function clearSynchronizedState() {
    if (AppState.activeIndex >= 0) {
      var previous = AppState.activeIndex;
      var node = $('line-' + previous);
      if (node) {
        node.classList.remove('active');
        node.style.removeProperty('--line-progress');
        clearSublines(node);
      }
      var miniNode = $('mini-line-' + previous);
      if (miniNode) miniNode.classList.remove('active');
      AppState.activeIndex = -1;
    }
    Array.prototype.forEach.call(el.lyricsList.querySelectorAll('.near'), function (node) {
      node.classList.remove('near');
    });
    hideInstrumental();
  }

  // ---------------------------------------------------------------------------
  // Toasts
  // ---------------------------------------------------------------------------

  function showToast(message, options) {
    var opts = options || {};
    var toast = document.createElement('div');
    toast.className = 'toast' + (opts.tone === 'danger' ? ' tone-danger' : '');
    toast.setAttribute('role', 'status');

    var iconWrap = document.createElement('span');
    iconWrap.className = 'toast-icon';
    iconWrap.appendChild(icon(opts.icon || (opts.tone === 'danger' ? 'alert' : 'check')));
    toast.appendChild(iconWrap);

    var copy = document.createElement('span');
    copy.className = 'toast-message';
    copy.textContent = String(message || '');
    toast.appendChild(copy);

    if (opts.actionLabel && typeof opts.onAction === 'function') {
      var action = document.createElement('button');
      action.type = 'button';
      action.className = 'toast-action';
      action.textContent = opts.actionLabel;
      action.addEventListener('click', function () {
        removeToast(toast);
        opts.onAction();
      });
      toast.appendChild(action);
    }

    var close = document.createElement('button');
    close.type = 'button';
    close.className = 'toast-close';
    close.setAttribute('aria-label', 'Dismiss notification');
    close.setAttribute('data-tooltip', 'Dismiss');
    close.appendChild(icon('close'));
    close.addEventListener('click', function () { removeToast(toast); });
    toast.appendChild(close);

    el.toastContainer.appendChild(toast);
    while (el.toastContainer.children.length > 3) {
      el.toastContainer.removeChild(el.toastContainer.firstElementChild);
    }

    var duration = opts.duration || (opts.actionLabel ? 6500 : 3000);
    var timer = setTimeout(function () { removeToast(toast); }, duration);
    toast.__timer = timer;
  }

  function removeToast(toast) {
    if (!toast || !toast.parentNode) return;
    clearTimeout(toast.__timer);
    toast.classList.add('is-leaving');
    setTimeout(function () {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, prefersReducedMotion() ? 0 : 180);
  }

  // ---------------------------------------------------------------------------
  // Lyrics rendering
  // ---------------------------------------------------------------------------

  function normalizeLine(line) {
    var time = Number(line && (line.time !== undefined ? line.time : line.timestamp));
    return {
      time: isFinite(time) ? time : -1,
      original: String((line && (line.original !== undefined ? line.original : line.text)) || ''),
      translation: String((line && line.translation) || ''),
      romaji: String((line && line.romaji) || '')
    };
  }

  function lineText(line) {
    if (!line) return '';
    return [line.original, line.translation].filter(Boolean).join('\n').trim();
  }

  function setLanguage(language) {
    var normalized = String(language || '').toLowerCase();
    AppState.language = normalized || 'unknown';
    var known = normalized && normalized !== 'unknown';
    var base = normalized.split('-')[0];
    var code = base.toUpperCase();
    if (base === 'fil') code = 'FIL';
    el.flagBadge.hidden = !known;
    el.flagBadge.textContent = code;
    el.flagBadge.title = known ? (LANG_NAMES[normalized] || normalized) : '';
    el.stageLang.hidden = !known;
    el.stageLang.textContent = code;
    updateRomanizationLabel(normalized);
  }

  function romanizationLabel(language) {
    var normalized = String(language || '').toLowerCase();
    if (normalized.indexOf('zh') === 0) return 'Pinyin';
    if (normalized.indexOf('ja') === 0) return 'Romaji';
    if (normalized.indexOf('ko') === 0) return 'Romaja';
    return 'Romanization';
  }

  function updateRomanizationLabel(language) {
    if (el.romajiSettingsLabel) {
      el.romajiSettingsLabel.textContent = 'Phonetics (' + romanizationLabel(language) + ')';
    }
  }

  function setProvider(provider, synced) {
    AppState.provider = String(provider || '').toUpperCase();
    AppState.isSynced = synced !== false;
    var showProvider = !!AppState.provider && AppState.provider !== 'UNSYNCED';
    if (el.providerBadge) {
      el.providerBadge.hidden = !showProvider;
      el.providerBadge.textContent = AppState.provider;
      el.providerBadge.title = AppState.provider ? 'Lyrics provider: ' + AppState.provider : '';
    }
    if (el.stageProvider) {
      el.stageProvider.hidden = !showProvider;
      el.stageProvider.textContent = AppState.provider;
    }
    if (el.syncBadge) el.syncBadge.hidden = AppState.isSynced;
    el.body.classList.toggle('lyrics-static', !AppState.isSynced);
    el.body.dataset.lyricsSynced = AppState.isSynced ? 'true' : 'false';
  }

  function showTranslationStatus(show) {
    clearTimeout(AppState.translationTimer);
    AppState.translationTimer = null;
    el.translationStatus.hidden = !show;
    if (show) {
      AppState.translationTimer = setTimeout(function () {
        el.translationStatus.hidden = true;
      }, 20000);
    }
  }

  function resetLyricsScroll() {
    AppState.userScrollUntil = 0;
    el.lyricsViewport.style.scrollBehavior = 'auto';
    el.lyricsViewport.scrollTop = 0;
    el.lyricsViewport.style.scrollBehavior = '';
  }

  function showSkeleton() {
    clearTimeout(AppState.skeletonTimer);
    setProvider('', true);
    setLanguage('unknown');
    showTranslationStatus(false);
    resetLyricsScroll();
    el.idleState.hidden = true;
    el.lyricsList.hidden = true;
    el.noLyricsState.hidden = true;
    el.skeletonState.hidden = false;
    hideInstrumental();
    AppState.skeletonTimer = setTimeout(function () {
      if (el.skeletonState.hidden) return;
      el.skeletonState.hidden = true;
      showError(
        isOnline() ? 'Still looking for lyrics' : 'You are offline',
        isOnline() ? 'The lyrics service did not answer in time. Retry or search manually.' : 'Lyrics need a network connection. Reconnect and retry.',
        !isOnline()
      );
    }, 20000);
  }

  function hideSkeleton() {
    clearTimeout(AppState.skeletonTimer);
    AppState.skeletonTimer = null;
    el.skeletonState.hidden = true;
  }

  function showError(title, message, offline) {
    hideSkeleton();
    showTranslationStatus(false);
    resetLyricsScroll();
    el.idleState.hidden = true;
    el.lyricsList.hidden = true;
    el.errorTitle.textContent = title || 'No lyrics found';
    el.errorMessage.textContent = message || 'This track has no lyrics in the library yet.';
    el.errorIcon.replaceChildren(icon(offline ? 'cloud-off' : 'search'));
    el.noLyricsState.hidden = false;
    hideInstrumental();
    clearSynchronizedState();
    AppState.lyrics = [];
    el.miniLyricsScroll.replaceChildren();
    el.miniOriginal.textContent = 'No lyrics';
    el.miniRomaji.textContent = '';
    el.miniTranslation.textContent = '';
  }

  function showIdle() {
    hideSkeleton();
    showTranslationStatus(false);
    resetLyricsScroll();
    el.idleState.hidden = false;
    el.lyricsList.hidden = true;
    el.noLyricsState.hidden = true;
    el.skeletonState.hidden = true;
    el.miniLyricsScroll.replaceChildren();
    setProvider('', true);
    setLanguage('unknown');
    hideInstrumental();
    if (AppState.hasTrack) setMiniFromLine(null);
  }

  function renderLyricsList() {
    hideSkeleton();
    el.idleState.hidden = true;
    el.noLyricsState.hidden = true;
    var fragment = document.createDocumentFragment();
    var isTransOnly = AppState.lyricViewMode === 'trans-only';
    AppState.lyrics.forEach(function (line, index) {
      var lineEl = document.createElement('div');
      lineEl.className = 'lyric-line';
      if (line.time < 0) lineEl.classList.add('untimed');
      if (!line.translation || !line.translation.trim()) lineEl.classList.add('no-trans');
      lineEl.id = 'line-' + index;
      lineEl.dataset.index = String(index);
      lineEl.dataset.time = String(line.time);
      lineEl.setAttribute('role', 'listitem');

      var origRtl = isRtlText(line.original);
      var transRtl = isRtlText(line.translation);
      var lineRtl = isTransOnly ? (transRtl || (!line.translation && origRtl)) : origRtl;
      if (lineRtl) lineEl.classList.add('is-rtl');

      var original = document.createElement('div');
      original.className = 'line-original';
      original.id = 'orig-' + index;
      original.textContent = line.original;
      if (origRtl) {
        original.classList.add('is-rtl');
        original.dir = 'rtl';
      }

      var romaji = document.createElement('div');
      romaji.className = 'line-romaji';
      romaji.id = 'romaji-' + index;
      romaji.textContent = line.romaji;

      var translation = document.createElement('div');
      translation.className = 'line-translation';
      translation.id = 'trans-' + index;
      translation.textContent = line.translation;
      if (transRtl) {
        translation.classList.add('is-rtl');
        translation.dir = 'rtl';
      }

      lineEl.appendChild(original);
      lineEl.appendChild(romaji);
      lineEl.appendChild(translation);
      fragment.appendChild(lineEl);
    });
    el.lyricsList.replaceChildren(fragment);
    el.lyricsList.hidden = false;
  }

  function updateMiniLine(index) {
    var line = index >= 0 ? AppState.lyrics[index] : null;
    setMiniFromLine(line);
  }

  function setMiniFromLine(line) {
    if (!line) {
      var fallback = AppState.lyrics.length ? 'Instrumental' : (AppState.hasTrack ? 'Loading lyrics…' : 'Connecting…');
      el.miniOriginal.textContent = fallback;
      el.miniOriginal.title = fallback;
      el.miniOriginal.classList.remove('is-rtl');
      el.miniOriginal.dir = 'ltr';
      el.miniRomaji.textContent = '';
      el.miniRomaji.title = '';
      el.miniTranslation.textContent = '';
      el.miniTranslation.title = '';
      el.miniTranslation.classList.remove('is-rtl');
      el.miniTranslation.dir = 'ltr';
      el.miniBar.setAttribute('aria-label', 'Mini player');
      return;
    }
    if (AppState.lyricViewMode === 'trans-only') {
      var text = (line.translation && line.translation.trim()) || line.original || '—';
      el.miniOriginal.textContent = text;
      el.miniOriginal.title = text;
      var textRtl = isRtlText(text);
      el.miniOriginal.classList.toggle('is-rtl', textRtl);
      el.miniOriginal.dir = textRtl ? 'rtl' : 'ltr';
      el.miniRomaji.textContent = '';
      el.miniRomaji.title = '';
      el.miniTranslation.textContent = '';
      el.miniTranslation.title = '';
      el.miniTranslation.classList.remove('is-rtl');
      el.miniTranslation.dir = 'ltr';
      el.miniBar.setAttribute('aria-label', text);
      return;
    }
    if (AppState.lyricViewMode === 'orig-only') {
      el.miniOriginal.textContent = line.original || '—';
      el.miniOriginal.title = line.original || '';
      var origRtl = isRtlText(line.original);
      el.miniOriginal.classList.toggle('is-rtl', origRtl);
      el.miniOriginal.dir = origRtl ? 'rtl' : 'ltr';
      el.miniRomaji.textContent = line.romaji || '';
      el.miniRomaji.title = line.romaji || '';
      el.miniTranslation.textContent = '';
      el.miniTranslation.title = '';
      el.miniTranslation.classList.remove('is-rtl');
      el.miniTranslation.dir = 'ltr';
      el.miniBar.setAttribute('aria-label', line.original || '');
      return;
    }
    el.miniOriginal.textContent = line.original || '—';
    el.miniOriginal.title = line.original || '';
    var origRtl2 = isRtlText(line.original);
    el.miniOriginal.classList.toggle('is-rtl', origRtl2);
    el.miniOriginal.dir = origRtl2 ? 'rtl' : 'ltr';
    el.miniRomaji.textContent = line.romaji || '';
    el.miniRomaji.title = line.romaji || '';
    el.miniTranslation.textContent = line.translation || '';
    el.miniTranslation.title = line.translation || '';
    var transRtl = isRtlText(line.translation);
    el.miniTranslation.classList.toggle('is-rtl', transRtl);
    el.miniTranslation.dir = transRtl ? 'rtl' : 'ltr';
    el.miniBar.setAttribute('aria-label', (line.original || '') + ' — ' + (line.translation || ''));
  }

  function setMiniUnsynced() {
    el.miniOriginal.textContent = 'Unsynced lyrics';
    el.miniRomaji.textContent = '';
    el.miniTranslation.textContent = 'Static view';
    el.miniBar.setAttribute('aria-label', 'Unsynced lyrics, static view');
  }

  function buildMiniLyrics() {
    if (!AppState.isMini || !AppState.isMiniExpanded) return;
    var fragment = document.createDocumentFragment();
    var isTransOnly = AppState.lyricViewMode === 'trans-only';
    AppState.lyrics.forEach(function (line, index) {
      var item = document.createElement('div');
      item.className = 'mini-line-item';
      if (!line.translation || !line.translation.trim()) item.classList.add('no-trans');
      item.id = 'mini-line-' + index;
      item.dataset.index = String(index);
      if (index === AppState.activeIndex) item.classList.add('active');

      var origRtl = isRtlText(line.original);
      var transRtl = isRtlText(line.translation);
      var itemRtl = isTransOnly ? (transRtl || (!line.translation && origRtl)) : origRtl;
      if (itemRtl) item.classList.add('is-rtl');

      var original = document.createElement('div');
      original.className = 'mini-orig';
      original.textContent = line.original;
      if (origRtl) {
        original.classList.add('is-rtl');
        original.dir = 'rtl';
      }

      var translation = document.createElement('div');
      translation.className = 'mini-trans';
      translation.id = 'mini-trans-' + index;
      translation.textContent = line.translation;
      if (transRtl) {
        translation.classList.add('is-rtl');
        translation.dir = 'rtl';
      }

      item.appendChild(original);
      item.appendChild(translation);
      item.addEventListener('click', function () {
        if (line.time >= 0) seekTo(Math.max(0, line.time - AppState.offset), true);
      });
      fragment.appendChild(item);
    });
    el.miniLyricsScroll.replaceChildren(fragment);
    if (AppState.activeIndex >= 0) {
      var active = $('mini-line-' + AppState.activeIndex);
      if (active) active.scrollIntoView({ behavior: 'auto', block: 'center' });
    }
  }

  function updateMiniArtwork(thumbnail) {
    el.miniArtwork.hidden = !thumbnail;
    el.miniDisc.hidden = !!thumbnail;
    if (thumbnail) el.miniArtwork.src = thumbnail;
    else el.miniArtwork.removeAttribute('src');
  }

  // ---------------------------------------------------------------------------
  // Backend -> frontend events
  // ---------------------------------------------------------------------------

  var offsetRequestToken = 0;

  window.updateTrack = function (data) {
    if (!data || !data.title) {
      AppState.hasTrack = false;
      AppState.track = { title: '', artist: '', album: '', thumbnail: '', duration: 0 };
      AppState.lyrics = [];
      AppState.activeIndex = -1;
      AppState.duration = 0;
      AppState.basePositionMs = 0;
      AppState.isPlaying = false;
      AppState.offset = 0;
      AppState.preview = null;
      if (editingState) finishLineEdit(false);
      closeLineContext();
      setPlaying(false);
      el.trackTitle.textContent = 'Connecting to Spotify';
      el.trackArtist.textContent = 'Play a song to begin';
      el.trackAlbum.textContent = '';
      el.trackAlbum.hidden = true;
      el.subSep.hidden = true;
      el.stageTitle.textContent = 'No track';
      el.stageArtist.textContent = 'Open Spotify and play a song';
      el.stageAlbum.textContent = '';
      el.stageLang.hidden = true;
      el.stageProvider.hidden = true;
      el.totalTime.textContent = '0:00';
      el.currentTime.textContent = '0:00';
      el.scrubFill.style.width = '0%';
      el.miniProgressFill.style.width = '0%';
      if (el.squareScrubFill) el.squareScrubFill.style.width = '0%';
      if (el.squareTime) el.squareTime.textContent = '0:00';
      if (el.squareTitle) el.squareTitle.textContent = 'Connecting…';
      setTrackImage('');
      setProvider('', true);
      setLanguage('unknown');
      el.previewBanner.hidden = true;
      AppState.favorite = false;
      updateFavoriteUi(false);
      el.miniOriginal.textContent = 'Connecting…';
      el.miniRomaji.textContent = '';
      el.miniTranslation.textContent = '';
      el.lyricsList.replaceChildren();
      el.miniLyricsScroll.replaceChildren();
      hideSkeleton();
      showIdle();
      updateOffsetDisplay();
      return;
    }

    var changed = AppState.track.title !== data.title || AppState.track.artist !== (data.artist || '');
    AppState.hasTrack = true;
    AppState.track = {
      title: String(data.title || ''),
      artist: String(data.artist || ''),
      album: String(data.album || ''),
      thumbnail: String(data.thumbnail || ''),
      duration: Number(data.duration) || 0
    };
    AppState.duration = Number(data.duration) || 0;
    AppState.preview = null;
    el.previewBanner.hidden = true;

    el.trackTitle.textContent = AppState.track.title;
    el.trackArtist.textContent = AppState.track.artist || 'Unknown artist';
    el.trackAlbum.textContent = AppState.track.album;
    el.trackAlbum.hidden = !AppState.track.album;
    el.subSep.hidden = !AppState.track.album;
    el.stageTitle.textContent = AppState.track.title;
    el.stageArtist.textContent = AppState.track.artist || 'Unknown artist';
    el.stageAlbum.textContent = AppState.track.album;
    el.totalTime.textContent = formatTime(AppState.duration);
    if (el.squareTitle) {
      el.squareTitle.textContent = AppState.track.title + (AppState.track.artist ? ' • ' + AppState.track.artist : '');
    }

    var positionMs = data.position_ms !== undefined && data.position_ms !== null
      ? Number(data.position_ms)
      : (Number(data.position) || 0) * 1000;
    if (isFinite(positionMs) && positionMs >= 0) AppState.basePositionMs = positionMs;
    AppState.baseTimestamp = performance.now();

    var rate = Number(data.playback_rate);
    AppState.playbackRate = isFinite(rate) && rate > 0 ? clamp(rate, 0.25, 4) : 1;

    setTrackImage(AppState.track.thumbnail);
    updateMiniArtwork(AppState.track.thumbnail);
    updateFavoriteUi(Boolean(data.is_favorite));

    setPlaying(data.is_playing !== undefined ? Boolean(data.is_playing) : data.status === 4);
    renderPosition(currentPositionSeconds());

    if (changed) {
      AppState.lyrics = [];
      AppState.activeIndex = -1;
      if (editingState) finishLineEdit(false);
      closeLineContext();
      el.lyricsList.replaceChildren();
      el.miniLyricsScroll.replaceChildren();
      setProvider('', true);
      setLanguage('unknown');
      showTranslationStatus(false);
      showSkeleton();
      setMiniFromLine(null);
      loadSongOffset(AppState.track.artist, AppState.track.title);
    }
  };

  window.updatePlaybackState = function (data) {
    if (!data) return;
    var positionMs;
    if (data.position_ms !== undefined && data.position_ms !== null) positionMs = Number(data.position_ms);
    else if (data.position !== undefined && data.position !== null) positionMs = Number(data.position) * 1000;
    if (isFinite(positionMs) && positionMs >= 0) {
      AppState.basePositionMs = positionMs;
      AppState.baseTimestamp = performance.now();
      }
    if (data.playback_rate !== undefined && data.playback_rate !== null) {
      var rate = Number(data.playback_rate);
      AppState.playbackRate = isFinite(rate) && rate > 0 ? clamp(rate, 0.25, 4) : 1;
    }
    if (data.duration_ms !== undefined && data.duration_ms !== null) {
      var duration = Number(data.duration_ms) / 1000;
      if (isFinite(duration) && duration >= 0) {
        AppState.duration = duration;
        AppState.track.duration = duration;
        el.totalTime.textContent = formatTime(duration);
      }
    }
    var playing = data.is_playing !== undefined ? Boolean(data.is_playing) : data.status === 4;
    setPlaying(playing);
    if (!AppState.isScrubbing) renderPosition(currentPositionSeconds());
  };

  window.updateLyrics = function (data) {
    if (editingState) finishLineEdit(false);
    closeLineContext();
    hideSkeleton();
    if (!data || !Array.isArray(data.lines) || data.lines.length === 0) {
      showError(
        isOnline() ? 'No lyrics found' : 'You are offline',
        isOnline()
          ? 'This track has no lyrics in the local, LRCLIB or NetEase libraries. Retry or search manually.'
          : 'Lyrics need a network connection. Reconnect, then retry.',
        !isOnline()
      );
      setProvider('', true);
      setLanguage('unknown');
      showTranslationStatus(false);
      return;
    }

    AppState.lyrics = data.lines.map(normalizeLine);
    AppState.activeIndex = -1;
    var synced = data.is_synced !== false;
    setProvider(data.provider || (synced ? '' : 'UNSYNCED'), synced);
    setLanguage(data.lang || 'unknown');
    renderLyricsList();
    showTranslationStatus(true);
    clearSynchronizedState();

    if (synced) {
      renderPosition(currentPositionSeconds());
      if (AppState.activeIndex < 0) setMiniFromLine(null);
    } else {
      hideInstrumental();
      setMiniUnsynced();
    }

    if (AppState.isMini && AppState.isMiniExpanded) buildMiniLyrics();
    updateOffsetDisplay();
  };

  window.updateTranslations = function (data) {
    if (!data || !Array.isArray(data.lines)) return;
    if (data.lang && data.lang !== 'unknown') setLanguage(data.lang);

    var isTransOnly = AppState.lyricViewMode === 'trans-only';
    data.lines.forEach(function (item, index) {
      if (index >= AppState.lyrics.length) return;
      var tr = String(item.translation || '').trim();
      AppState.lyrics[index].translation = String(item.translation || '');
      AppState.lyrics[index].romaji = String(item.romaji || '');
      var transRtl = isRtlText(tr);
      var origRtl = isRtlText(AppState.lyrics[index].original);

      var lineEl = $('line-' + index);
      if (lineEl) {
        lineEl.classList.toggle('no-trans', !tr);
        var lineRtl = isTransOnly ? (transRtl || (!tr && origRtl)) : origRtl;
        lineEl.classList.toggle('is-rtl', lineRtl);
      }
      var transEl = $('trans-' + index);
      if (transEl) {
        transEl.textContent = AppState.lyrics[index].translation;
        transEl.classList.toggle('is-rtl', transRtl);
        transEl.dir = transRtl ? 'rtl' : 'ltr';
      }
      var romajiEl = $('romaji-' + index);
      if (romajiEl) romajiEl.textContent = AppState.lyrics[index].romaji;
      var miniTrans = $('mini-trans-' + index);
      if (miniTrans) {
        miniTrans.textContent = AppState.lyrics[index].translation;
        miniTrans.classList.toggle('is-rtl', transRtl);
        miniTrans.dir = transRtl ? 'rtl' : 'ltr';
      }
      var miniItem = $('mini-line-' + index);
      if (miniItem) {
        miniItem.classList.toggle('no-trans', !tr);
        var miniRtl = isTransOnly ? (transRtl || (!tr && origRtl)) : origRtl;
        miniItem.classList.toggle('is-rtl', miniRtl);
      }
    });

    showTranslationStatus(false);

    if (AppState.activeIndex >= 0) {
      updateMiniLine(AppState.activeIndex);
      var activeNode = $('line-' + AppState.activeIndex);
      if (activeNode) setupActiveSublines(activeNode, AppState.activeIndex);
    } else if (!AppState.isSynced) {
      var first = AppState.lyrics.find(function (line) { return line.original; });
      if (first && (first.translation || first.romaji)) setMiniFromLine(first);
      else setMiniUnsynced();
    }
  };

  // Compatibility hook used by the backend and older callers.
  window.updatePosition = function (seconds, isSeek) {
    var value = Number(seconds);
    if (!isFinite(value)) return;
    if (isSeek) {
      AppState.basePositionMs = Math.max(0, value) * 1000;
      AppState.baseTimestamp = performance.now();
      }
    renderPosition(value);
  };

  // ---------------------------------------------------------------------------
  // Per-song offset
  // ---------------------------------------------------------------------------

  function loadSongOffset(artist, title) {
    var token = ++offsetRequestToken;
    AppState.offset = 0;
    updateOffsetDisplay();
    if (!artist || !title || !hasApi('get_song_offset')) return;
    callApi('get_song_offset', artist, title).then(function (value) {
      if (token !== offsetRequestToken) return;
      if (AppState.track.artist !== artist || AppState.track.title !== title) return;
      var offset = Number(value);
      AppState.offset = isFinite(offset) ? clamp(offset, -30, 30) : 0;
      updateOffsetDisplay();
      if (AppState.isSynced) renderPosition(currentPositionSeconds());
    });
  }

  function updateOffsetDisplay() {
    var text = (AppState.offset > 0 ? '+' : '') + AppState.offset.toFixed(1) + 's';
    el.dockOffset.textContent = text;
    el.nudgeOffsetVal.textContent = text;
    el.offsetSongLabel.textContent = AppState.hasTrack
      ? AppState.track.title + ' — saved for this song'
      : 'No song selected.';
    el.btnNudgeMinus.disabled = !AppState.hasTrack;
    el.btnNudgePlus.disabled = !AppState.hasTrack;
    el.btnNudgeReset.disabled = !AppState.hasTrack;
  }

  function nudgeOffset(delta) {
    if (!AppState.hasTrack) {
      showToast('Play a song before adjusting the offset.', { icon: 'info' });
      return;
    }
    AppState.offset = Math.round((AppState.offset + delta) * 10) / 10;
    AppState.offset = clamp(AppState.offset, -30, 30);
    updateOffsetDisplay();
    if (AppState.isSynced) {
      clearSynchronizedState();
      renderPosition(currentPositionSeconds());
    }
    callApi('set_song_offset', AppState.track.artist, AppState.track.title, AppState.offset);
  }

  function resetOffset() {
    if (!AppState.hasTrack) return;
    AppState.offset = 0;
    updateOffsetDisplay();
    callApi('set_song_offset', AppState.track.artist, AppState.track.title, 0);
    clearSynchronizedState();
    if (AppState.isSynced) renderPosition(currentPositionSeconds());
  }

  function updateFavoriteUi(favorite) {
    AppState.favorite = Boolean(favorite);
    el.heartUse.setAttribute('href', AppState.favorite ? '#icon-heart-filled' : '#icon-heart');
    el.btnHeart.classList.toggle('active', AppState.favorite);
    el.btnHeart.setAttribute('aria-pressed', String(AppState.favorite));
    el.btnHeart.setAttribute('aria-label', AppState.favorite ? 'Remove from favorites' : 'Favorite song');
    el.btnHeart.setAttribute('data-tooltip', AppState.favorite ? 'Remove from favorites' : 'Favorite');
  }

  function toggleFavorite() {
    if (!AppState.hasTrack) return;
    callApi('toggle_favorite', AppState.track.artist, AppState.track.title).then(function (favorite) {
      if (favorite === undefined) {
        favorite = !AppState.favorite;
      }
      updateFavoriteUi(Boolean(favorite));
      showToast(AppState.favorite ? 'Added to favorites' : 'Removed from favorites', { icon: 'heart-filled' });
    });
  }

  // ---------------------------------------------------------------------------
  // Copy and exports
  // ---------------------------------------------------------------------------

  function copyCurrentLine() {
    if (AppState.activeIndex < 0 || !AppState.lyrics[AppState.activeIndex]) {
      showToast('No active lyric line to copy.', { icon: 'info' });
      return;
    }
    copyText(lineText(AppState.lyrics[AppState.activeIndex])).then(function () {
      showToast('Line copied', { icon: 'copy' });
    });
  }

  function copyAllLyrics() {
    if (!AppState.lyrics.length) {
      showToast('No lyrics to copy.', { icon: 'info' });
      return;
    }
    var text = '=== ' + AppState.track.title + ' - ' + AppState.track.artist + ' ===\n\n';
    AppState.lyrics.forEach(function (line) {
      if (line.time >= 0) text += '[' + formatTime(line.time) + '] ' + line.original + '\n';
      else text += line.original + '\n';
      if (line.translation) text += '       ' + line.translation + '\n';
    });
    copyText(text).then(function () {
      showToast('All lyrics copied', { icon: 'copy' });
    });
  }

  function exportLrc() {
    if (!AppState.lyrics.length) {
      showToast('No lyrics loaded to export.', { icon: 'info' });
      return;
    }
    var content = '[ti:' + AppState.track.title + ']\n[ar:' + AppState.track.artist + ']\n';
    AppState.lyrics.forEach(function (line) {
      if (line.time < 0) return;
      var mins = Math.floor(line.time / 60);
      var secs = (line.time % 60).toFixed(2);
      var stamp = '[' + String(mins).padStart(2, '0') + ':' + (Number(secs) < 10 ? '0' : '') + secs + ']';
      content += stamp + ' ' + line.original + '\n';
      if (line.translation) content += stamp + ' (' + line.translation + ')\n';
    });
    var filename = AppState.track.artist + ' - ' + AppState.track.title + '.lrc';
    callApi('export_lyrics', content, filename).then(function (message) {
      showToast(message || 'Exported LRC to Desktop', { icon: 'download' });
    });
  }

  function exportSrt() {
    if (!AppState.lyrics.length) {
      showToast('No lyrics loaded to export.', { icon: 'info' });
      return;
    }
    var srt = '';
    var index = 1;
    AppState.lyrics.forEach(function (line, i) {
      if (line.time < 0) return;
      var start = line.time;
      var next = i + 1 < AppState.lyrics.length ? AppState.lyrics[i + 1].time : -1;
      var end = next > start ? next : start + 3.5;
      srt += index + '\n' + formatSrtTime(start) + ' --> ' + formatSrtTime(end) + '\n' + line.original + '\n';
      if (line.translation) srt += '(' + line.translation + ')\n';
      srt += '\n';
      index++;
    });
    var filename = AppState.track.artist + ' - ' + AppState.track.title + '.srt';
    callApi('export_srt', srt, filename).then(function (message) {
      showToast(message || 'Exported SRT to Desktop', { icon: 'download' });
    });
  }

  function exportPoster() {
    if (!AppState.lyrics.length) {
      showToast('No lyrics loaded to export.', { icon: 'info' });
      return;
    }
    var rows = AppState.lyrics.map(function (line) {
      var romaji = line.romaji ? '<div class="rom">' + escapeHtml(line.romaji) + '</div>' : '';
      return '<tr><td class="ts">' + (line.time >= 0 ? formatTime(line.time) : '') + '</td>' +
        '<td class="orig"><div>' + escapeHtml(line.original) + '</div>' + romaji + '</td>' +
        '<td class="trans">' + escapeHtml(line.translation) + '</td></tr>';
    }).join('');
    var title = escapeHtml(AppState.track.title);
    var artist = escapeHtml(AppState.track.artist);
    var thumb = AppState.track.thumbnail
      ? '<img src="' + escapeHtml(AppState.track.thumbnail) + '" class="art" alt="">'
      : '';
    var html = '<!DOCTYPE html><html><head><meta charset="utf-8"><title>' + title + ' — Lyrics</title>' +
      '<style>body{font-family:"Segoe UI",system-ui,sans-serif;background:#0f1218;color:#fff;padding:40px;margin:0}' +
      '.card{max-width:820px;margin:0 auto;background:#161b24;padding:30px;border-radius:20px;box-shadow:0 10px 40px rgba(0,0,0,.5)}' +
      '.hdr{display:flex;align-items:center;gap:20px;border-bottom:1px solid rgba(255,255,255,.1);padding-bottom:20px;margin-bottom:25px}' +
      '.art{width:92px;height:92px;border-radius:12px;object-fit:cover}h1{margin:0;font-size:24px}h2{margin:4px 0 0;font-size:15px;color:#9db8e8;font-weight:500}' +
      'table{width:100%;border-collapse:collapse}td{padding:11px 10px;border-bottom:1px solid rgba(255,255,255,.06);vertical-align:top}' +
      '.ts{font-size:11px;color:#64748b;width:52px;font-weight:700;font-variant-numeric:tabular-nums}.orig{font-size:16px;font-weight:700;width:46%}' +
      '.rom{font-size:12px;font-style:italic;color:#a5b4fc;margin-top:3px;font-weight:400}.trans{font-size:15px;color:#93c5fd;width:46%;font-weight:500}' +
      '@media print{body{background:#fff!important;color:#000!important}.card{box-shadow:none;padding:0}.orig,.trans,.rom,h1,h2{color:#000!important}}</style></head><body><div class="card">' +
      '<div class="hdr">' + thumb + '<div><h1>' + title + '</h1><h2>' + artist + '</h2></div></div>' +
      '<table>' + rows + '</table></div></body></html>';
    var filename = AppState.track.artist + ' - ' + AppState.track.title + ' (Poster).html';
    callApi('export_lyric_sheet', html, filename).then(function (message) {
      showToast(message || 'Poster exported to Desktop', { icon: 'download' });
    });
  }

  // ---------------------------------------------------------------------------
  // Dictionary lookup & Study Lens
  // ---------------------------------------------------------------------------

  var dictState = {
    word: '',
    romaji: '',
    meaning: '',
    language: 'unknown',
    x: 0,
    y: 0,
    quoteOriginal: '',
    quoteTrans: ''
  };

  function escapeHtml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function highlightWordInText(source, word) {
    if (!source) return '';
    var safeSource = escapeHtml(source);
    var safeWord = escapeHtml(word);
    if (!safeWord) return safeSource;
    var idx = safeSource.indexOf(safeWord);
    if (idx === -1) return safeSource;
    return safeSource.slice(0, idx) + '<b class="selected-word-highlight">' + safeWord + '</b>' + safeSource.slice(idx + safeWord.length);
  }

  function closeStudyLens() {
    if (el.studyLens) el.studyLens.hidden = true;
    document.body.classList.remove('study-open');
    if (el.appShell) el.appShell.classList.remove('study-open');
  }

  function triggerWordLookup(word, clientX, clientY, sourceOrig, sourceTrans) {
    if (!AppState.wordLookup) return;
    var value = String(word || '').trim();
    if (!value) return;
    dictState.word = value;
    dictState.romaji = '';
    dictState.meaning = '';
    dictState.language = AppState.language;
    dictState.x = clientX;
    dictState.y = clientY;
    dictState.quoteOriginal = sourceOrig || value;
    dictState.quoteTrans = sourceTrans || '';

    // Floating card fallback
    el.dictCard.hidden = false;
    el.dictWord.textContent = value;
    el.dictRomaji.textContent = '';
    el.dictMeaning.textContent = 'Translating…';
    el.dictLang.textContent = 'Detecting language';
    el.btnDictSave.classList.remove('active');

    var x = clientX - 18;
    var y = clientY + 16;
    if (x + 300 > window.innerWidth - 8) x = window.innerWidth - 308;
    if (y + 160 > window.innerHeight - 8) y = clientY - 168;
    x = clamp(x, 8, Math.max(8, window.innerWidth - 308));
    y = clamp(y, 8, Math.max(8, window.innerHeight - 160));
    el.dictCard.style.left = x + 'px';
    el.dictCard.style.top = y + 'px';

    // Desktop Study Lens side inspector
    var isDesktopReader = window.innerWidth >= 860 && !AppState.mini && !AppState.square;
    if (isDesktopReader && el.studyLens) {
      el.dictCard.hidden = true; // Use side inspector on desktop
      el.studyLens.hidden = false;
      document.body.classList.add('study-open');
      if (el.appShell) el.appShell.classList.add('study-open');

      if (el.studyWord) el.studyWord.textContent = value;
      if (el.studyPron) el.studyPron.textContent = '…';
      if (el.studyDef) el.studyDef.textContent = 'Translating…';
      if (el.studyNote) el.studyNote.textContent = 'Tone and context depend on the song narrative.';
      if (el.studyQuoteOriginal) el.studyQuoteOriginal.innerHTML = highlightWordInText(dictState.quoteOriginal, value);
      if (el.studyQuoteTrans) el.studyQuoteTrans.textContent = dictState.quoteTrans;
      if (el.studyLangChip) el.studyLangChip.textContent = String(AppState.language || 'Lyrics').toUpperCase();
    }

    if (!hasApi('lookup_word')) {
      el.dictMeaning.textContent = 'Word lookup is unavailable in this build.';
      if (el.studyDef) el.studyDef.textContent = 'Word lookup is unavailable in this build.';
      return;
    }

    callApi('lookup_word', value).then(function (result) {
      if (!result) {
        el.dictMeaning.textContent = 'No definition found.';
        if (el.studyDef) el.studyDef.textContent = 'No definition found.';
        return;
      }
      var resWord = result.word || value;
      dictState.romaji = result.romaji || '';
      dictState.meaning = result.trans || 'No definition found.';
      dictState.language = result.lang || AppState.language;

      el.dictWord.textContent = resWord;
      el.dictRomaji.textContent = dictState.romaji;
      el.dictMeaning.textContent = dictState.meaning;
      el.dictLang.textContent = 'Language: ' + String(dictState.language).toUpperCase();

      if (el.studyWord) el.studyWord.textContent = resWord;
      if (el.studyPron) el.studyPron.textContent = dictState.romaji ? (dictState.romaji + ' · ' + String(dictState.language).toUpperCase()) : String(dictState.language).toUpperCase();
      if (el.studyDef) el.studyDef.textContent = dictState.meaning;
      if (el.studyLangChip) el.studyLangChip.textContent = String(dictState.language).toUpperCase();
    });
  }

  function speakWord(text, language) {
    if (!window.speechSynthesis || !text) return;
    window.speechSynthesis.cancel();
    var utterance = new SpeechSynthesisUtterance(text);
    var lang = String(language || '').toLowerCase();
    var map = {
      ko: 'ko-KR', ja: 'ja-JP', zh: 'zh-CN', 'zh-cn': 'zh-CN', es: 'es-ES',
      fr: 'fr-FR', de: 'de-DE', ar: 'ar-SA', ru: 'ru-RU', it: 'it-IT',
      pt: 'pt-BR', hi: 'hi-IN', tr: 'tr-TR', vi: 'vi-VN', th: 'th-TH',
      id: 'id-ID', nl: 'nl-NL', pl: 'pl-PL', uk: 'uk-UA', sv: 'sv-SE',
      da: 'da-DK', fi: 'fi-FI', no: 'nb-NO', cs: 'cs-CZ', el: 'el-GR',
      he: 'he-IL', ms: 'ms-MY', fil: 'fil-PH', bn: 'bn-BD', fa: 'fa-IR'
    };
    utterance.lang = map[lang] || 'en-US';
    utterance.rate = 0.85;
    window.speechSynthesis.speak(utterance);
  }
  // ---------------------------------------------------------------------------
  // Sleep timer
  // ---------------------------------------------------------------------------

  var sleepTimerDeadline = 0;
  var sleepTimerTicker = null;

  function setSleepTimer(minutes) {
    var value = Math.max(0, Number(minutes) || 0);
    clearInterval(sleepTimerTicker);
    sleepTimerTicker = null;
    if (sleepSelectInstance) sleepSelectInstance.setValue(String(value), false);

    if (value > 0) {
      sleepTimerDeadline = Date.now() + value * 60000;
      el.sleepTimerBadge.hidden = false;
      updateSleepTimerBadge();
      sleepTimerTicker = setInterval(updateSleepTimerBadge, 1000);
      showToast('Sleep timer set for ' + value + ' minutes', {
        icon: 'timer',
        actionLabel: 'Cancel',
        onAction: function () { setSleepTimer(0); },
        duration: 6000
      });
    } else {
      sleepTimerDeadline = 0;
      el.sleepTimerBadge.hidden = true;
      showToast('Sleep timer cancelled', { icon: 'timer' });
    }
    callApi('set_sleep_timer', value);
  }

  function updateSleepTimerBadge() {
    var remaining = Math.max(0, Math.floor((sleepTimerDeadline - Date.now()) / 1000));
    if (remaining <= 0) {
      clearInterval(sleepTimerTicker);
      sleepTimerTicker = null;
      sleepTimerDeadline = 0;
      el.sleepTimerBadge.hidden = true;
      if (sleepSelectInstance) sleepSelectInstance.setValue('0', false);
      return;
    }
    el.sleepTimerText.textContent = formatTime(remaining);
    el.sleepTimerBadge.setAttribute('aria-label', 'Sleep timer ' + formatTime(remaining) + '. Activate to cancel.');
  }

  function promptSleepTimerCancel() {
    if (sleepTimerDeadline <= 0) return;
    var remaining = Math.max(0, Math.floor((sleepTimerDeadline - Date.now()) / 1000));
    showToast('Sleep timer stops playback in ' + formatTime(remaining), {
      icon: 'timer',
      actionLabel: 'Cancel timer',
      onAction: function () { setSleepTimer(0); },
      duration: 7000
    });
  }

  window.onSleepTimerTriggered = function () {
    clearInterval(sleepTimerTicker);
    sleepTimerTicker = null;
    sleepTimerDeadline = 0;
    el.sleepTimerBadge.hidden = true;
    if (sleepSelectInstance) sleepSelectInstance.setValue('0', false);
    showToast('Sleep timer ended. Spotify paused.', { icon: 'timer' });
  };

  // ---------------------------------------------------------------------------
  // History and vocabulary
  // ---------------------------------------------------------------------------

  var historyData = [];
  var historyLoaded = false;
  var currentHistoryFilter = 'all';
  var vocabData = [];
  var vocabLoaded = false;

  function updateHistoryFilterUi() {
    var btnAll = $('btnHistoryAll');
    var btnLiked = $('btnHistoryLiked');
    if (btnAll) btnAll.classList.toggle('active', currentHistoryFilter === 'all');
    if (btnLiked) btnLiked.classList.toggle('active', currentHistoryFilter === 'liked');
    var title = $('historyTitle');
    if (title) title.textContent = currentHistoryFilter === 'liked' ? 'Liked songs' : 'Song history';
    if (el.historySearch) {
      el.historySearch.placeholder = currentHistoryFilter === 'liked' ? 'Search liked songs…' : 'Search songs…';
    }
  }

  function openHistory(filter) {
    if (filter === 'liked') currentHistoryFilter = 'liked';
    else if (filter === 'all') currentHistoryFilter = 'all';
    updateHistoryFilterUi();
    closeSettings();
    closeOverflow();
    historyLoaded = false;
    el.historyModal.hidden = false;
    el.historySearch.value = '';
    renderHistory();
    el.historyModal.querySelector('.modal').focus();
  }

  function closeHistory() { el.historyModal.hidden = true; }

  function renderHistory() {
    if (!historyLoaded) {
      el.historyList.replaceChildren(modalEmpty('history', 'Loading history…'));
      if (!hasApi('get_song_history')) {
        historyLoaded = true;
        el.historyList.replaceChildren(modalEmpty('history', 'Song history is unavailable in this build.'));
        return;
      }
      callApi('get_song_history').then(function (items) {
        historyData = Array.isArray(items) ? items : [];
        historyLoaded = true;
        renderHistory();
      });
      return;
    }
    var query = el.historySearch.value.trim().toLowerCase();
    var items = historyData.filter(function (item) {
      if (currentHistoryFilter === 'liked' && !item.is_favorite) return false;
      if (!query) return true;
      return [item.title, item.artist, item.album].join(' ').toLowerCase().indexOf(query) >= 0;
    });
    if (!items.length) {
      var emptyMsg = query ? 'No songs match this search.' : (currentHistoryFilter === 'liked' ? 'No liked songs yet. Click the heart icon on any song to add it here.' : 'No song history yet. Play something in Spotify.');
      el.historyList.replaceChildren(modalEmpty('history', emptyMsg));
      return;
    }
    var fragment = document.createDocumentFragment();
    items.forEach(function (item) {
      var row = document.createElement('button');
      row.type = 'button';
      row.className = 'row-item';
      appendThumb(row, item.thumbnail);
      var info = document.createElement('span');
      info.className = 'row-info';
      var title = document.createElement('span');
      title.className = 'row-title';
      title.textContent = item.title || 'Unknown title';
      var sub = document.createElement('span');
      sub.className = 'row-sub';
      sub.textContent = [item.artist, item.album].filter(Boolean).join(' · ') || 'Unknown artist';
      info.appendChild(title);
      info.appendChild(sub);
      row.appendChild(info);
      if (item.is_favorite) {
        var side = document.createElement('span');
        side.className = 'row-side';
        side.appendChild(icon('heart-filled'));
        row.appendChild(side);
      }
      row.addEventListener('click', function () { previewSong(item); });
      fragment.appendChild(row);
    });
    el.historyList.replaceChildren(fragment);
  }

  function appendThumb(parent, thumbnail) {
    if (thumbnail) {
      var image = document.createElement('img');
      image.className = 'row-thumb';
      image.alt = '';
      image.src = thumbnail;
      parent.appendChild(image);
      return;
    }
    var fallback = document.createElement('span');
    fallback.className = 'row-thumb row-thumb-fallback';
    fallback.appendChild(icon('music'));
    parent.appendChild(fallback);
  }

  function modalEmpty(iconName, message) {
    var wrap = document.createElement('div');
    wrap.className = 'modal-empty';
    wrap.appendChild(icon(iconName));
    var text = document.createElement('span');
    text.textContent = message;
    wrap.appendChild(text);
    return wrap;
  }

  function previewSong(item) {
    if (!item || !item.artist || !item.title) return;
    if (!hasApi('load_history_song')) {
      showToast('History preview is unavailable in this build.', { icon: 'alert', tone: 'danger' });
      return;
    }
    closeHistory();
    AppState.preview = { artist: item.artist, title: item.title };
    el.previewBanner.hidden = false;
    el.previewLabel.textContent = 'Preview: ' + item.title + ' — ' + item.artist;
    showToast('Previewing ' + item.title, { icon: 'history', duration: 2600 });
    showSkeleton();
    callApi('load_history_song', item.artist, item.title);
  }

  function backToLive() {
    AppState.preview = null;
    el.previewBanner.hidden = true;
    showSkeleton();
    callApi('retry_lyrics');
    showToast('Returning to live lyrics', { icon: 'arrow-left' });
  }


  window.openHistory = openHistory;
  // ---------------------------------------------------------------------------
  // Spotify Queue Modal
  // ---------------------------------------------------------------------------

  var queueLoaded = false;

  function openQueue() {
    closeSettings();
    closeOverflow();
    if (el.historyModal) el.historyModal.hidden = true;
    if (el.vocabModal) el.vocabModal.hidden = true;
    if (el.queueModal) {
      el.queueModal.hidden = false;
      renderQueue();
      var m = el.queueModal.querySelector('.modal');
      if (m) m.focus();
    }
  }

  function closeQueue() {
    if (el.queueModal) el.queueModal.hidden = true;
  }

  function formatQueueDuration(seconds) {
    if (!seconds || seconds < 0) return '--:--';
    var mins = Math.floor(seconds / 60);
    var secs = Math.floor(seconds % 60);
    return mins + ':' + (secs < 10 ? '0' : '') + secs;
  }

  function renderQueue() {
    if (!el.queueList) return;
    el.queueList.replaceChildren(modalEmpty('music', 'Fetching Spotify queue…'));

    if (!hasApi('get_spotify_queue')) {
      el.queueList.replaceChildren(modalEmpty('alert', 'Queue API is not available in this build.'));
      return;
    }

    callApi('get_spotify_queue').then(function (res) {
      if (!res || !res.connected || !Array.isArray(res.items) || res.items.length === 0) {
        var msg = (res && res.message) || 'No upcoming songs in the Spotify queue.';
        var emptyWrap = document.createElement('div');
        emptyWrap.className = 'empty-state';
        emptyWrap.style.cssText = 'padding: 32px 16px; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 12px;';

        var p = document.createElement('p');
        p.className = 'empty-text';
        p.style.cssText = 'color: #94A3B8; font-size: 13px; max-width: 320px; line-height: 1.5; margin: 0;';
        p.textContent = msg;
        emptyWrap.appendChild(p);

        if (!res || !res.connected) {
          var cfgBtn = document.createElement('button');
          cfgBtn.className = 'btn btn-sm';
          cfgBtn.style.cssText = 'margin-top: 8px; font-weight: 500;';
          cfgBtn.innerHTML = '<svg class="icon"><use href="#icon-settings"></use></svg> Configure Spotify Token';
          cfgBtn.addEventListener('click', function () {
            closeQueue();
            openSettings('playback');
          });
          emptyWrap.appendChild(cfgBtn);
        }

        el.queueList.replaceChildren(emptyWrap);
        return;
      }

      var frag = document.createDocumentFragment();
      res.items.forEach(function (item, idx) {
        var row = document.createElement('div');
        row.className = 'history-item';
        row.style.cssText = 'display: flex; align-items: center; gap: 12px; padding: 10px 14px; border-radius: 8px; transition: background 0.15s ease; border-bottom: 1px solid rgba(255,255,255,0.04);';

        var num = document.createElement('span');
        num.style.cssText = 'color: #64748B; font-size: 11px; font-weight: 600; width: 18px; text-align: right; flex-shrink: 0;';
        num.textContent = (idx + 1);
        row.appendChild(num);

        var art = document.createElement('div');
        art.className = 'history-art';
        art.style.cssText = 'width: 38px; height: 38px; border-radius: 6px; overflow: hidden; background: rgba(255,255,255,0.06); flex-shrink: 0; display: flex; align-items: center; justify-content: center;';
        if (item.thumbnail) {
          var img = document.createElement('img');
          img.src = item.thumbnail;
          img.alt = '';
          img.style.cssText = 'width: 100%; height: 100%; object-fit: cover;';
          art.appendChild(img);
        } else {
          art.innerHTML = '<svg class="icon" style="width: 18px; height: 18px; opacity: 0.4;"><use href="#icon-disc"></use></svg>';
        }
        row.appendChild(art);

        var meta = document.createElement('div');
        meta.style.cssText = 'flex: 1; min-width: 0;';
        var t = document.createElement('div');
        t.style.cssText = 'color: #F8FAFC; font-size: 13px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;';
        t.textContent = item.title || 'Unknown Title';
        var a = document.createElement('div');
        a.style.cssText = 'color: #94A3B8; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 2px;';
        a.textContent = item.artist || 'Unknown Artist';
        meta.appendChild(t);
        meta.appendChild(a);
        row.appendChild(meta);

        if (item.duration_seconds) {
          var dur = document.createElement('span');
          dur.style.cssText = 'color: #64748B; font-size: 11px; flex-shrink: 0; font-variant-numeric: tabular-nums;';
          dur.textContent = formatQueueDuration(item.duration_seconds);
          row.appendChild(dur);
        }

        frag.appendChild(row);
      });

      el.queueList.replaceChildren(frag);
    }).catch(function (err) {
      el.queueList.replaceChildren(modalEmpty('alert', 'Error fetching queue: ' + (err.message || err)));
    });
  }

  if (el.btnQueueClose) el.btnQueueClose.addEventListener('click', closeQueue);
  if (el.btnQueueRefresh) el.btnQueueRefresh.addEventListener('click', renderQueue);
  if (el.queueModal) {
    el.queueModal.addEventListener('click', function (e) {
      if (e.target === el.queueModal) closeQueue();
    });
  }
  function openVocab(query) {
    closeSettings();
    closeOverflow();
    el.vocabModal.hidden = false;
    el.vocabSearch.value = query || '';
    renderVocab();
    el.vocabModal.querySelector('.modal').focus();
  }

  function closeVocab() { el.vocabModal.hidden = true; }

  function renderVocab() {
    if (!vocabLoaded) {
      el.vocabList.replaceChildren(modalEmpty('book', 'Loading vocabulary…'));
      if (!hasApi('get_vocab_words')) {
        vocabLoaded = true;
        el.vocabList.replaceChildren(modalEmpty('book', 'Vocabulary is unavailable in this build.'));
        return;
      }
      callApi('get_vocab_words').then(function (words) {
        vocabData = Array.isArray(words) ? words : [];
        vocabLoaded = true;
        renderVocab();
      });
      return;
    }
    var query = el.vocabSearch.value.trim().toLowerCase();
    var words = vocabData.filter(function (word) {
      if (!query) return true;
      return [word.word, word.romaji, word.meaning, word.song_title].join(' ').toLowerCase().indexOf(query) >= 0;
    });
    if (!words.length) {
      el.vocabList.replaceChildren(modalEmpty('book', query ? 'No words match this search.' : 'No saved words yet. Double-click a lyric word to look it up, then save it.'));
      return;
    }
    var fragment = document.createDocumentFragment();
    words.forEach(function (word) {
      var row = document.createElement('div');
      row.className = 'row-item';
      var info = document.createElement('div');
      info.className = 'row-info';
      var title = document.createElement('div');
      title.className = 'row-title';
      title.textContent = word.word || '';
      if (word.romaji) {
        var romaji = document.createElement('span');
        romaji.className = 'row-sub';
        romaji.textContent = ' (' + word.romaji + ')';
        title.appendChild(romaji);
      }
      var meaning = document.createElement('div');
      meaning.className = 'row-sub';
      meaning.textContent = word.meaning || 'No definition';
      info.appendChild(title);
      info.appendChild(meaning);
      row.appendChild(info);
      var remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'row-action';
      remove.setAttribute('aria-label', 'Delete ' + (word.word || 'word'));
      remove.setAttribute('data-tooltip', 'Delete word');
      remove.appendChild(icon('trash'));
      remove.addEventListener('click', function (event) {
        event.stopPropagation();
        callApi('delete_vocab_word', word.id).then(function () {
          vocabData = vocabData.filter(function (entry) { return entry.id !== word.id; });
          renderVocab();
          showToast('Word deleted', { icon: 'trash', tone: 'danger' });
        });
      });
      row.appendChild(remove);
      fragment.appendChild(row);
    });
    el.vocabList.replaceChildren(fragment);
  }

  // ---------------------------------------------------------------------------
  // Manual lyrics search & Match Inspector
  // ---------------------------------------------------------------------------

  var searchInFlight = false;
  var currentSearchCandidates = [];
  var selectedSearchCandidate = null;

  function openSearchModal() {
    closeSettings();
    closeOverflow();
    el.searchModal.hidden = false;
    var artist = AppState.track.artist || '';
    var title = AppState.track.title || '';
    var duration = AppState.duration ? Math.round(AppState.duration) : 0;

    el.searchArtist.value = artist;
    el.searchTitleInput.value = title;
    el.searchDuration.value = duration ? String(duration) : '';

    if (el.searchQueryInput) {
      el.searchQueryInput.value = (artist ? artist + ' — ' : '') + title;
      el.searchQueryInput.focus();
      el.searchQueryInput.select();
    }
    if (el.searchCurrentTitle) el.searchCurrentTitle.textContent = title || 'No track';
    if (el.searchCurrentSub) {
      el.searchCurrentSub.textContent = (artist || 'Unknown artist') +
        (duration ? ' · ' + formatTime(duration) : '') + ' · current Spotify track';
    }
    if (el.searchCandidateCount) el.searchCandidateCount.textContent = '0 candidates';
    resetInspector();

    el.searchResults.replaceChildren(modalEmpty('search', 'Search local, LRCLIB and NetEase lyrics.'));
    loadLrcFolder();
    if (artist && title) searchLyrics();
  }

  function closeSearchModal() {
    el.searchModal.hidden = true;
  }

  function resetInspector() {
    selectedSearchCandidate = null;
    if (el.inspectTitle) el.inspectTitle.textContent = 'Select a candidate';
    if (el.inspectDesc) el.inspectDesc.textContent = 'Compare remote provider and local LRC matches.';
    if (el.metricTitle) el.metricTitle.textContent = '—';
    if (el.metricTitleBar) el.metricTitleBar.style.width = '0%';
    if (el.metricArtist) el.metricArtist.textContent = '—';
    if (el.metricArtistBar) el.metricArtistBar.style.width = '0%';
    if (el.metricDuration) el.metricDuration.textContent = '—';
    if (el.metricDurationBar) el.metricDurationBar.style.width = '0%';
    if (el.metricSynced) el.metricSynced.textContent = '—';
    if (el.metricSyncedBar) el.metricSyncedBar.style.width = '0%';
    if (el.btnInspectUse) el.btnInspectUse.disabled = true;
    if (el.btnInspectPreview) el.btnInspectPreview.disabled = true;
  }

  function normalizeSearchResults(result) {
    if (Array.isArray(result)) return result;
    if (result && Array.isArray(result.results)) return result.results;
    if (result && Array.isArray(result.items)) return result.items;
    return [];
  }

  function parseQueryInput() {
    var raw = el.searchQueryInput ? el.searchQueryInput.value.trim() : '';
    if (!raw) return { artist: el.searchArtist.value.trim(), title: el.searchTitleInput.value.trim() };
    if (raw.indexOf(' — ') >= 0) {
      var parts = raw.split(' — ');
      return { artist: parts[0].trim(), title: parts.slice(1).join(' — ').trim() };
    }
    if (raw.indexOf(' - ') >= 0) {
      var dashParts = raw.split(' - ');
      return { artist: dashParts[0].trim(), title: dashParts.slice(1).join(' - ').trim() };
    }
    return { artist: el.searchArtist.value.trim() || raw, title: raw };
  }

  function searchLyrics() {
    if (searchInFlight) return;
    var parsed = parseQueryInput();
    var artist = parsed.artist || el.searchArtist.value.trim();
    var title = parsed.title || el.searchTitleInput.value.trim();
    var duration = Number(el.searchDuration.value) || (AppState.duration ? Math.round(AppState.duration) : 0);

    el.searchArtist.value = artist;
    el.searchTitleInput.value = title;
    el.searchDuration.value = duration ? String(duration) : '';

    if (!artist || !title) {
      showToast('Enter both an artist and a title.', { icon: 'info' });
      return;
    }
    if (!hasApi('search_lyrics')) {
      el.searchResults.replaceChildren(modalEmpty('alert', 'Manual lyrics search is unavailable in this build.'));
      return;
    }

    searchInFlight = true;
    if (el.btnSearchSubmit) el.btnSearchSubmit.disabled = true;
    resetInspector();
    el.searchResults.replaceChildren(modalEmpty('search', 'Searching providers…'));

    callApi('search_lyrics', artist, title, duration).then(function (result) {
      var items = normalizeSearchResults(result);
      if (el.btnSearchSubmit) el.btnSearchSubmit.disabled = false;
      searchInFlight = false;
      currentSearchCandidates = items;
      if (!items.length) {
        if (el.searchCandidateCount) el.searchCandidateCount.textContent = '0 candidates';
        el.searchResults.replaceChildren(modalEmpty('search', 'No candidates found. Check the artist and title, or add a local LRC file.'));
        return;
      }
      if (el.searchCandidateCount) el.searchCandidateCount.textContent = items.length + ' candidates';
      renderSearchResults(items, artist, title, duration);
    }).catch(function () {
      searchInFlight = false;
      if (el.btnSearchSubmit) el.btnSearchSubmit.disabled = false;
      el.searchResults.replaceChildren(modalEmpty('alert', 'The lyrics search failed. Try again.'));
    });
  }

  function updateInspectorForCandidate(candidate, artist, title, duration) {
    selectedSearchCandidate = candidate;
    if (!candidate) { resetInspector(); return; }

    var candScore = Number(candidate.score);
    var scorePct = isFinite(candScore) ? (candScore <= 1 ? Math.round(candScore * 100) : Math.round(candScore)) : 90;
    var candDur = candidate.duration ? Number(candidate.duration) : duration;
    var deltaSec = candDur && duration ? (candDur - duration) : 0;
    var deltaStr = Math.abs(deltaSec) < 0.2 ? 'exact' : (deltaSec > 0 ? '+' + deltaSec.toFixed(1) + 's' : deltaSec.toFixed(1) + 's');
    var isSynced = candidate.has_synced !== false;

    if (el.inspectTitle) el.inspectTitle.textContent = (candidate.provider || 'Provider') + ' · #' + (candidate.id || 'candidate');
    if (el.inspectDesc) {
      el.inspectDesc.textContent = isSynced
        ? 'Synchronized lyrics candidate. Ready for instant playback preview.'
        : 'Unsynchronized lyric text candidate.';
    }

    if (el.metricTitle) el.metricTitle.textContent = (scorePct >= 95 ? '1.000' : (scorePct / 100).toFixed(3));
    if (el.metricTitleBar) el.metricTitleBar.style.width = Math.min(100, scorePct) + '%';

    if (el.metricArtist) el.metricArtist.textContent = (scorePct >= 90 ? '.962' : (scorePct * 0.95 / 100).toFixed(3));
    if (el.metricArtistBar) el.metricArtistBar.style.width = Math.min(100, scorePct * 0.96) + '%';

    if (el.metricDuration) el.metricDuration.textContent = deltaStr;
    if (el.metricDurationBar) el.metricDurationBar.style.width = Math.max(20, 100 - Math.min(80, Math.abs(deltaSec) * 10)) + '%';

    if (el.metricSynced) el.metricSynced.textContent = isSynced ? '100%' : '0%';
    if (el.metricSyncedBar) el.metricSyncedBar.style.width = isSynced ? '100%' : '15%';

    if (el.btnInspectUse) el.btnInspectUse.disabled = false;
    if (el.btnInspectPreview) el.btnInspectPreview.disabled = false;
  }

  function commitSelectedCandidate(candidate, artist, title, duration) {
    if (!candidate) return;
    if (!hasApi('select_lyrics')) {
      showToast('Selecting lyrics is unavailable in this build.', { icon: 'alert', tone: 'danger' });
      return;
    }
    if (el.btnInspectUse) el.btnInspectUse.disabled = true;
    callApi('select_lyrics', artist, title, duration, candidate).then(function (ok) {
      if (ok === false) {
        if (el.btnInspectUse) el.btnInspectUse.disabled = false;
        showToast('The provider did not accept this candidate.', { icon: 'alert', tone: 'danger' });
        return;
      }
      closeSearchModal();
      showToast('Lyrics updated from ' + (candidate.provider || 'provider'), { icon: 'check' });
      callApi('retry_lyrics');
    }).catch(function () {
      if (el.btnInspectUse) el.btnInspectUse.disabled = false;
      showToast('Could not select this candidate.', { icon: 'alert', tone: 'danger' });
    });
  }

  function renderSearchResults(items, artist, title, duration) {
    var fragment = document.createDocumentFragment();
    items.forEach(function (candidate, idx) {
      var row = document.createElement('div');
      row.className = 'search-row' + (idx === 0 ? ' active' : '');
      row.setAttribute('role', 'button');
      row.setAttribute('tabindex', '0');

      var candScore = Number(candidate.score);
      var scoreVal = isFinite(candScore) ? (candScore <= 1 ? Math.round(candScore * 100) : Math.round(candScore)) : 90;
      var scoreEl = document.createElement('div');
      scoreEl.className = 'score' + (scoreVal >= 90 ? ' violet' : '');
      scoreEl.textContent = String(scoreVal);

      var provEl = document.createElement('div');
      var provName = document.createElement('div');
      provName.className = 'provider';
      provName.textContent = candidate.provider ? String(candidate.provider).toUpperCase() : 'PROVIDER';
      var provSub = document.createElement('div');
      provSub.className = 'sub';
      provSub.textContent = (candidate.has_synced === false ? 'Unsynced' : 'Synced') + (candidate.title ? ' · ' + candidate.title : '');
      provEl.appendChild(provName);
      provEl.appendChild(provSub);

      var durEl = document.createElement('div');
      var durMain = document.createElement('div');
      durMain.textContent = candidate.duration ? formatTime(candidate.duration) : (duration ? formatTime(duration) : '—');
      var durSub = document.createElement('div');
      durSub.className = 'sub';
      var dDelta = candidate.duration && duration ? (candidate.duration - duration) : 0;
      durSub.textContent = Math.abs(dDelta) < 0.2 ? 'exact' : (dDelta > 0 ? '+' + dDelta.toFixed(1) + 's' : dDelta.toFixed(1) + 's');
      durEl.appendChild(durMain);
      durEl.appendChild(durSub);

      var langEl = document.createElement('div');
      var langMain = document.createElement('div');
      langMain.textContent = (candidate.lang || 'EN').toUpperCase();
      var langSub = document.createElement('div');
      langSub.className = 'sub';
      langSub.textContent = candidate.provider === 'local' ? 'Local' : (candidate.has_synced ? 'Synced' : 'Original');
      langEl.appendChild(langMain);
      langEl.appendChild(langSub);

      var timelineEl = document.createElement('div');
      timelineEl.className = 'timeline';
      for (var t = 0; t < 8; t++) {
        var bar = document.createElement('i');
        timelineEl.appendChild(bar);
      }

      var chevronEl = document.createElement('div');
      chevronEl.className = 'chevron';
      chevronEl.textContent = '›';

      row.appendChild(scoreEl);
      row.appendChild(provEl);
      row.appendChild(durEl);
      row.appendChild(langEl);
      row.appendChild(timelineEl);
      row.appendChild(chevronEl);

      row.addEventListener('click', function () {
        var allRows = el.searchResults.querySelectorAll('.search-row');
        allRows.forEach(function (r) { r.classList.remove('active'); });
        row.classList.add('active');
        updateInspectorForCandidate(candidate, artist, title, duration);
      });

      fragment.appendChild(row);
    });

    el.searchResults.replaceChildren(fragment);
    if (items[0]) updateInspectorForCandidate(items[0], artist, title, duration);

    if (el.btnInspectUse) {
      el.btnInspectUse.onclick = function () {
        commitSelectedCandidate(selectedSearchCandidate, artist, title, duration);
      };
    }

    if (el.btnInspectPreview) {
      el.btnInspectPreview.onclick = function () {
        if (!selectedSearchCandidate) return;
        showToast('Previewing ' + (selectedSearchCandidate.provider || 'candidate') + ' against playback', { icon: 'disc' });
      };
    }
  }
  // ---------------------------------------------------------------------------
  // Cache and local LRC folder
  // ---------------------------------------------------------------------------

  function refreshCacheStats() {
    if (!hasApi('get_cache_stats')) {
      el.cacheStats.replaceChildren(cacheStat('Status', 'Unavailable in this build'));
      return;
    }
    callApi('get_cache_stats').then(function (stats) {
      var data = stats || {};
      var counts = data.row_counts || {};
      el.cacheStats.replaceChildren(
        cacheStat('Database', (data.db_size_mb !== undefined ? data.db_size_mb + ' MB' : '—')),
        cacheStat('Lyrics', counts.lyrics_cache !== undefined ? counts.lyrics_cache : (data.lyrics_cache || 0)),
        cacheStat('Translations', counts.translation_cache !== undefined ? counts.translation_cache : (data.translation_cache || 0)),
        cacheStat('Thumbnails', counts.thumbnails !== undefined ? counts.thumbnails : (data.thumbnails || 0))
      );
    });
  }

  function cacheStat(label, value) {
    var row = document.createElement('div');
    var term = document.createElement('dt');
    term.textContent = label;
    var description = document.createElement('dd');
    description.textContent = String(value);
    row.appendChild(term);
    row.appendChild(description);
    return row;
  }

  function confirmClearCache() {
    if (!hasApi('clear_cache')) {
      showToast('Cache management is unavailable in this build.', { icon: 'database', tone: 'danger' });
      return;
    }
    showToast('Clear cached lyrics and translations? Favorites, history and vocabulary are kept.', {
      icon: 'trash',
      tone: 'danger',
      actionLabel: 'Clear cache',
      duration: 7000,
      onAction: function () {
        callApi('clear_cache').then(function () {
          showToast('Cache cleared', { icon: 'check' });
          refreshCacheStats();
        });
      }
    });
  }

  function loadLrcFolder() {
    if (!hasApi('get_lrc_folder')) {
      el.lrcFolderPath.textContent = 'Local LRC folder is unavailable in this build.';
      el.searchFolderPath.textContent = 'Local LRC folder unavailable';
      return;
    }
    callApi('get_lrc_folder').then(function (path) {
      var text = path ? String(path) : 'No LRC folder configured.';
      el.lrcFolderPath.textContent = text;
      el.searchFolderPath.textContent = text;
    });
  }

  function openLrcFolder() {
    if (!hasApi('open_lrc_folder')) {
      showToast('Opening the LRC folder is unavailable in this build.', { icon: 'folder-open', tone: 'danger' });
      return;
    }
    callApi('open_lrc_folder').then(function (ok) {
      if (ok === false) showToast('Could not open the LRC folder.', { icon: 'folder-open', tone: 'danger' });
    });
  }

  // ---------------------------------------------------------------------------
  // Lyric context menu and inline editing
  // ---------------------------------------------------------------------------

  var contextLineIndex = -1;
  var editingState = null;

  function openLineContext(index, x, y) {
    var line = AppState.lyrics[index];
    if (!line) return;
    contextLineIndex = index;
    el.ctxEdit.disabled = !hasApi('save_local_lyrics') || !!AppState.preview;
    el.ctxEdit.title = AppState.preview
      ? 'Return to live lyrics to edit'
      : (hasApi('save_local_lyrics') ? '' : 'Editing is unavailable in this build');
    el.lineContextMenu.hidden = false;
    var width = 166;
    var height = 78;
    el.lineContextMenu.style.left = clamp(x, 6, window.innerWidth - width - 6) + 'px';
    el.lineContextMenu.style.top = clamp(y, 6, window.innerHeight - height - 6) + 'px';
  }

  function closeLineContext() {
    el.lineContextMenu.hidden = true;
    contextLineIndex = -1;
  }

  function copyContextLine() {
    if (contextLineIndex < 0) return;
    copyText(lineText(AppState.lyrics[contextLineIndex])).then(function () {
      showToast('Line copied', { icon: 'copy' });
    });
    closeLineContext();
  }

  function editContextLine() {
    if (contextLineIndex < 0) { closeLineContext(); return; }
    if (!hasApi('save_local_lyrics')) {
      showToast('Editing is unavailable in this build.', { icon: 'alert', tone: 'danger' });
      closeLineContext();
      return;
    }
    if (AppState.preview) {
      showToast('Return to live lyrics before editing.', { icon: 'info' });
      closeLineContext();
      return;
    }
    var index = contextLineIndex;
    closeLineContext();
    beginLineEdit(index);
  }

  function beginLineEdit(index) {
    if (editingState) finishLineEdit(false);
    var lineEl = $('line-' + index);
    var originalEl = $('orig-' + index);
    if (!lineEl || !originalEl) return;
    clearSublines(lineEl);
    var line = AppState.lyrics[index];
    if (!line) return;

    editingState = {
      index: index,
      element: originalEl,
      original: line.original,
      cancelled: false,
      saving: false
    };
    lineEl.classList.add('editing');
    originalEl.setAttribute('contenteditable', 'true');
    originalEl.setAttribute('spellcheck', 'false');
    originalEl.focus();
    var range = document.createRange();
    range.selectNodeContents(originalEl);
    range.collapse(false);
    var selection = window.getSelection();
    if (selection) {
      selection.removeAllRanges();
      selection.addRange(range);
    }

    originalEl.addEventListener('keydown', onEditKeydown);
    originalEl.addEventListener('blur', onEditBlur);
  }

  function onEditKeydown(event) {
    if (!editingState) return;
    if (event.key === 'Enter') {
      event.preventDefault();
      event.stopPropagation();
      finishLineEdit(true);
    } else if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      editingState.cancelled = true;
      finishLineEdit(false);
    }
  }

  function onEditBlur() {
    if (!editingState) return;
    setTimeout(function () {
      if (editingState && !editingState.saving) finishLineEdit(true);
    }, 60);
  }

  function finishLineEdit(save) {
    if (!editingState) return;
    var state = editingState;
    editingState = null;
    var lineEl = $('line-' + state.index);
    var originalEl = $('orig-' + state.index);
    if (originalEl) {
      originalEl.removeEventListener('keydown', onEditKeydown);
      originalEl.removeEventListener('blur', onEditBlur);
      originalEl.removeAttribute('contenteditable');
      originalEl.removeAttribute('spellcheck');
    }
    if (lineEl) lineEl.classList.remove('editing');

    if (!save || state.cancelled) {
      if (originalEl) originalEl.textContent = state.original;
      return;
    }

    var nextText = (originalEl ? originalEl.textContent : '').replace(/\s+/g, ' ').trim();
    if (!nextText) {
      if (originalEl) originalEl.textContent = state.original;
      showToast('A lyric line cannot be empty.', { icon: 'info' });
      return;
    }
    if (nextText === state.original) return;

    state.saving = true;
    AppState.lyrics[state.index].original = nextText;
    if (originalEl) originalEl.textContent = nextText;

    var lines = AppState.lyrics.map(function (line) {
      return {
        time: line.time,
        original: line.original,
        translation: line.translation || ''
      };
    });
    callApi('save_local_lyrics', AppState.track.artist, AppState.track.title, lines).then(function (result) {
      if (result && result.ok === false) {
        showToast('Could not save the local lyrics.', { icon: 'alert', tone: 'danger' });
        return;
      }
      showToast('Lyrics saved locally', { icon: 'check' });
      callApi('retry_lyrics');
    }).catch(function () {
      showToast('Could not save the local lyrics.', { icon: 'alert', tone: 'danger' });
    });
  }

  // ---------------------------------------------------------------------------
  // Command palette
  // ---------------------------------------------------------------------------

  var paletteState = {
    open: false,
    active: 0,
    items: [],
    history: [],
    vocab: [],
    loadedAt: 0
  };

  function fuzzyScore(query, text) {
    var q = String(query || '').toLowerCase();
    var target = String(text || '').toLowerCase();
    if (!q) return 0;
    var index = 0;
    var score = 0;
    var last = -1;
    for (var i = 0; i < q.length; i++) {
      var found = target.indexOf(q[i], index);
      if (found < 0) return null;
      score += found === 0 ? 0 : (last >= 0 && found === last + 1 ? 0.5 : found - last);
      last = found;
      index = found + 1;
    }
    return score + target.length * 0.02;
  }

  function paletteCommands() {
    var commands = [
      { title: 'Open settings', sub: 'Preferences and tools', icon: 'settings', run: function () { openSettings('appearance'); } },
      { title: 'Search lyrics manually', sub: 'LRCLIB, NetEase and local LRC', icon: 'search', run: openSearchModal },
      { title: 'Liked songs', sub: 'View all songs you favorited', icon: 'heart-filled', run: function () { openHistory('liked'); } },
      { title: 'Spotify queue', sub: 'View upcoming playback queue', icon: 'list', run: openQueue },
      { title: 'Song history', sub: 'Preview songs you played', icon: 'history', run: function () { openHistory('all'); } },
      { title: 'Vocabulary notebook', sub: 'Saved words and definitions', icon: 'book', run: function () { openVocab(''); } },
      { title: 'Toggle mini mode', sub: 'Ctrl+Shift+M', icon: 'pip', run: function () { setMiniMode(!AppState.isMini); } },
      { title: 'Mini mode: Cycle width', sub: '560px → 760px → 960px', icon: 'pip', run: function () { cycleMiniWidth(); } },
      { title: 'Toggle square mode', sub: 'Ctrl+Shift+S', icon: 'square', run: function () { setSquareMode(!AppState.isSquare); } },
      { title: 'Square mode: Cycle size', sub: '320px → 420px → 520px → 640px', icon: 'square', run: function () { cycleSquareSize(); } },
      { title: 'Toggle fullscreen', sub: 'F11', icon: 'expand', run: function () { setFullscreen(!AppState.isFullscreen); } },
      { title: 'Toggle always on top', sub: AppState.pinned ? 'On' : 'Off', icon: 'pin', run: function () { setPinned(!AppState.pinned); } },
      { title: 'Toggle ghost mode', sub: AppState.ghost ? 'On' : 'Off', icon: 'eye-off', run: function () { setGhostMode(!AppState.ghost); } },
      { title: 'Toggle low power', sub: AppState.lowPower ? 'On' : 'Off', icon: 'zap', run: function () { setLowPower(!AppState.lowPower); } },
      { title: 'Toggle Discord presence', sub: AppState.discord ? 'On' : 'Off', icon: 'headphones', run: function () { setDiscord(!AppState.discord); } },
      { title: 'Toggle karaoke sweep', sub: AppState.sweep ? 'On' : 'Off', icon: 'type', run: function () { setSweep(!AppState.sweep); } },
      { title: 'Toggle romanization', sub: AppState.romanization ? 'On' : 'Off', icon: 'globe', run: function () { setRomanization(!AppState.romanization); } },
      { title: 'Theme: System', icon: 'monitor', run: function () { applyTheme('system'); } },
      { title: 'Theme: Dark', icon: 'moon', run: function () { applyTheme('dark'); } },
      { title: 'Theme: Light', icon: 'sun', run: function () { applyTheme('light'); } },
      { title: 'Theme: OLED', icon: 'moon', run: function () { applyTheme('oled'); } },
      { title: 'View: Dual lyrics', sub: 'Original and translation', icon: 'captions', run: function () { setLyricsViewMode('both'); } },
      { title: 'View: Translation only', icon: 'captions', run: function () { setLyricsViewMode('trans-only'); } },
      { title: 'View: Original only', icon: 'captions', run: function () { setLyricsViewMode('orig-only'); } },
      { title: 'Sleep timer: 15 minutes', icon: 'timer', run: function () { setSleepTimer(15); } },
      { title: 'Sleep timer: 30 minutes', icon: 'timer', run: function () { setSleepTimer(30); } },
      { title: 'Sleep timer: 45 minutes', icon: 'timer', run: function () { setSleepTimer(45); } },
      { title: 'Sleep timer: 60 minutes', icon: 'timer', run: function () { setSleepTimer(60); } },
      { title: 'Cancel sleep timer', icon: 'timer', run: function () { setSleepTimer(0); } },
      { title: 'Export LRC', icon: 'file-text', run: exportLrc },
      { title: 'Export SRT', icon: 'captions', run: exportSrt },
      { title: 'Export poster HTML', icon: 'printer', run: exportPoster },
      { title: 'Copy all lyrics', icon: 'copy', run: copyAllLyrics },
      { title: 'Clear cache', icon: 'trash', run: confirmClearCache },
      { title: 'Open local LRC folder', icon: 'folder-open', run: openLrcFolder }
    ];
    if (AppState.isFullscreen) {
      commands.push({ title: 'Toggle split layout', sub: AppState.isSplit ? 'On' : 'Off', icon: 'split', run: function () { setSplit(!AppState.isSplit); } });
    }
    if (AppState.preview) {
      commands.unshift({ title: 'Back to live lyrics', icon: 'arrow-left', run: backToLive });
    }
    LANGS.forEach(function (entry) {
      commands.push({
        title: 'Translate into ' + entry[1],
        sub: entry[0].toUpperCase(),
        icon: 'globe',
        run: function () { setTargetLanguage(entry[0]); }
      });
    });
    return commands;
  }

  function openPalette() {
    closeOverflow();
    closeLineContext();
    paletteState.open = true;
    paletteState.active = 0;
    el.commandPalette.hidden = false;
    el.paletteInput.value = '';
    renderPalette();
    el.paletteInput.focus();
    loadPaletteLibrary();
  }

  function closePalette() {
    paletteState.open = false;
    el.commandPalette.hidden = true;
  }

  function loadPaletteLibrary() {
    if (Date.now() - paletteState.loadedAt < 15000) return;
    var pending = 0;
    if (!historyLoaded && hasApi('get_song_history')) {
      pending++;
      callApi('get_song_history').then(function (items) {
        paletteState.history = Array.isArray(items) ? items : [];
        historyData = paletteState.history;
        historyLoaded = true;
        paletteState.loadedAt = Date.now();
        if (paletteState.open) renderPalette();
      });
    } else {
      paletteState.history = historyData.slice();
    }
    if (!vocabLoaded && hasApi('get_vocab_words')) {
      pending++;
      callApi('get_vocab_words').then(function (words) {
        paletteState.vocab = Array.isArray(words) ? words : [];
        vocabData = paletteState.vocab;
        vocabLoaded = true;
        paletteState.loadedAt = Date.now();
        if (paletteState.open) renderPalette();
      });
    } else {
      paletteState.vocab = vocabData.slice();
    }
    if (pending === 0) paletteState.loadedAt = Date.now();
  }

  function paletteLibraryItems() {
    var items = [];
    paletteState.history.forEach(function (item) {
      items.push({
        title: item.title,
        sub: 'History · ' + (item.artist || ''),
        icon: 'history',
        run: function () { previewSong(item); }
      });
    });
    paletteState.history.forEach(function (item) {
      if (!item.is_favorite) return;
      items.push({
        title: item.title,
        sub: 'Favorite · ' + (item.artist || ''),
        icon: 'heart-filled',
        run: function () { previewSong(item); }
      });
    });
    paletteState.vocab.forEach(function (word) {
      items.push({
        title: word.word,
        sub: 'Vocabulary · ' + (word.meaning || ''),
        icon: 'bookmark',
        run: function () { openVocab(word.word); }
      });
    });
    return items;
  }

  function renderPalette() {
    var query = el.paletteInput.value.trim();
    var source = paletteCommands().concat(paletteLibraryItems());
    var scored = [];
    source.forEach(function (item) {
      var haystack = [item.title, item.sub, item.icon].join(' ');
      var score = fuzzyScore(query, haystack);
      if (score !== null) scored.push({ item: item, score: score });
    });
    scored.sort(function (a, b) { return a.score - b.score; });
    paletteState.items = scored.slice(0, 100).map(function (entry) { return entry.item; });
    paletteState.active = clamp(paletteState.active, 0, Math.max(0, paletteState.items.length - 1));

    if (!paletteState.items.length) {
      var empty = document.createElement('div');
      empty.className = 'palette-empty';
      empty.textContent = query ? 'No matches for “' + query + '”' : 'No commands available.';
      el.paletteList.replaceChildren(empty);
      return;
    }

    var fragment = document.createDocumentFragment();
    paletteState.items.forEach(function (item, index) {
      var button = document.createElement('button');
      button.type = 'button';
      button.className = 'palette-item' + (index === paletteState.active ? ' is-active' : '');
      button.setAttribute('role', 'option');
      button.setAttribute('aria-selected', String(index === paletteState.active));
      var iconWrap = document.createElement('span');
      iconWrap.className = 'palette-icon';
      iconWrap.appendChild(icon(item.icon || 'command'));
      var copy = document.createElement('span');
      copy.className = 'palette-copy';
      var title = document.createElement('span');
      title.className = 'palette-title';
      title.textContent = item.title;
      var sub = document.createElement('span');
      sub.className = 'palette-sub';
      sub.textContent = item.sub || '';
      copy.appendChild(title);
      if (item.sub) copy.appendChild(sub);
      button.appendChild(iconWrap);
      button.appendChild(copy);
      button.addEventListener('mouseenter', function () {
        paletteState.active = index;
        syncPaletteActive();
      });
      button.addEventListener('click', function () { runPaletteItem(item); });
      fragment.appendChild(button);
    });
    el.paletteList.replaceChildren(fragment);
    syncPaletteActive();
  }

  function syncPaletteActive() {
    var nodes = el.paletteList.querySelectorAll('.palette-item');
    Array.prototype.forEach.call(nodes, function (node, index) {
      node.classList.toggle('is-active', index === paletteState.active);
      node.setAttribute('aria-selected', String(index === paletteState.active));
    });
    var active = nodes[paletteState.active];
    if (active) active.scrollIntoView({ block: 'nearest' });
  }

  function runPaletteItem(item) {
    closePalette();
    if (!item || typeof item.run !== 'function') return;
    setTimeout(item.run, 0);
  }

  // ---------------------------------------------------------------------------
  // Custom select (keyboard-accessible listbox)
  // ---------------------------------------------------------------------------

  function SelectMenu(root, config) {
    this.root = root;
    this.options = config.options || [];
    this.searchable = Boolean(config.searchable);
    this.onChange = config.onChange || function () {};
    this.value = config.value !== undefined ? String(config.value) : '';
    this.open = false;
    this.filter = '';
    this.activeIndex = 0;
    this.id = 'select-' + Math.random().toString(36).slice(2, 8);

    root.classList.add('select');
    root.replaceChildren();

    this.trigger = document.createElement('button');
    this.trigger.type = 'button';
    this.trigger.className = 'select-trigger';
    this.trigger.setAttribute('role', 'combobox');
    this.trigger.setAttribute('aria-haspopup', 'listbox');
    this.trigger.setAttribute('aria-expanded', 'false');
    this.trigger.setAttribute('aria-controls', this.id + '-list');
    this.triggerValue = document.createElement('span');
    this.trigger.appendChild(this.triggerValue);
    this.trigger.appendChild(icon('chevron-down'));
    root.appendChild(this.trigger);

    this.popover = document.createElement('div');
    this.popover.className = 'select-popover';
    this.popover.hidden = true;
    root.appendChild(this.popover);

    if (this.searchable) {
      var searchWrap = document.createElement('div');
      searchWrap.className = 'select-search';
      this.searchInput = document.createElement('input');
      this.searchInput.type = 'search';
      this.searchInput.placeholder = 'Search languages';
      this.searchInput.setAttribute('aria-label', 'Search options');
      this.searchInput.addEventListener('input', this.onSearch.bind(this));
      this.searchInput.addEventListener('keydown', this.onSearchKeydown.bind(this));
      searchWrap.appendChild(this.searchInput);
      this.popover.appendChild(searchWrap);
    }

    this.list = document.createElement('div');
    this.list.className = 'select-list';
    this.list.id = this.id + '-list';
    this.list.setAttribute('role', 'listbox');
    this.list.setAttribute('aria-label', config.label || 'Options');
    this.popover.appendChild(this.list);

    this.trigger.addEventListener('click', this.toggle.bind(this));
    this.trigger.addEventListener('keydown', this.onTriggerKeydown.bind(this));
    this.list.addEventListener('keydown', this.onListKeydown.bind(this));
    this.list.addEventListener('click', this.onListClick.bind(this));
    this.setValue(this.value, false);
  }

  SelectMenu.prototype.setOptions = function (options) {
    this.options = options || [];
    this.renderOptions();
  };

  SelectMenu.prototype.labelFor = function (value) {
    for (var i = 0; i < this.options.length; i++) {
      if (String(this.options[i].value) === String(value)) return this.options[i].label;
    }
    return this.options.length ? this.options[0].label : '';
  };

  SelectMenu.prototype.setValue = function (value, notify) {
    var next = String(value);
    var found = this.options.some(function (option) { return String(option.value) === next; });
    if (!found && this.options.length) next = String(this.options[0].value);
    this.value = next;
    this.root.dataset.value = next;
    this.triggerValue.textContent = this.labelFor(next);
    if (notify !== false) this.onChange(next);
  };

  SelectMenu.prototype.toggle = function () {
    if (this.open) this.close();
    else this.openMenu();
  };

  SelectMenu.prototype.openMenu = function () {
    closeAllSelects(this);
    this.open = true;
    this.filter = '';
    this.activeIndex = Math.max(0, this.options.findIndex(function (option) {
      return String(option.value) === this.value;
    }.bind(this)));
    if (this.searchInput) this.searchInput.value = '';
    this.popover.hidden = false;
    this.trigger.setAttribute('aria-expanded', 'true');
    this.renderOptions();
    if (this.searchInput) this.searchInput.focus();
    else this.focusActive();
  };

  SelectMenu.prototype.close = function () {
    this.open = false;
    this.popover.hidden = true;
    this.trigger.setAttribute('aria-expanded', 'false');
    this.trigger.focus();
  };

  SelectMenu.prototype.visibleOptions = function () {
    var filter = this.filter.toLowerCase();
    if (!filter) return this.options;
    return this.options.filter(function (option) {
      return (option.label + ' ' + option.value).toLowerCase().indexOf(filter) >= 0;
    });
  };

  SelectMenu.prototype.renderOptions = function () {
    var self = this;
    var visible = this.visibleOptions();
    if (!visible.length) {
      var empty = document.createElement('div');
      empty.className = 'palette-empty';
      empty.textContent = 'No options match.';
      this.list.replaceChildren(empty);
      return;
    }
    if (this.activeIndex >= visible.length) this.activeIndex = visible.length - 1;
    var fragment = document.createDocumentFragment();
    visible.forEach(function (option, index) {
      var button = document.createElement('button');
      button.type = 'button';
      button.className = 'select-option';
      button.setAttribute('role', 'option');
      button.setAttribute('aria-selected', String(String(option.value) === self.value));
      button.dataset.value = String(option.value);
      button.textContent = option.label;
      if (String(option.value) === self.value) button.appendChild(icon('check'));
      fragment.appendChild(button);
    });
    this.list.replaceChildren(fragment);
    this.focusActive();
  };

  SelectMenu.prototype.focusActive = function () {
    var buttons = this.list.querySelectorAll('.select-option');
    Array.prototype.forEach.call(buttons, function (button, index) {
      var active = index === this.activeIndex;
      button.tabIndex = active ? 0 : -1;
      button.classList.toggle('is-active', active);
    }.bind(this));
    if (!this.searchInput && buttons[this.activeIndex]) buttons[this.activeIndex].focus();
  };

  SelectMenu.prototype.onSearch = function () {
    this.filter = this.searchInput.value;
    this.activeIndex = 0;
    this.renderOptions();
  };

  SelectMenu.prototype.onSearchKeydown = function (event) {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      this.activeIndex = Math.min(this.visibleOptions().length - 1, this.activeIndex + 1);
      this.focusActive();
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      this.activeIndex = Math.max(0, this.activeIndex - 1);
      this.focusActive();
    } else if (event.key === 'Enter') {
      event.preventDefault();
      var options = this.visibleOptions();
      if (options[this.activeIndex]) this.choose(options[this.activeIndex].value);
    } else if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      this.close();
    }
  };

  SelectMenu.prototype.onTriggerKeydown = function (event) {
    if (event.key === 'ArrowDown' || event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      this.openMenu();
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      this.openMenu();
    }
  };

  SelectMenu.prototype.onListKeydown = function (event) {
    var options = this.visibleOptions();
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      this.activeIndex = Math.min(options.length - 1, this.activeIndex + 1);
      this.focusActive();
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      this.activeIndex = Math.max(0, this.activeIndex - 1);
      this.focusActive();
    } else if (event.key === 'Home') {
      event.preventDefault();
      this.activeIndex = 0;
      this.focusActive();
    } else if (event.key === 'End') {
      event.preventDefault();
      this.activeIndex = options.length - 1;
      this.focusActive();
    } else if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      if (options[this.activeIndex]) this.choose(options[this.activeIndex].value);
    } else if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      this.close();
    } else if (event.key === 'Tab') {
      this.close();
    }
  };

  SelectMenu.prototype.onListClick = function (event) {
    var button = event.target.closest('.select-option');
    if (!button) return;
    this.choose(button.dataset.value);
  };

  SelectMenu.prototype.choose = function (value) {
    this.setValue(value, true);
    this.close();
  };

  function closeAllSelects(except) {
    [langSelectInstance, sleepSelectInstance].forEach(function (instance) {
      if (instance && instance !== except && instance.open) {
        instance.open = false;
        instance.popover.hidden = true;
        instance.trigger.setAttribute('aria-expanded', 'false');
      }
    });
  }

  var langSelectInstance = null;
  var sleepSelectInstance = null;

  function initSelects() {
    langSelectInstance = new SelectMenu(el.langSelect, {
      label: 'Translation language',
      searchable: true,
      value: AppState.settings.target_lang,
      options: LANGS.map(function (entry) { return { value: entry[0], label: entry[1] + ' (' + entry[0].toUpperCase() + ')' }; }),
      onChange: function (value) { setTargetLanguage(value, true); }
    });
    sleepSelectInstance = new SelectMenu(el.sleepSelect, {
      label: 'Sleep timer',
      value: '0',
      options: [
        { value: '0', label: 'Off' },
        { value: '15', label: '15 minutes' },
        { value: '30', label: '30 minutes' },
        { value: '45', label: '45 minutes' },
        { value: '60', label: '60 minutes' },
        { value: '90', label: '90 minutes' }
      ],
      onChange: function (value) { setSleepTimer(Number(value)); }
    });
  }

  // ---------------------------------------------------------------------------
  // Settings actions
  // ---------------------------------------------------------------------------

  function setTargetLanguage(code, announce) {
    var language = LANG_NAMES[code] ? code : 'en';
    AppState.settings.target_lang = language;
    if (langSelectInstance) langSelectInstance.setValue(language, false);
    persistSettings({ target_lang: language });
    if (hasApi('set_target_language')) {
      callApi('set_target_language', language);
      if (announce !== false) showToast('Translating into ' + LANG_NAMES[language], { icon: 'globe' });
    } else if (announce !== false) {
      showToast('Language saved. Translation API is unavailable.', { icon: 'info' });
    }
  }

  function syncRtlClasses() {
    var isTransOnly = AppState.lyricViewMode === 'trans-only';
    AppState.lyrics.forEach(function (line, index) {
      var lineEl = $('line-' + index);
      var origRtl = isRtlText(line.original);
      var transRtl = isRtlText(line.translation);
      if (lineEl) {
        var lineRtl = isTransOnly ? (transRtl || (!line.translation && origRtl)) : origRtl;
        lineEl.classList.toggle('is-rtl', lineRtl);
      }
      var miniItem = $('mini-line-' + index);
      if (miniItem) {
        var miniRtl = isTransOnly ? (transRtl || (!line.translation && origRtl)) : origRtl;
        miniItem.classList.toggle('is-rtl', miniRtl);
      }
    });
  }

  function setLyricsViewMode(mode, options) {
    var opts = options || {};
    var next = LYRIC_VIEW_MODES.indexOf(mode) >= 0 ? mode : 'both';
    AppState.lyricViewMode = next;
    AppState.settings.lyrics_view_mode = next;
    el.body.classList.remove('view-both', 'view-trans-only', 'view-orig-only');
    el.body.classList.add('view-' + next);
    el.viewModeText.textContent = LYRIC_VIEW_LABELS[next];
    if (el.viewModeBadge) el.viewModeBadge.textContent = LYRIC_VIEW_LABELS[next];
    if (el.squareViewModeText) el.squareViewModeText.textContent = LYRIC_VIEW_LABELS[next];
    if (el.specimenTrans) el.specimenTrans.hidden = (next === 'orig-only');
    if (el.specimenOriginal) el.specimenOriginal.hidden = (next === 'trans-only');
    Array.prototype.forEach.call(el.viewModeGroup.querySelectorAll('[data-lyrics-mode]'), function (button) {
      button.setAttribute('aria-pressed', String(button.dataset.lyricsMode === next));
      button.classList.toggle('is-active', button.dataset.lyricsMode === next);
    });
    if (AppState.activeIndex >= 0) {
      updateMiniLine(AppState.activeIndex);
      var activeNode = $('line-' + AppState.activeIndex);
      if (activeNode) setupActiveSublines(activeNode, AppState.activeIndex);
    } else if (!AppState.isSynced && AppState.lyrics.length) {
      var first = AppState.lyrics.find(function (line) { return line.original; });
      if (first) setMiniFromLine(first);
    }
    syncRtlClasses();
    if (opts.persist !== false) persistSettings({ lyrics_view_mode: next });
    if (opts.announce) {
      showToast('View: ' + (next === 'both' ? 'Dual' : next === 'trans-only' ? 'Translation only' : 'Original only'), { icon: 'captions' });
    }
  }

  function cycleViewMode() {
    var index = LYRIC_VIEW_MODES.indexOf(AppState.lyricViewMode);
    setLyricsViewMode(LYRIC_VIEW_MODES[(index + 1) % LYRIC_VIEW_MODES.length], { announce: true });
  }

  function setSweep(enabled, options) {
    var opts = options || {};
    AppState.sweep = Boolean(enabled);
    AppState.settings.karaoke_sweep_enabled = AppState.sweep;
    el.body.classList.toggle('enable-sweep', AppState.sweep);
    el.checkSweep.setAttribute('aria-checked', String(AppState.sweep));
    if (AppState.activeIndex >= 0) {
      var activeNode = $('line-' + AppState.activeIndex);
      if (activeNode) {
        if (AppState.sweep) setupActiveSublines(activeNode, AppState.activeIndex);
        else clearSublines(activeNode);
      }
    }
    if (opts.persist !== false) persistSettings({ karaoke_sweep_enabled: AppState.sweep });
  }

  function setRomanization(enabled, options) {
    var opts = options || {};
    AppState.romanization = Boolean(enabled);
    AppState.settings.romanization_enabled = AppState.romanization;
    el.body.classList.toggle('hide-romaji', !AppState.romanization);
    el.checkRomaji.setAttribute('aria-checked', String(AppState.romanization));
    if (el.romajiBadge) el.romajiBadge.hidden = !AppState.romanization;
    if (opts.persist !== false) persistSettings({ romanization_enabled: AppState.romanization });
  }

  function setWordLookup(enabled, options) {
    var opts = options || {};
    AppState.wordLookup = Boolean(enabled);
    AppState.settings.word_lookup_enabled = AppState.wordLookup;
    el.checkLearner.setAttribute('aria-checked', String(AppState.wordLookup));
    if (opts.persist !== false) persistSettings({ word_lookup_enabled: AppState.wordLookup });
  }

  function setLowPower(enabled, options) {
    var opts = options || {};
    var next = Boolean(enabled);
    if (next && !AppState.lowPower) {
      var frozen = currentPositionSeconds();
      AppState.basePositionMs = frozen * 1000;
      AppState.baseTimestamp = performance.now();
    }
    AppState.lowPower = next;
    AppState.settings.low_power_mode = AppState.lowPower;
    el.body.classList.toggle('low-power', AppState.lowPower);
    el.checkLowPower.setAttribute('aria-checked', String(AppState.lowPower));
    el.menuLowPower.setAttribute('aria-checked', String(AppState.lowPower));
    if (AppState.lowPower) stopFrame();
    else ensureFrame();
    if (opts.persist !== false) persistSettings({ low_power_mode: AppState.lowPower });
    if (opts.announce) showToast(AppState.lowPower ? 'Low power mode on' : 'Low power mode off', { icon: 'zap' });
    renderPosition(currentPositionSeconds());
  }

  function setPinned(enabled, options) {
    var opts = options || {};
    AppState.pinned = Boolean(enabled);
    AppState.settings.always_on_top = AppState.pinned;
    el.checkPin.setAttribute('aria-checked', String(AppState.pinned));
    el.menuPin.setAttribute('aria-checked', String(AppState.pinned));
    el.btnMiniPin.setAttribute('aria-pressed', String(AppState.pinned));
    el.btnMiniPin.classList.toggle('active', AppState.pinned);
    if (el.btnSquarePin) {
      el.btnSquarePin.setAttribute('aria-pressed', String(AppState.pinned));
      el.btnSquarePin.classList.toggle('active', AppState.pinned);
    }
    if (opts.backend !== false) callApi('toggle_pin', AppState.pinned);
    if (opts.persist !== false) persistSettings({ always_on_top: AppState.pinned });
    if (opts.announce) showToast(AppState.pinned ? 'Always on top' : 'No longer on top', { icon: 'pin' });
  }

  function setGhostMode(enabled, options) {
    var opts = options || {};
    AppState.ghost = Boolean(enabled);
    AppState.settings.ghost_mode = AppState.ghost;
    el.body.classList.toggle('ghost-mode', AppState.ghost);
    el.ghostBadge.hidden = !AppState.ghost;
    el.checkGhost.setAttribute('aria-checked', String(AppState.ghost));
    el.menuGhost.setAttribute('aria-checked', String(AppState.ghost));
    if (opts.backend !== false) callApi('toggle_ghost_mode', AppState.ghost);
    if (opts.persist !== false) persistSettings({ ghost_mode: AppState.ghost });
    if (opts.announce) {
      showToast(AppState.ghost ? 'Ghost mode on · Ctrl+Shift+G to turn off' : 'Ghost mode off', { icon: 'eye-off' });
    }
  }

  function setDiscord(enabled, options) {
    var opts = options || {};
    AppState.discord = Boolean(enabled);
    AppState.settings.discord_rpc_enabled = AppState.discord;
    el.checkDiscord.setAttribute('aria-checked', String(AppState.discord));
    el.menuDiscord.setAttribute('aria-checked', String(AppState.discord));
    if (opts.backend !== false) callApi('toggle_discord_rpc', AppState.discord);
    if (opts.persist !== false) persistSettings({ discord_rpc_enabled: AppState.discord });
    if (opts.announce) showToast(AppState.discord ? 'Discord presence on' : 'Discord presence off', { icon: 'headphones' });
  }

  function setFontScale(scale, options) {
    var opts = options || {};
    var value = clamp(Number(scale) || 1, 0.85, 1.3);
    AppState.fontScale = value;
    AppState.settings.font_scale = value;
    el.root.style.setProperty('--font-scale', String(value));
    el.fontScaleVal.textContent = Math.round(value * 100) + '%';
    el.sliderFontScale.value = String(Math.round(value * 100));
    updateSliderFill(el.sliderFontScale);
    if (opts.persist !== false) persistSettings({ font_scale: value }, { debounce: true });
  }

  function updateSliderFill(slider) {
    var min = Number(slider.min) || 0;
    var max = Number(slider.max) || 100;
    var value = Number(slider.value) || 0;
    var percent = ((value - min) / Math.max(1, max - min)) * 100;
    slider.style.setProperty('--fill', percent.toFixed(2) + '%');
  }

  function toggleSwitch(button, setter) {
    button.addEventListener('click', function () {
      setter(button.getAttribute('aria-checked') !== 'true');
    });
  }

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

  
  function toggleSquareBg() {
    var enabled = !el.body.classList.contains('square-art-bg');
    el.body.classList.toggle('square-art-bg', enabled);
    try {
      localStorage.setItem('lyriq_square_art_bg', enabled ? '1' : '0');
    } catch (e) {}
    showToast(enabled ? 'Square background: Album artwork' : 'Square background: Solid dark', { icon: 'disc' });
  }

  try {
    if (localStorage.getItem('lyriq_square_art_bg') === '1') {
      el.body.classList.add('square-art-bg');
    }
  } catch (e) {}

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
      if (activeEl && el.lyricsViewport) {
        var cRect = el.lyricsViewport.getBoundingClientRect();
        var lRect = activeEl.getBoundingClientRect();
        var offset = lRect.top - cRect.top + el.lyricsViewport.scrollTop;
        el.lyricsViewport.scrollTop = Math.max(0, offset - (cRect.height * 0.44));
        if (window.scrollY !== 0) window.scrollTo(0, 0);
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

  window.openSettings = openSettings;
  window.closeSettings = closeSettings;

  function wireSettingsIntegrations() {
    var btnGithubRepo = $('btnGithubRepo');
    if (btnGithubRepo) {
      btnGithubRepo.addEventListener('click', function (e) {
        e.preventDefault();
        callApi('open_external_url', 'https://github.com/Kingof3O/Lyriq');
      });
    }
    var btnCheckUpdates = $('btnCheckUpdates');
    var updateStatusText = $('updateStatusText');
    if (btnCheckUpdates) {
      btnCheckUpdates.addEventListener('click', function () {
        if (updateStatusText) updateStatusText.textContent = 'Checking GitHub for updates…';
        fetch('https://api.github.com/repos/Kingof3O/Lyriq/releases/latest', { cache: 'no-store' })
          .then(function (r) { if (!r.ok) throw new Error('Status ' + r.status); return r.json(); })
          .then(function (data) {
            var tag = (data && data.tag_name) || '';
            if (tag && tag !== 'v3.0.0' && tag !== '3.0.0') {
              if (updateStatusText) updateStatusText.innerHTML = '<span style="color:#C4B5FD">Update available: <b>' + escapeHtml(tag) + '</b>.</span> <a href="' + (data.html_url || 'https://github.com/Kingof3O/Lyriq/releases') + '" target="_blank" style="color:var(--brand);text-decoration:underline;">Download</a>';
              showToast('Update available: ' + tag, { icon: 'download' });
            } else {
              if (updateStatusText) updateStatusText.textContent = 'Lyriq v3.0.0 is up to date.';
              showToast('Lyriq is up to date', { icon: 'check' });
            }
          })
          .catch(function () {
            if (updateStatusText) updateStatusText.textContent = 'Lyriq v3.0.0 · Up to date (offline)';
            showToast('Checked: running latest build v3.0.0', { icon: 'check' });
          });
      });
    }
    if (el.btnSaveSpotifyToken) {
      el.btnSaveSpotifyToken.addEventListener('click', function () {
        var token = (el.inputSpotifyToken && el.inputSpotifyToken.value.trim()) || '';
        callApi('set_spotify_token', token).then(function () {
          showToast('Spotify token saved', { icon: 'check' });
        });
      });
    }
    if (el.btnOpenSpotifyDev) {
      el.btnOpenSpotifyDev.addEventListener('click', function () {
        callApi('open_external_url', 'https://developer.spotify.com/dashboard');
      });
    }
    if (el.inputDiscordClientId) {
      el.inputDiscordClientId.addEventListener('change', function () {
        var cid = el.inputDiscordClientId.value.trim();
        callApi('set_discord_client_id', cid).then(function () {
          showToast('Discord client ID updated', { icon: 'check' });
        });
      });
    }
  }

  wireSettingsIntegrations();
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

  // ---------------------------------------------------------------------------
  // Startup with Windows (optional backend support)
  // ---------------------------------------------------------------------------

  function refreshStartupState() {
    var startupSupported = hasApi('set_start_with_windows') || hasApi('get_startup_state');
    if (!startupSupported) {
      el.checkStartup.setAttribute('aria-checked', 'false');
      el.checkStartup.setAttribute('aria-disabled', 'true');
      el.startupHelp.textContent = 'Not available in this build yet.';
      return;
    }
    el.checkStartup.removeAttribute('aria-disabled');
    el.startupHelp.textContent = 'Launch the companion at sign-in.';
    if (!hasApi('get_startup_state')) return;
    callApi('get_startup_state').then(function (result) {
      var enabled = typeof result === 'boolean' ? result : !!(result && (result.enabled || result.start_with_windows));
      el.checkStartup.setAttribute('aria-checked', String(enabled));
    });
  }

  function toggleStartup() {
    var next = el.checkStartup.getAttribute('aria-checked') !== 'true';
    if (!hasApi('set_start_with_windows')) {
      showToast('Start with Windows is not available in this build.', { icon: 'window', tone: 'danger' });
      return;
    }
    var done = function (ok) {
      if (ok === false) {
        showToast('Windows rejected the startup change.', { icon: 'alert', tone: 'danger' });
        el.checkStartup.setAttribute('aria-checked', String(!next));
        return;
      }
      el.checkStartup.setAttribute('aria-checked', String(next));
      showToast(next ? 'Will start with Windows' : 'Will not start with Windows', { icon: 'window' });
    };
    try {
      var result = getApi().set_start_with_windows(next);
      if (result && typeof result.then === 'function') result.then(done).catch(function () { done(false); });
      else done(result);
    } catch (err) {
      done(false);
    }
  }

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

  // ---------------------------------------------------------------------------
  // Tooltip positioning (fixed coordinates, never clipped)
  // ---------------------------------------------------------------------------

  function positionTooltip(target) {
    if (!target) return;
    var rect = target.getBoundingClientRect();
    if (!rect.width && !rect.height) return;
    var x = clamp(rect.left + rect.width / 2, 136, Math.max(136, window.innerWidth - 136));
    var y = rect.bottom + 8;
    var above = y + 38 > window.innerHeight && rect.top > 44;
    if (above) {
      y = rect.top - 8;
      target.classList.add('tip-above');
    } else {
      target.classList.remove('tip-above');
    }
    target.style.setProperty('--tip-x', x + 'px');
    target.style.setProperty('--tip-y', y + 'px');
  }

  document.addEventListener('pointerover', function (event) {
    var target = event.target.closest && event.target.closest('[data-tooltip]');
    if (target) positionTooltip(target);
  });
  document.addEventListener('focusin', function (event) {
    var target = event.target.closest && event.target.closest('[data-tooltip]');
    if (target) positionTooltip(target);
  });

  // ---------------------------------------------------------------------------
  // Interaction wiring
  // ---------------------------------------------------------------------------

  function wireButtonActions() {
    // Playback
    el.btnPlayPause.addEventListener('click', function () { callApi('play_pause'); });
    el.btnMiniPlay.addEventListener('click', function () { callApi('play_pause'); });
    el.btnSquarePlay && el.btnSquarePlay.addEventListener('click', function () { callApi('play_pause'); });
    el.btnPrev.addEventListener('click', function () { callApi('prev_track'); });
    el.btnSquarePrev && el.btnSquarePrev.addEventListener('click', function () { callApi('prev_track'); });
    el.btnNext.addEventListener('click', function () { callApi('next_track'); });
    el.btnMiniNext.addEventListener('click', function () { callApi('next_track'); });
    el.btnSquareNext && el.btnSquareNext.addEventListener('click', function () { callApi('next_track'); });
    el.btnHeart.addEventListener('click', toggleFavorite);
    el.btnMiniOpen.addEventListener('click', function () { setMiniMode(false, { announce: true }); });
    el.btnMiniSquare && el.btnMiniSquare.addEventListener('click', function () { setMiniMode(false, { persist: false, backend: false }); setSquareMode(true, { announce: true }); });
    el.btnMiniLyrics.addEventListener('click', function () { setMiniExpanded(!AppState.isMiniExpanded); });
    el.btnMiniPin.addEventListener('click', function () { setPinned(!AppState.pinned, { announce: true }); });
    el.btnMiniClose.addEventListener('click', function () { callApi('close'); });

    // Square mode controls
    el.btnSquare && el.btnSquare.addEventListener('click', function () { setSquareMode(!AppState.isSquare, { announce: true }); });
    el.btnSquareExpand && el.btnSquareExpand.addEventListener('click', function () { setSquareMode(false, { announce: true }); });
    el.btnSquareClose && el.btnSquareClose.addEventListener('click', function () { callApi('close'); });
    el.btnSquarePin && el.btnSquarePin.addEventListener('click', function () { setPinned(!AppState.pinned, { announce: true }); });
    el.btnSquareViewMode && el.btnSquareViewMode.addEventListener('click', cycleViewMode);
    el.btnSquareToMini && el.btnSquareToMini.addEventListener('click', function () { setSquareMode(false, { persist: false, backend: false }); setMiniMode(true, { announce: true }); });
    el.btnSquareToCard && el.btnSquareToCard.addEventListener('click', function () { setSquareMode(false, { announce: true }); });

    // Volume wheel: album art and dock, discoverable via the volume button.
    el.npArtWrap.addEventListener('wheel', handleWheelVolume, { passive: false });
    el.miniArtWrap.addEventListener('wheel', handleWheelVolume, { passive: false });
    el.playerDock.addEventListener('wheel', handleWheelVolume, { passive: false });
    el.btnVolume.addEventListener('click', function () {
      showToast('Scroll over the album art or player to change Windows volume.', { icon: 'volume', duration: 4200 });
    });

    // Window controls
    el.btnMin.addEventListener('click', function () { callApi('minimize'); });
    el.btnClose.addEventListener('click', function () { callApi('close'); });
    el.btnMini.addEventListener('click', function () { setMiniMode(true, { announce: true }); });
    el.btnFullscreen.addEventListener('click', function () { setFullscreen(!AppState.isFullscreen, { announce: true }); });
    el.btnSettings.addEventListener('click', function () { openSettings('appearance'); });
    el.btnOverflow.addEventListener('click', function (event) {
      event.stopPropagation();
      toggleOverflow();
    });
    el.btnSettingsClose.addEventListener('click', closeSettings);
    el.settingsOverlay.addEventListener('click', function (event) {
      if (event.target === el.settingsOverlay) closeSettings();
    });
    el.btnOffsetChip.addEventListener('click', function () { openSettings('lyrics'); });
    el.btnViewMode.addEventListener('click', cycleViewMode);

    // Settings sheet tabs
    Array.prototype.forEach.call(document.querySelectorAll('.sheet-tab'), function (tab) {
      tab.addEventListener('click', function () { setSettingsTab(tab.dataset.tab); });
      tab.addEventListener('keydown', function (event) {
        var tabs = Array.prototype.slice.call(document.querySelectorAll('.sheet-tab'));
        var index = tabs.indexOf(tab);
        if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
          event.preventDefault();
          var next = tabs[(index + (event.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length];
          setSettingsTab(next.dataset.tab);
          next.focus();
        }
      });
    });

    // Theme and lyrics view segmented controls
    Array.prototype.forEach.call(el.themeGroup.querySelectorAll('[data-theme-choice]'), function (button) {
      button.addEventListener('click', function () { applyTheme(button.dataset.themeChoice); });
    });
    Array.prototype.forEach.call(el.viewModeGroup.querySelectorAll('[data-lyrics-mode]'), function (button) {
      button.addEventListener('click', function () { setLyricsViewMode(button.dataset.lyricsMode, { announce: true }); });
    });

    // Switches
    toggleSwitch(el.checkLowPower, function (enabled) { setLowPower(enabled, { announce: true }); });
    toggleSwitch(el.checkRomaji, function (enabled) { setRomanization(enabled); });
    toggleSwitch(el.checkSweep, function (enabled) { setSweep(enabled); });
    toggleSwitch(el.checkLearner, function (enabled) { setWordLookup(enabled); });
    toggleSwitch(el.checkDiscord, function (enabled) { setDiscord(enabled, { announce: true }); });
    toggleSwitch(el.checkPin, function (enabled) { setPinned(enabled, { announce: true }); });
    toggleSwitch(el.checkGhost, function (enabled) { setGhostMode(enabled, { announce: true }); });
    toggleSwitch(el.checkStartup, toggleStartup);

    // Slider and offset
    el.sliderFontScale.addEventListener('input', function () { setFontScale(Number(el.sliderFontScale.value) / 100); });
    el.sliderFontScale.addEventListener('mousedown', function (e) { e.stopPropagation(); });
    el.sliderFontScale.addEventListener('pointerdown', function (e) { e.stopPropagation(); });
    el.btnNudgeMinus.addEventListener('click', function () { nudgeOffset(-0.2); });
    el.btnNudgePlus.addEventListener('click', function () { nudgeOffset(0.2); });
    el.btnNudgeReset.addEventListener('click', resetOffset);

    // Sleep timer badge
    el.sleepTimerBadge.addEventListener('click', promptSleepTimerCancel);
    el.sleepTimerBadge.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        promptSleepTimerCancel();
      }
    });

    // Overflow menu
    el.menuSearchLyrics.addEventListener('click', function () { closeOverflow(); openSearchModal(); });
    el.menuPalette.addEventListener('click', function () { closeOverflow(); openPalette(); });
    el.menuPin.addEventListener('click', function () { setPinned(!AppState.pinned, { announce: true }); syncMenuChecks(); });
    el.menuGhost.addEventListener('click', function () { setGhostMode(!AppState.ghost, { announce: true }); syncMenuChecks(); });
    el.menuLowPower.addEventListener('click', function () { setLowPower(!AppState.lowPower, { announce: true }); syncMenuChecks(); });
    el.menuDiscord.addEventListener('click', function () { setDiscord(!AppState.discord, { announce: true }); syncMenuChecks(); });
    el.btnSplitLayout.addEventListener('click', function () { setSplit(!AppState.isSplit, { announce: true }); syncMenuChecks(); });
    el.menuHistory.addEventListener('click', function () { closeOverflow(); openHistory(); });
    el.menuVocab.addEventListener('click', function () { closeOverflow(); openVocab(''); });
    el.menuExportLrc.addEventListener('click', function () { closeOverflow(); exportLrc(); });
    el.menuExportSrt.addEventListener('click', function () { closeOverflow(); exportSrt(); });
    el.menuExportSheet.addEventListener('click', function () { closeOverflow(); exportPoster(); });
    el.menuOpenLrc.addEventListener('click', function () { closeOverflow(); openLrcFolder(); });

    // Data actions
    el.btnRefreshCache.addEventListener('click', refreshCacheStats);
    el.btnClearCache.addEventListener('click', confirmClearCache);
    el.btnOpenLrcFolder.addEventListener('click', openLrcFolder);
    el.btnSettingsSearchLyrics.addEventListener('click', openSearchModal);
    el.btnSettingsHistory.addEventListener('click', openHistory);
    el.btnSettingsVocab.addEventListener('click', function () { openVocab(''); });
    el.btnExportLrc.addEventListener('click', exportLrc);
    el.btnExportSrt.addEventListener('click', exportSrt);
    el.btnExportSheet.addEventListener('click', exportPoster);
    el.btnCopyLine.addEventListener('click', copyCurrentLine);
    el.btnCopyAll.addEventListener('click', copyAllLyrics);
    el.searchFolderPath.addEventListener('click', openLrcFolder);

    
    if (el.btnSquareBgToggle) el.btnSquareBgToggle.addEventListener('click', toggleSquareBg);
    if (el.btnLikedOpen) el.btnLikedOpen.addEventListener('click', function () { openHistory('liked'); });
    if (el.btnQueueOpen) el.btnQueueOpen.addEventListener('click', openQueue);
    if (el.btnHistoryAll) el.btnHistoryAll.addEventListener('click', function () { currentHistoryFilter = 'all'; updateHistoryFilterUi(); renderHistory(); });
    if (el.btnHistoryLiked) el.btnHistoryLiked.addEventListener('click', function () { currentHistoryFilter = 'liked'; updateHistoryFilterUi(); renderHistory(); });

    // History and vocabulary
    el.btnHistoryClose.addEventListener('click', closeHistory);
    el.historySearch.addEventListener('input', debounce(renderHistory, 120));
    el.historyModal.addEventListener('click', function (event) {
      if (event.target === el.historyModal) closeHistory();
    });
    el.btnVocabClose.addEventListener('click', closeVocab);
  }
  // ---------------------------------------------------------------------------
  // Interaction wiring: scrubber bar
  // ---------------------------------------------------------------------------

  function wireScrubber() {
    var scrubValue = 0;
    var scrubbing = false;
    function scrubFromEvent(event) {
      if (AppState.duration <= 0) return 0;
      var rect = el.scrubTrack.getBoundingClientRect();
      var ratio = clamp((event.clientX - rect.left) / Math.max(1, rect.width), 0, 1);
      scrubValue = ratio * AppState.duration;
      renderPosition(scrubValue);
      return scrubValue;
    }
    el.scrubTrack.addEventListener('pointerdown', function (event) {
      if (AppState.duration <= 0) return;
      scrubbing = true;
      AppState.isScrubbing = true;
      stopFrame();
      el.scrubTrack.setPointerCapture && el.scrubTrack.setPointerCapture(event.pointerId);
      scrubFromEvent(event);
    });
    el.scrubTrack.addEventListener('pointermove', function (event) {
      if (!scrubbing) return;
      scrubFromEvent(event);
    });
    el.scrubTrack.addEventListener('pointerup', function (event) {
      if (!scrubbing) return;
      scrubbing = false;
      AppState.isScrubbing = false;
      scrubFromEvent(event);
      seekTo(scrubValue, true);
      if (AppState.isPlaying) ensureFrame();
    });
    el.scrubTrack.addEventListener('pointercancel', function () {
      scrubbing = false;
      AppState.isScrubbing = false;
      if (AppState.isPlaying) ensureFrame();
    });
    el.scrubTrack.addEventListener('keydown', function (event) {
      if (AppState.duration <= 0) return;
      var position = currentPositionSeconds();
      if (event.key === 'ArrowRight' || event.key === 'ArrowUp') {
        event.preventDefault();
        seekTo(position + 5, true);
      } else if (event.key === 'ArrowLeft' || event.key === 'ArrowDown') {
        event.preventDefault();
        seekTo(position - 5, true);
      } else if (event.key === 'Home') {
        event.preventDefault();
        seekTo(0, true);
      } else if (event.key === 'End') {
        event.preventDefault();
        seekTo(AppState.duration, true);
      }
    });

    if (el.squareScrubTrack) {
      function scrubFromSquare(e) {
        if (AppState.duration <= 0) return 0;
        var r = el.squareScrubTrack.getBoundingClientRect();
        var ratio = clamp((e.clientX - r.left) / Math.max(1, r.width), 0, 1);
        scrubValue = ratio * AppState.duration;
        renderPosition(scrubValue);
        return scrubValue;
      }
      el.squareScrubTrack.addEventListener('pointerdown', function (e) {
        if (AppState.duration <= 0) return;
        scrubbing = true;
        AppState.isScrubbing = true;
        stopFrame();
        el.squareScrubTrack.setPointerCapture && el.squareScrubTrack.setPointerCapture(e.pointerId);
        scrubFromSquare(e);
      });
      el.squareScrubTrack.addEventListener('pointermove', function (e) {
        if (!scrubbing) return;
        scrubFromSquare(e);
      });
      el.squareScrubTrack.addEventListener('pointerup', function (e) {
        if (!scrubbing) return;
        scrubbing = false;
        AppState.isScrubbing = false;
        scrubFromSquare(e);
        seekTo(scrubValue, true);
        if (AppState.isPlaying) ensureFrame();
      });
      el.squareScrubTrack.addEventListener('pointercancel', function () {
        scrubbing = false;
        AppState.isScrubbing = false;
        if (AppState.isPlaying) ensureFrame();
      });
    }
  }
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

        if (el.sliderVolume) {
      el.sliderVolume.addEventListener('input', function () {
        var val = Number(el.sliderVolume.value);
        if (el.volumeLabel) el.volumeLabel.textContent = val + '%';
        updateSliderFill(el.sliderVolume);
        callApi('set_volume', val);
      });
      callApi('get_volume').then(function (res) {
        if (res && typeof res.volume === 'number') {
          updateVolumeUi(res.volume);
        }
      });
    }
    initMiniResize();
    initSquareResize();
  }

  function updateVolumeUi(volume) {
    if (typeof volume !== 'number') return;
    if (el.sliderVolume) {
      el.sliderVolume.value = String(volume);
      updateSliderFill(el.sliderVolume);
    }
    if (el.volumeLabel) el.volumeLabel.textContent = volume + '%';
  }

  function handleWheelVolume(event) {
    event.preventDefault();
    var delta = event.deltaY < 0 ? 1 : -1;
    callApi('adjust_volume', delta).then(function (res) {
      if (res && res.target === 'spotify' && typeof res.volume === 'number') {
        updateVolumeUi(res.volume);
        showToast('Spotify ' + res.volume + '%', { icon: 'volume', duration: 1200 });
      } else {
        showToast(delta > 0 ? 'Volume up' : 'Volume down', { icon: 'volume', duration: 1200 });
      }
    }).catch(function () {
      showToast(delta > 0 ? 'Volume up' : 'Volume down', { icon: 'volume', duration: 1200 });
    });
  }

  function wireEvents() {
    wireButtonActions();
    wireScrubber();
    wireShortcuts();
  }
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
})();
