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
