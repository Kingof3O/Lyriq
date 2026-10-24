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

