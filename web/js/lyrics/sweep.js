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

