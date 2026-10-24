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

