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

