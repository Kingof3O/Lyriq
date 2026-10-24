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

