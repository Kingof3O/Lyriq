  // ---------------------------------------------------------------------------
  // Dictionary lookup
  // ---------------------------------------------------------------------------

  var dictState = {
    word: '',
    romaji: '',
    meaning: '',
    language: 'unknown',
    x: 0,
    y: 0
  };

  function triggerWordLookup(word, clientX, clientY) {
    if (!AppState.wordLookup) return;
    var value = String(word || '').trim();
    if (!value) return;
    dictState.word = value;
    dictState.romaji = '';
    dictState.meaning = '';
    dictState.language = AppState.language;
    dictState.x = clientX;
    dictState.y = clientY;

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

    if (!hasApi('lookup_word')) {
      el.dictMeaning.textContent = 'Word lookup is unavailable in this build.';
      return;
    }
    callApi('lookup_word', value).then(function (result) {
      if (!result) {
        el.dictMeaning.textContent = 'No definition found.';
        return;
      }
      el.dictWord.textContent = result.word || value;
      dictState.romaji = result.romaji || '';
      dictState.meaning = result.trans || 'No definition found.';
      dictState.language = result.lang || AppState.language;
      el.dictRomaji.textContent = dictState.romaji;
      el.dictMeaning.textContent = dictState.meaning;
      el.dictLang.textContent = 'Language: ' + String(dictState.language).toUpperCase();
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

