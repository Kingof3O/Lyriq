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

  function studyContextLine() {
    if (contextLineIndex < 0) { closeLineContext(); return; }
    var line = AppState.lyrics[contextLineIndex];
    closeLineContext();
    if (!line) return;
    triggerWordLookup(line.original, window.innerWidth / 2, 200, line.original, line.translation);
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

  function wireContextMenuActions() {
    if (el.ctxStudy) el.ctxStudy.addEventListener('click', studyContextLine);
    if (el.ctxCopy) el.ctxCopy.addEventListener('click', copyContextLine);
    if (el.ctxEdit) el.ctxEdit.addEventListener('click', editContextLine);
  }
