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

