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

