// State
let currentLyrics = [];
let activeIndex = -1;
let currentDuration = 0;
let basePosition = 0;
let baseTimestamp = 0;
let lastRenderedPosition = 0;
let syncOffset = 0.0;
let userScrolledRecently = false;
let userScrollTimeout = null;
let isPinned = false;
let isMiniMode = false;
let isMiniExpanded = false;
let isFullscreen = false;
let isSplitLayout = false;
let isPlaying = false;
let isFavorite = false;
let currentSongTitle = "";
let currentSongArtist = "";
let currentSongThumbnail = "";
let dominantLanguage = "unknown";
let enableSweep = true;

// Word Dictionary State
let currentDictWord = "";
let currentDictRomaji = "";
let currentDictMeaning = "";
let currentDictLang = "unknown";

// Sleep Timer State
let sleepTimerEnd = 0;
let sleepTimerTicker = null;

// View Modes: 'both' (Dual), 'trans-only' (English Only), 'orig-only' (Original Only)
const viewModes = ['both', 'trans-only', 'orig-only'];
let viewModeIndex = 0;

// Language Flags Mapping
const LANG_FLAGS = {
  'ko': '🇰🇷 KO',
  'ja': '🇯🇵 JA',
  'zh': '🇨🇳 ZH',
  'zh-cn': '🇨🇳 ZH',
  'es': '🇪🇸 ES',
  'fr': '🇫🇷 FR',
  'de': '🇩🇪 DE',
  'ar': '🇸🇦 AR',
  'pt': '🇧🇷 PT',
  'ru': '🇷🇺 RU',
  'en': '🇺🇸 EN',
  'it': '🇮🇹 IT'
};

// Toast Timer
let toastTimeout = null;

// DOM Elements
const elTrackCard = document.getElementById('trackCard');
const elTrackTitle = document.getElementById('trackTitle');
const elTrackArtist = document.getElementById('trackArtist');
const elTrackArtwork = document.getElementById('trackArtwork');
const elTrackDisc = document.getElementById('trackDisc');
const btnHeart = document.getElementById('btnHeart');
const elLyricsList = document.getElementById('lyricsList');
const elLyricsViewport = document.getElementById('lyricsViewport');
const elIdleState = document.getElementById('idleState');
const elNoLyricsState = document.getElementById('noLyricsState');
const elCurrentTime = document.getElementById('currentTime');
const elTotalTime = document.getElementById('totalTime');
const elScrubFill = document.getElementById('scrubFill');
const elScrubTrack = document.getElementById('scrubTrack');
const elFlagBadge = document.getElementById('flagBadge');
const elGhostBadge = document.getElementById('ghostBadge');
const elSleepTimerBadge = document.getElementById('sleepTimerBadge');
const elInstrumentalPill = document.getElementById('instrumentalPill');
const elInstrumentalText = document.getElementById('instrumentalText');
const elToastPill = document.getElementById('toastPill');
const elToastMsg = document.getElementById('toastMsg');
const elPlayerDock = document.getElementById('playerDock');

// Mode 2: Island Elements
const elIslandArtwork = document.getElementById('islandArtwork');
const elIslandDisc = document.getElementById('islandDisc');
const elIslandOriginal = document.getElementById('islandOriginal');
const elIslandRomaji = document.getElementById('islandRomaji');
const elIslandTranslation = document.getElementById('islandTranslation');
const elIslandSingleLine = document.getElementById('islandSingleLine');
const elIslandHeaderInfo = document.getElementById('islandHeaderInfo');
const elIslandSongTitle = document.getElementById('islandSongTitle');
const elIslandSongArtist = document.getElementById('islandSongArtist');
const elIslandDrawer = document.getElementById('islandDrawer');
const elIslandLyricsScroll = document.getElementById('islandLyricsScroll');
const btnIslandPlay = document.getElementById('btnIslandPlay');
const btnIslandNext = document.getElementById('btnIslandNext');
const btnIslandFold = document.getElementById('btnIslandFold');
const btnIslandExpand = document.getElementById('btnIslandExpand');
const iconUnfold = document.querySelector('.icon-unfold');
const iconFold = document.querySelector('.icon-fold');

// Settings Drawer Elements
const settingsDrawer = document.getElementById('settingsDrawer');
const btnToolsToggle = document.getElementById('btnToolsToggle');
const btnToolsClose = document.getElementById('btnToolsClose');
const selectTheme = document.getElementById('selectTheme');
const selectLang = document.getElementById('selectLang');
const sliderOpacity = document.getElementById('sliderOpacity');
const opacityVal = document.getElementById('opacityVal');
const btnNudgeMinus = document.getElementById('btnNudgeMinus');
const btnNudgePlus = document.getElementById('btnNudgePlus');
const btnNudgeReset = document.getElementById('btnNudgeReset');
const nudgeOffsetVal = document.getElementById('nudgeOffsetVal');
const checkSweep = document.getElementById('checkSweep');
const checkRomaji = document.getElementById('checkRomaji');
const checkLearner = document.getElementById('checkLearner');
const checkDiscord = document.getElementById('checkDiscord');
const checkGhost = document.getElementById('checkGhost');
const selectSleep = document.getElementById('selectSleep');
const btnCopyLine = document.getElementById('btnCopyLine');
const btnCopyAll = document.getElementById('btnCopyAll');
const btnExportLrc = document.getElementById('btnExportLrc');
const btnExportSrt = document.getElementById('btnExportSrt');
const btnExportSheet = document.getElementById('btnExportSheet');

// Modals
const historyModal = document.getElementById('historyModal');
const btnHistoryOpen = document.getElementById('btnHistoryOpen');
const btnHistoryClose = document.getElementById('btnHistoryClose');
const historyList = document.getElementById('historyList');

const vocabModal = document.getElementById('vocabModal');
const btnVocabOpen = document.getElementById('btnVocabOpen');
const btnVocabClose = document.getElementById('btnVocabClose');
const vocabList = document.getElementById('vocabList');
const btnExportVocab = document.getElementById('btnExportVocab');

// Dictionary Modal Elements
const dictCard = document.getElementById('dictCard');
const dictWord = document.getElementById('dictWord');
const dictRomaji = document.getElementById('dictRomaji');
const dictMeaning = document.getElementById('dictMeaning');
const dictLang = document.getElementById('dictLang');
const btnDictSpeak = document.getElementById('btnDictSpeak');
const btnDictSave = document.getElementById('btnDictSave');
const btnDictCopy = document.getElementById('btnDictCopy');
const btnDictClose = document.getElementById('btnDictClose');

// Canvas Spectrum
const canvasSpectrum = document.getElementById('audioSpectrum');
let ctxSpectrum = canvasSpectrum ? canvasSpectrum.getContext('2d') : null;
let spectrumAnimId = null;

// Icons & Buttons
const iconPlay = document.querySelector('.icon-play');
const iconPause = document.querySelector('.icon-pause');
const islandIconPlay = document.querySelector('.island-icon-play');
const islandIconPause = document.querySelector('.island-icon-pause');

const btnPin = document.getElementById('btnPin');
const btnMini = document.getElementById('btnMini');
const btnFullscreen = document.getElementById('btnFullscreen');
const btnSplitLayout = document.getElementById('btnSplitLayout');
const btnViewMode = document.getElementById('btnViewMode');
const viewModeText = document.getElementById('viewModeText');
const btnMin = document.getElementById('btnMin');
const btnClose = document.getElementById('btnClose');
const btnRetry = document.getElementById('btnRetry');
const btnPlayPause = document.getElementById('btnPlayPause');
const btnPrev = document.getElementById('btnPrev');
const btnNext = document.getElementById('btnNext');

// Toast Notification Helper
function showToast(msg) {
  if (!elToastPill) return;
  elToastMsg.textContent = msg;
  elToastPill.style.display = 'block';
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => {
    elToastPill.style.display = 'none';
  }, 2200);
}

// Format Seconds to m:ss
function formatTime(seconds) {
  if (isNaN(seconds) || seconds < 0) return "0:00";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

// Format Seconds to 00:00:00,000 for SRT Subtitles
function formatSrtTime(seconds) {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 1000);
  return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')},${String(ms).padStart(3, '0')}`;
}

// User scroll detection
elLyricsViewport.addEventListener('wheel', () => {
  userScrolledRecently = true;
  clearTimeout(userScrollTimeout);
  userScrollTimeout = setTimeout(() => {
    userScrolledRecently = false;
  }, 3000);
});

// Interactive Scrubber
let isScrubbing = false;

function handleScrub(e) {
  if (currentDuration <= 0) return;
  const rect = elScrubTrack.getBoundingClientRect();
  const clickX = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
  const pct = clickX / rect.width;
  const targetSeconds = pct * currentDuration;
  
  elScrubFill.style.width = `${pct * 100}%`;
  elCurrentTime.textContent = formatTime(targetSeconds);

  basePosition = targetSeconds;
  baseTimestamp = Date.now();
  window.updatePosition(targetSeconds, true);

  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.seek(targetSeconds);
  }
}

elScrubTrack.addEventListener('mousedown', (e) => {
  isScrubbing = true;
  handleScrub(e);
});

window.addEventListener('mousemove', (e) => {
  if (isScrubbing) handleScrub(e);
});

window.addEventListener('mouseup', () => {
  isScrubbing = false;
});

// Mouse Wheel Volume Control on Track Card & Player Dock
function handleWheelVolume(e) {
  e.preventDefault();
  const delta = e.deltaY < 0 ? 1 : -1;
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.adjust_volume(delta);
    showToast(delta > 0 ? "🔊 Volume: Up" : "🔉 Volume: Down");
  }
}

if (elTrackCard) elTrackCard.addEventListener('wheel', handleWheelVolume);
if (elPlayerDock) elPlayerDock.addEventListener('wheel', handleWheelVolume);

// Heart Favorite Button
btnHeart.addEventListener('click', () => {
  if (!currentSongArtist || !currentSongTitle) return;
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.toggle_favorite(currentSongArtist, currentSongTitle).then((fav) => {
      isFavorite = fav;
      btnHeart.textContent = fav ? "♥" : "♡";
      btnHeart.classList.toggle('active', fav);
      showToast(fav ? "❤️ Added to Favorites!" : "Removed from Favorites");
    });
  }
});

// Media Control Buttons
btnPlayPause.addEventListener('click', () => {
  if (window.pywebview && window.pywebview.api) window.pywebview.api.play_pause();
});

btnIslandPlay.addEventListener('click', () => {
  if (window.pywebview && window.pywebview.api) window.pywebview.api.play_pause();
});

btnPrev.addEventListener('click', () => {
  if (window.pywebview && window.pywebview.api) window.pywebview.api.prev_track();
});

btnNext.addEventListener('click', () => {
  if (window.pywebview && window.pywebview.api) window.pywebview.api.next_track();
});

btnIslandNext.addEventListener('click', () => {
  if (window.pywebview && window.pywebview.api) window.pywebview.api.next_track();
});

// Window Mode Controls
btnPin.addEventListener('click', () => {
  isPinned = !isPinned;
  btnPin.classList.toggle('active', isPinned);
  if (window.pywebview && window.pywebview.api) window.pywebview.api.toggle_pin(isPinned);
});

btnMini.addEventListener('click', () => {
  setMiniMode(true);
});

function setMiniMode(mini) {
  isMiniMode = mini;
  if (mini) {
    document.body.classList.remove('mode-fullscreen');
    document.body.classList.add('mode-mini');
  } else {
    document.body.classList.remove('mode-mini');
    isMiniExpanded = false;
    elIslandDrawer.style.display = 'none';
    elIslandSingleLine.style.display = 'flex';
    elIslandHeaderInfo.style.display = 'none';
    iconUnfold.style.display = 'block';
    iconFold.style.display = 'none';
  }
  if (window.pywebview && window.pywebview.api) window.pywebview.api.toggle_mini_mode(mini);
}

// Global Hotkey Hook: Toggle Mini Island
window.toggleMiniModeHotKey = function() {
  setMiniMode(!isMiniMode);
  showToast(isMiniMode ? "Mini Island Overlay Enabled" : "Standard Window Mode");
};

btnIslandFold.addEventListener('click', () => {
  isMiniExpanded = !isMiniExpanded;
  if (isMiniExpanded) {
    elIslandDrawer.style.display = 'block';
    elIslandSingleLine.style.display = 'none';
    elIslandHeaderInfo.style.display = 'flex';
    iconUnfold.style.display = 'none';
    iconFold.style.display = 'block';
    if (window.pywebview && window.pywebview.api) window.pywebview.api.toggle_mini_expand(true);
    if (activeIndex >= 0) {
      const activeItem = document.getElementById(`mini-line-${activeIndex}`);
      if (activeItem) activeItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  } else {
    elIslandDrawer.style.display = 'none';
    elIslandSingleLine.style.display = 'flex';
    elIslandHeaderInfo.style.display = 'none';
    iconUnfold.style.display = 'block';
    iconFold.style.display = 'none';
    if (window.pywebview && window.pywebview.api) window.pywebview.api.toggle_mini_expand(false);
  }
});

btnIslandExpand.addEventListener('click', () => {
  setMiniMode(false);
});

btnFullscreen.addEventListener('click', () => toggleFullscreen());

btnSplitLayout.addEventListener('click', () => {
  isSplitLayout = !isSplitLayout;
  document.body.classList.toggle('layout-split', isSplitLayout);
  btnSplitLayout.classList.toggle('active', isSplitLayout);
  showToast(isSplitLayout ? "Split View Fullscreen" : "Centered View Fullscreen");
});

function toggleFullscreen() {
  isFullscreen = !isFullscreen;
  document.body.classList.toggle('mode-fullscreen', isFullscreen);
  btnFullscreen.classList.toggle('active', isFullscreen);
  btnSplitLayout.style.display = isFullscreen ? 'inline-flex' : 'none';
  if (window.pywebview && window.pywebview.api) window.pywebview.api.toggle_fullscreen();
}

window.addEventListener('keydown', (e) => {
  if (e.key === 'F11') {
    e.preventDefault();
    toggleFullscreen();
  } else if (e.key === 'Escape') {
    if (isFullscreen) toggleFullscreen();
    if (settingsDrawer.style.display === 'flex') settingsDrawer.style.display = 'none';
    if (dictCard.style.display === 'flex') dictCard.style.display = 'none';
    if (historyModal.style.display === 'flex') historyModal.style.display = 'none';
    if (vocabModal.style.display === 'flex') vocabModal.style.display = 'none';
  }
});

// 3-Way Lyrics View Switcher
function cycleViewMode() {
  viewModeIndex = (viewModeIndex + 1) % viewModes.length;
  const currentMode = viewModes[viewModeIndex];

  document.body.classList.remove('view-both', 'view-trans-only', 'view-orig-only');
  document.body.classList.add(`view-${currentMode}`);

  if (currentMode === 'both') {
    viewModeText.textContent = 'DUAL';
    showToast("Mode: Dual (Original + Translation)");
  } else if (currentMode === 'trans-only') {
    viewModeText.textContent = 'TRANS ONLY';
    showToast("Mode: Translation Only");
  } else if (currentMode === 'orig-only') {
    viewModeText.textContent = 'ORIG ONLY';
    showToast("Mode: Original Foreign Lyrics Only");
  }
}

btnViewMode.addEventListener('click', cycleViewMode);
window.cycleViewMode = cycleViewMode; // Expose to global hotkey Ctrl+Shift+L

// Settings & Tools Drawer
btnToolsToggle.addEventListener('click', () => {
  const isHidden = (settingsDrawer.style.display === 'none' || !settingsDrawer.style.display);
  settingsDrawer.style.display = isHidden ? 'flex' : 'none';
});

btnToolsClose.addEventListener('click', () => {
  settingsDrawer.style.display = 'none';
});

// Theme Selector
selectTheme.addEventListener('change', (e) => {
  const theme = e.target.value;
  document.body.dataset.theme = theme;
  localStorage.setItem('lyrics_theme', theme);
  showToast(`Theme: ${e.target.options[e.target.selectedIndex].text}`);
});

const savedTheme = localStorage.getItem('lyrics_theme');
if (savedTheme) {
  document.body.dataset.theme = savedTheme;
  selectTheme.value = savedTheme;
}

// Target Language Selector
selectLang.addEventListener('change', (e) => {
  const lang = e.target.value;
  const langName = e.target.options[e.target.selectedIndex].text;
  showToast(`Switching translation to ${langName}...`);
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.set_target_language(lang);
  }
});

// Opacity Slider
sliderOpacity.addEventListener('input', (e) => {
  const val = e.target.value;
  opacityVal.textContent = `${val}%`;
  document.documentElement.style.setProperty('--bg-dark', `rgba(10, 12, 16, ${val / 100})`);
});

// Sync Timing Nudge
function updateNudge(val) {
  syncOffset = Math.round((syncOffset + val) * 10) / 10;
  nudgeOffsetVal.textContent = `${syncOffset > 0 ? '+' : ''}${syncOffset.toFixed(1)}s`;
}

btnNudgeMinus.addEventListener('click', () => updateNudge(-0.2));
btnNudgePlus.addEventListener('click', () => updateNudge(0.2));
btnNudgeReset.addEventListener('click', () => {
  syncOffset = 0.0;
  nudgeOffsetVal.textContent = '0.0s';
});

// Syllable Sweep Checkbox
checkSweep.addEventListener('change', (e) => {
  enableSweep = e.target.checked;
  document.body.classList.toggle('enable-sweep', enableSweep);
});
document.body.classList.add('enable-sweep');

// Phonetics / Romaji Checkbox
checkRomaji.addEventListener('change', (e) => {
  document.body.classList.toggle('hide-romaji', !e.target.checked);
});

// Discord Rich Presence Checkbox
checkDiscord.addEventListener('change', (e) => {
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.toggle_discord_rpc(e.target.checked);
    showToast(e.target.checked ? "Discord Status Enabled" : "Discord Status Disabled");
  }
});

// Gamer Ghost Mode (Click-Through)
function setGhostMode(isGhost) {
  checkGhost.checked = isGhost;
  elGhostBadge.style.display = isGhost ? 'inline-block' : 'none';
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.toggle_ghost_mode(isGhost);
  }
  showToast(isGhost ? "Ghost Mode ON (Press Ctrl+Shift+G to disable)" : "Ghost Mode Disabled");
}

checkGhost.addEventListener('change', (e) => {
  setGhostMode(e.target.checked);
});

// Global Hotkey Hook: Toggle Ghost Mode
window.toggleGhostModeHotKey = function() {
  setGhostMode(!checkGhost.checked);
};

// Sleep Timer with Live Countdown Pill
selectSleep.addEventListener('change', (e) => {
  const mins = parseInt(e.target.value, 10);
  setSleepTimer(mins);
});

function setSleepTimer(mins) {
  clearInterval(sleepTimerTicker);
  if (mins > 0) {
    sleepTimerEnd = Date.now() + mins * 60 * 1000;
    elSleepTimerBadge.style.display = 'inline-block';
    updateSleepTimerBadge();
    sleepTimerTicker = setInterval(updateSleepTimerBadge, 1000);
    showToast(`🌙 Sleep timer set for ${mins} minutes`);
  } else {
    sleepTimerEnd = 0;
    elSleepTimerBadge.style.display = 'none';
    selectSleep.value = "0";
  }

  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.set_sleep_timer(mins);
  }
}

function updateSleepTimerBadge() {
  const now = Date.now();
  const diffSec = Math.max(0, Math.floor((sleepTimerEnd - now) / 1000));
  if (diffSec <= 0) {
    clearInterval(sleepTimerTicker);
    elSleepTimerBadge.style.display = 'none';
    selectSleep.value = "0";
    return;
  }
  elSleepTimerBadge.textContent = `🌙 ${formatTime(diffSec)}`;
}

elSleepTimerBadge.addEventListener('click', () => {
  if (confirm("Cancel the active sleep timer?")) {
    setSleepTimer(0);
    showToast("Sleep timer cancelled.");
  }
});

window.onSleepTimerTriggered = function() {
  clearInterval(sleepTimerTicker);
  elSleepTimerBadge.style.display = 'none';
  selectSleep.value = "0";
  showToast("🌙 Sleep Timer triggered: Spotify paused.");
};

// Copy Current Line
btnCopyLine.addEventListener('click', () => {
  if (activeIndex >= 0 && activeIndex < currentLyrics.length) {
    const item = currentLyrics[activeIndex];
    const textToCopy = `${item.original || item.text || ''}\n${item.translation || ''}`.trim();
    navigator.clipboard.writeText(textToCopy).then(() => {
      showToast("📋 Copied line to clipboard!");
    });
  }
});

// Copy All Lyrics (Bilingual)
btnCopyAll.addEventListener('click', () => {
  if (!currentLyrics || currentLyrics.length === 0) return;
  let text = `=== ${currentSongTitle} - ${currentSongArtist} ===\n\n`;
  currentLyrics.forEach(l => {
    if (l.time >= 0) {
      const timeTag = `[${formatTime(l.time)}]`;
      text += `${timeTag} ${l.original || l.text || ''}\n`;
      if (l.translation) text += `       ${l.translation}\n`;
    }
  });
  navigator.clipboard.writeText(text).then(() => {
    showToast("📄 Full bilingual lyrics copied to clipboard!");
  });
});

// Export .LRC File
btnExportLrc.addEventListener('click', () => {
  if (!currentLyrics || currentLyrics.length === 0) return;
  let content = `[ti:${currentSongTitle}]\n[ar:${currentSongArtist}]\n`;
  currentLyrics.forEach(l => {
    if (l.time >= 0) {
      const min = Math.floor(l.time / 60);
      const sec = (l.time % 60).toFixed(2);
      const timeTag = `[${min < 10 ? '0' : ''}${min}:${sec < 10 ? '0' : ''}${sec}]`;
      content += `${timeTag} ${l.original || l.text || ''}\n`;
      if (l.translation) content += `${timeTag} (${l.translation})\n`;
    }
  });

  const filename = `${currentSongArtist} - ${currentSongTitle}.lrc`;
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.export_lyrics(content, filename).then((msg) => {
      showToast(msg || "Exported .lrc successfully!");
    });
  }
});

// Export .SRT Subtitles File
btnExportSrt.addEventListener('click', () => {
  if (!currentLyrics || currentLyrics.length === 0) return;
  let srt = "";
  let index = 1;
  for (let i = 0; i < currentLyrics.length; i++) {
    const cur = currentLyrics[i];
    if (cur.time < 0) continue;
    const startTime = cur.time;
    let endTime = (i + 1 < currentLyrics.length && currentLyrics[i + 1].time > startTime)
      ? currentLyrics[i + 1].time
      : startTime + 3.5;

    srt += `${index}\n`;
    srt += `${formatSrtTime(startTime)} --> ${formatSrtTime(endTime)}\n`;
    srt += `${cur.original || cur.text || ''}\n`;
    if (cur.translation) {
      srt += `(${cur.translation})\n`;
    }
    srt += `\n`;
    index++;
  }

  const filename = `${currentSongArtist} - ${currentSongTitle}.srt`;
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.export_srt(srt, filename).then((msg) => {
      showToast(msg || "Exported .srt subtitles successfully!");
    });
  }
});

// Export Printable Lyric Poster (HTML)
btnExportSheet.addEventListener('click', () => {
  if (!currentLyrics || currentLyrics.length === 0) {
    showToast("No lyrics loaded to export.");
    return;
  }

  let rows = "";
  currentLyrics.forEach(l => {
    rows += `
      <tr>
        <td class="ts">${l.time >= 0 ? formatTime(l.time) : ''}</td>
        <td class="orig">
          <div>${l.original || l.text || ''}</div>
          ${l.romaji ? `<div class="rom">${l.romaji}</div>` : ''}
        </td>
        <td class="trans">${l.translation || ''}</td>
      </tr>
    `;
  });

  const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>${currentSongTitle} - Lyrics & Translation</title>
  <style>
    body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0f1218; color: #fff; padding: 40px; margin: 0; }
    .card { max-width: 800px; margin: 0 auto; background: #161b24; padding: 30px; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.5); }
    .hdr { display: flex; align-items: center; gap: 20px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 20px; margin-bottom: 25px; }
    .art { width: 90px; height: 90px; border-radius: 12px; object-fit: cover; }
    h1 { margin: 0; font-size: 24px; color: #fff; }
    h2 { margin: 4px 0 0; font-size: 16px; color: #10b981; }
    table { width: 100%; border-collapse: collapse; }
    td { padding: 12px 10px; border-bottom: 1px solid rgba(255,255,255,0.06); vertical-align: top; }
    .ts { font-size: 11px; color: #64748b; width: 50px; font-weight: bold; }
    .orig { font-size: 16px; font-weight: 700; width: 45%; }
    .rom { font-size: 12px; font-style: italic; color: #a5b4fc; margin-top: 3px; font-weight: normal; }
    .trans { font-size: 15px; color: #22d3ee; width: 45%; font-weight: 600; }
    @media print {
      body { background: #fff !important; color: #000 !important; }
      .card { box-shadow: none; padding: 0; }
      h1, h2, .orig { color: #000 !important; }
      .trans { color: #333 !important; }
      .rom { color: #666 !important; }
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="hdr">
      ${currentSongThumbnail ? `<img src="${currentSongThumbnail}" class="art">` : ''}
      <div>
        <h1>${currentSongTitle}</h1>
        <h2>${currentSongArtist}</h2>
      </div>
    </div>
    <table>
      ${rows}
    </table>
  </div>
</body>
</html>`;

  const filename = `${currentSongArtist} - ${currentSongTitle} (Poster).html`;
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.export_lyric_sheet(html, filename).then(msg => {
      showToast(msg || "Printable poster sheet exported to Desktop!");
    });
  }
});

// Song History Modal Handlers
btnHistoryOpen.addEventListener('click', () => {
  settingsDrawer.style.display = 'none';
  historyModal.style.display = 'flex';
  renderHistory();
});

btnHistoryClose.addEventListener('click', () => {
  historyModal.style.display = 'none';
});

function renderHistory() {
  historyList.innerHTML = '<div style="color:var(--text-muted);font-size:12px;text-align:center;padding:20px;">Loading history...</div>';
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.get_song_history().then(items => {
      if (!items || items.length === 0) {
        historyList.innerHTML = '<div style="color:var(--text-muted);font-size:12px;text-align:center;padding:20px;">No song history yet.</div>';
        return;
      }
      historyList.innerHTML = '';
      items.forEach(it => {
        const row = document.createElement('div');
        row.className = 'history-item';
        row.innerHTML = `
          ${it.thumbnail ? `<img src="${it.thumbnail}" class="history-thumb">` : `<div class="history-thumb"></div>`}
          <div class="history-info">
            <div class="history-title">${it.title}</div>
            <div class="history-artist">${it.artist}</div>
          </div>
          ${it.is_favorite ? `<span class="history-fav-star">♥</span>` : ''}
        `;
        row.addEventListener('click', () => {
          historyModal.style.display = 'none';
          showToast(`Loading: ${it.title}...`);
          window.pywebview.api.load_history_song(it.artist, it.title);
        });
        historyList.appendChild(row);
      });
    });
  }
}

// Vocabulary Notebook Modal Handlers
btnVocabOpen.addEventListener('click', () => {
  settingsDrawer.style.display = 'none';
  vocabModal.style.display = 'flex';
  renderVocab();
});

btnVocabClose.addEventListener('click', () => {
  vocabModal.style.display = 'none';
});

btnExportVocab.addEventListener('click', () => {
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.export_vocab_csv().then(msg => {
      showToast(msg || "Exported vocabulary deck to Desktop!");
    });
  }
});

function renderVocab() {
  vocabList.innerHTML = '<div style="color:var(--text-muted);font-size:12px;text-align:center;padding:20px;">Loading words...</div>';
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.get_vocab_words().then(words => {
      if (!words || words.length === 0) {
        vocabList.innerHTML = '<div style="color:var(--text-muted);font-size:12px;text-align:center;padding:20px;">No saved vocabulary words yet.<br>Double-click any lyric word and click ⭐ to save!</div>';
        return;
      }
      vocabList.innerHTML = '';
      words.forEach(w => {
        const item = document.createElement('div');
        item.className = 'vocab-item';
        item.innerHTML = `
          <div class="vocab-left">
            <div class="vocab-word">${w.word} <span class="vocab-romaji">(${w.romaji || ''})</span></div>
            <div class="vocab-meaning">${w.meaning}</div>
          </div>
          <button class="vocab-del" title="Delete word">✕</button>
        `;
        item.querySelector('.vocab-del').addEventListener('click', (e) => {
          e.stopPropagation();
          window.pywebview.api.delete_vocab_word(w.id);
          renderVocab();
        });
        vocabList.appendChild(item);
      });
    });
  }
}

// Floating Word Dictionary & Pronunciation Tooltip
function triggerWordLookup(word, clientX, clientY) {
  if (!word || !checkLearner.checked) return;
  currentDictWord = word;
  
  dictCard.style.display = 'flex';
  dictWord.textContent = word;
  dictRomaji.textContent = "Loading pronunciation...";
  dictMeaning.textContent = "Translating...";
  dictLang.textContent = "Detecting...";
  btnDictSave.textContent = "⭐";

  const cardWidth = 280;
  const cardHeight = 125;
  let posX = clientX - 20;
  let posY = clientY + 15;

  if (posX + cardWidth > window.innerWidth - 10) posX = window.innerWidth - cardWidth - 15;
  if (posY + cardHeight > window.innerHeight - 10) posY = clientY - cardHeight - 15;
  if (posX < 10) posX = 10;
  if (posY < 10) posY = 10;

  dictCard.style.left = `${posX}px`;
  dictCard.style.top = `${posY}px`;

  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.lookup_word(word).then(res => {
      if (res) {
        dictWord.textContent = res.word || word;
        currentDictRomaji = res.romaji || "";
        currentDictMeaning = res.trans || "No definition found.";
        dictRomaji.textContent = currentDictRomaji;
        dictMeaning.textContent = currentDictMeaning;
        currentDictLang = res.lang || dominantLanguage;
        dictLang.textContent = `Language: ${currentDictLang.toUpperCase()}`;
      }
    });
  }
}

btnDictClose.addEventListener('click', () => {
  dictCard.style.display = 'none';
});

btnDictCopy.addEventListener('click', () => {
  const text = `${dictWord.textContent} (${dictRomaji.textContent}): ${dictMeaning.textContent}`;
  navigator.clipboard.writeText(text).then(() => {
    showToast("📋 Word copied to clipboard!");
  });
});

btnDictSave.addEventListener('click', () => {
  if (!currentDictWord) return;
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.save_vocab_word(
      currentDictWord,
      currentDictRomaji,
      currentDictMeaning,
      currentDictLang,
      currentSongTitle
    ).then(() => {
      btnDictSave.textContent = "✓";
      showToast(`⭐ Saved "${currentDictWord}" to Vocabulary Notebook!`);
    });
  }
});

// Text-to-Speech audio pronunciation
function speakWord(text, lang) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  if (lang === 'ko') utterance.lang = 'ko-KR';
  else if (lang === 'ja') utterance.lang = 'ja-JP';
  else if (lang === 'zh' || lang === 'zh-cn') utterance.lang = 'zh-CN';
  else if (lang === 'es') utterance.lang = 'es-ES';
  else if (lang === 'fr') utterance.lang = 'fr-FR';
  else if (lang === 'de') utterance.lang = 'de-DE';
  else if (lang === 'ar') utterance.lang = 'ar-SA';
  else if (lang === 'ru') utterance.lang = 'ru-RU';
  else utterance.lang = 'en-US';
  utterance.rate = 0.85;
  window.speechSynthesis.speak(utterance);
}

btnDictSpeak.addEventListener('click', () => {
  speakWord(currentDictWord, currentDictLang);
});

// Hide dictionary popup on outside click
document.addEventListener('mousedown', (e) => {
  if (dictCard.style.display === 'flex' && !dictCard.contains(e.target)) {
    dictCard.style.display = 'none';
  }
});

btnMin.addEventListener('click', () => {
  if (window.pywebview && window.pywebview.api) window.pywebview.api.minimize();
});

btnClose.addEventListener('click', () => {
  if (window.pywebview && window.pywebview.api) window.pywebview.api.close();
});

btnRetry.addEventListener('click', () => {
  if (window.pywebview && window.pywebview.api) window.pywebview.api.retry_lyrics();
});

// Dynamic Ambient Color Extractor from Album Art Thumbnail
function extractAndApplyColors(imgEl) {
  try {
    const canvas = document.createElement('canvas');
    canvas.width = 32;
    canvas.height = 32;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(imgEl, 0, 0, 32, 32);
    const data = ctx.getImageData(0, 0, 32, 32).data;

    let r = 0, g = 0, b = 0, count = 0;
    for (let i = 0; i < data.length; i += 16) {
      const red = data[i], green = data[i+1], blue = data[i+2];
      if ((red + green + blue > 60) && (red + green + blue < 700)) {
        r += red; g += green; b += blue; count++;
      }
    }
    if (count > 0) {
      r = Math.floor(r / count);
      g = Math.floor(g / count);
      b = Math.floor(b / count);
      const color1 = `rgb(${r}, ${g}, ${b})`;
      const color2 = `rgb(${Math.min(255, r + 45)}, ${Math.max(0, g - 25)}, ${Math.min(255, b + 65)})`;
      const color3 = `rgb(${Math.max(0, r - 30)}, ${Math.min(255, g + 50)}, ${Math.min(255, b + 80)})`;
      document.documentElement.style.setProperty('--orb-color-1', color1);
      document.documentElement.style.setProperty('--orb-color-2', color2);
      document.documentElement.style.setProperty('--orb-color-3', color3);
    }
  } catch (e) {}
}

elTrackArtwork.onload = () => extractAndApplyColors(elTrackArtwork);

// Fluid Canvas Spectrum Visualizer Animation
function startSpectrumVisualizer() {
  if (!ctxSpectrum) return;
  cancelAnimationFrame(spectrumAnimId);

  const numBars = 18;
  const barWidth = 5;
  const gap = 3;
  let phase = 0;

  function draw() {
    ctxSpectrum.clearRect(0, 0, canvasSpectrum.width, canvasSpectrum.height);

    if (isPlaying) {
      phase += 0.08;
      for (let i = 0; i < numBars; i++) {
        // Pseudo-audio wave simulation
        const wave1 = Math.sin(phase * 1.5 + i * 0.45);
        const wave2 = Math.cos(phase * 2.1 + i * 0.7);
        const heightFactor = Math.abs(wave1 * 0.6 + wave2 * 0.4);
        const barHeight = Math.max(3, heightFactor * canvasSpectrum.height * 0.95);
        const x = i * (barWidth + gap) + 6;
        const y = canvasSpectrum.height - barHeight;

        // Gradient based on current theme/album colors
        const grad = ctxSpectrum.createLinearGradient(0, y, 0, canvasSpectrum.height);
        grad.addColorStop(0, '#10b981');
        grad.addColorStop(1, '#06b6d4');
        ctxSpectrum.fillStyle = grad;
        ctxSpectrum.fillRect(x, y, barWidth, barHeight);
      }
      spectrumAnimId = requestAnimationFrame(draw);
    } else {
      // Draw resting dots
      for (let i = 0; i < numBars; i++) {
        const x = i * (barWidth + gap) + 6;
        ctxSpectrum.fillStyle = 'rgba(255,255,255,0.2)';
        ctxSpectrum.fillRect(x, canvasSpectrum.height - 3, barWidth, 3);
      }
    }
  }

  draw();
}

// Python -> JS API Updates
window.updateTrack = function(data) {
  if (!data || !data.title) {
    elTrackTitle.textContent = "Waiting for Spotify...";
    elTrackArtist.textContent = "Play a song to begin";
    elIslandSongTitle.textContent = "Waiting for Spotify...";
    elIslandSongArtist.textContent = "";
    document.body.classList.add('paused');
    elIdleState.style.display = 'flex';
    elLyricsList.style.display = 'none';
    elNoLyricsState.style.display = 'none';
    elFlagBadge.style.display = 'none';
    elTrackArtwork.style.display = 'none';
    elTrackDisc.style.display = 'flex';
    elIslandArtwork.style.display = 'none';
    elIslandDisc.style.display = 'flex';
    elInstrumentalPill.style.display = 'none';
    isPlaying = false;
    currentLyrics = [];
    basePosition = 0;
    baseTimestamp = 0;
    startSpectrumVisualizer();
    return;
  }

  currentSongTitle = data.title;
  currentSongArtist = data.artist || "";
  currentSongThumbnail = data.thumbnail || "";
  elTrackTitle.textContent = data.title;
  elTrackArtist.textContent = data.artist || "Unknown Artist";
  elIslandSongTitle.textContent = data.title;
  elIslandSongArtist.textContent = data.artist || "";
  currentDuration = data.duration || 0;
  elTotalTime.textContent = formatTime(currentDuration);

  // Sync position timestamps
  if (data.position !== undefined) {
    basePosition = Number(data.position) || 0;
    baseTimestamp = Number(data.timestamp) || Date.now();
    window.updatePosition(basePosition, Boolean(data.is_seek));
  }

  // Favorite Heart Status
  isFavorite = Boolean(data.is_favorite);
  btnHeart.textContent = isFavorite ? "♥" : "♡";
  btnHeart.classList.toggle('active', isFavorite);

  // Album Artwork
  if (data.thumbnail) {
    elTrackArtwork.src = data.thumbnail;
    elTrackArtwork.style.display = 'block';
    elTrackDisc.style.display = 'none';

    elIslandArtwork.src = data.thumbnail;
    elIslandArtwork.style.display = 'block';
    elIslandDisc.style.display = 'none';
  } else {
    elTrackArtwork.style.display = 'none';
    elTrackDisc.style.display = 'flex';

    elIslandArtwork.style.display = 'none';
    elIslandDisc.style.display = 'flex';
  }

  // Playback Status
  isPlaying = (data.status === 4);
  if (isPlaying) {
    document.body.classList.remove('paused');
    iconPlay.style.display = 'none';
    iconPause.style.display = 'block';
    islandIconPlay.style.display = 'none';
    islandIconPause.style.display = 'block';
  } else {
    document.body.classList.add('paused');
    iconPlay.style.display = 'block';
    iconPause.style.display = 'none';
    islandIconPlay.style.display = 'block';
    islandIconPause.style.display = 'none';
    if (basePosition >= 0) {
      window.updatePosition(basePosition, false);
    }
  }

  startSpectrumVisualizer();
};

window.updateLyrics = function(data) {
  elIdleState.style.display = 'none';
  
  if (!data || !data.lines || data.lines.length === 0) {
    elLyricsList.style.display = 'none';
    elNoLyricsState.style.display = 'flex';
    elFlagBadge.style.display = 'none';
    currentLyrics = [];
    elIslandLyricsScroll.innerHTML = '';
    return;
  }

  elNoLyricsState.style.display = 'none';
  elLyricsList.style.display = 'flex';
  currentLyrics = data.lines;
  activeIndex = -1;

  // Language Flag Badge
  if (data.lang && data.lang !== 'unknown') {
    dominantLanguage = data.lang.toLowerCase();
    elFlagBadge.textContent = LANG_FLAGS[dominantLanguage] || `${data.lang.toUpperCase()}`;
    elFlagBadge.style.display = 'inline-block';
  } else {
    elFlagBadge.style.display = 'none';
  }

  // Render Lyric Lines for Main Viewport
  elLyricsList.innerHTML = '';
  elIslandLyricsScroll.innerHTML = '';

  currentLyrics.forEach((line, index) => {
    // Main Viewport Line
    const div = document.createElement('div');
    div.className = 'lyric-line' + (line.translation ? '' : ' no-trans');
    div.id = `line-${index}`;
    div.dataset.time = line.time;

    const origDiv = document.createElement('div');
    origDiv.className = 'original-text';
    origDiv.textContent = line.original || line.text || '';
    div.appendChild(origDiv);

    const romajiDiv = document.createElement('div');
    romajiDiv.className = 'romaji-text';
    romajiDiv.id = `romaji-${index}`;
    romajiDiv.textContent = line.romaji || '';
    div.appendChild(romajiDiv);

    const transDiv = document.createElement('div');
    transDiv.className = 'translated-text';
    transDiv.id = `trans-${index}`;
    transDiv.textContent = line.translation || '';
    div.appendChild(transDiv);

    const seekIcon = document.createElement('div');
    seekIcon.className = 'line-seek-icon';
    seekIcon.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>`;
    div.appendChild(seekIcon);

    // Click to Seek
    div.addEventListener('click', () => {
      if (line.time >= 0 && window.pywebview && window.pywebview.api) {
        basePosition = line.time;
        baseTimestamp = Date.now();
        window.updatePosition(line.time, true);
        window.pywebview.api.seek(line.time);
      }
    });

    // Right-Click: Copy Line with Toast
    div.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      const textToCopy = `${line.original || line.text || ''}\n${line.translation || ''}`.trim();
      navigator.clipboard.writeText(textToCopy).then(() => {
        showToast("📋 Copied line to clipboard!");
      });
    });

    // Double-Click: Dictionary Lookup & Audio Speech
    origDiv.addEventListener('dblclick', (e) => {
      e.stopPropagation();
      let selectedText = window.getSelection().toString().trim();
      if (!selectedText) {
        selectedText = origDiv.textContent.trim();
      }
      if (selectedText) {
        triggerWordLookup(selectedText, e.clientX, e.clientY);
      }
    });

    elLyricsList.appendChild(div);

    // Mini Drawer Line Item
    const miniItem = document.createElement('div');
    miniItem.className = 'mini-line-item';
    miniItem.id = `mini-line-${index}`;
    miniItem.dataset.time = line.time;

    const miniOrig = document.createElement('div');
    miniOrig.className = 'mini-orig';
    miniOrig.textContent = line.original || line.text || '';
    miniItem.appendChild(miniOrig);

    const miniTrans = document.createElement('div');
    miniTrans.className = 'mini-trans';
    miniTrans.id = `mini-trans-${index}`;
    miniTrans.textContent = line.translation || '';
    miniItem.appendChild(miniTrans);

    miniItem.addEventListener('click', () => {
      if (line.time >= 0 && window.pywebview && window.pywebview.api) {
        basePosition = line.time;
        baseTimestamp = Date.now();
        window.updatePosition(line.time, true);
        window.pywebview.api.seek(line.time);
      }
    });

    miniItem.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      const textToCopy = `${line.original || line.text || ''}\n${line.translation || ''}`.trim();
      navigator.clipboard.writeText(textToCopy).then(() => {
        showToast("📋 Copied line to clipboard!");
      });
    });

    elIslandLyricsScroll.appendChild(miniItem);
  });
};

// Stream Translations + Romanizations into Rendered Lines
window.updateTranslations = function(data) {
  if (!data || !data.lines) return;

  if (data.lang && data.lang !== 'unknown') {
    dominantLanguage = data.lang.toLowerCase();
    elFlagBadge.textContent = LANG_FLAGS[dominantLanguage] || `${data.lang.toUpperCase()}`;
    elFlagBadge.style.display = 'inline-block';
  }

  data.lines.forEach((item, index) => {
    if (index < currentLyrics.length) {
      currentLyrics[index].translation = item.translation || '';
      currentLyrics[index].romaji = item.romaji || '';

      const lineEl = document.getElementById(`line-${index}`);
      if (lineEl) {
        if (item.translation) {
          lineEl.classList.remove('no-trans');
        } else {
          lineEl.classList.add('no-trans');
        }
      }

      const transEl = document.getElementById(`trans-${index}`);
      if (transEl) transEl.textContent = item.translation || '';

      const romajiEl = document.getElementById(`romaji-${index}`);
      if (romajiEl) romajiEl.textContent = item.romaji || '';

      const miniTransEl = document.getElementById(`mini-trans-${index}`);
      if (miniTransEl) miniTransEl.textContent = item.translation || '';
    }
  });

  if (activeIndex >= 0 && activeIndex < currentLyrics.length) {
    elIslandTranslation.textContent = currentLyrics[activeIndex].translation || '';
    elIslandRomaji.textContent = currentLyrics[activeIndex].romaji || '';
  }
};

// Position Tracker, Word-by-Word Karaoke Sweep & Instrumental Countdown
window.updatePosition = function(seconds, isSeek = false) {
  if (isSeek) {
    basePosition = seconds;
    baseTimestamp = Date.now();
  }

  const adjustedSeconds = Math.max(0, seconds + syncOffset);

  const jumpDiff = Math.abs(adjustedSeconds - lastRenderedPosition);
  if (jumpDiff > 1.4 || isSeek) {
    userScrolledRecently = false;
    clearTimeout(userScrollTimeout);
  }
  lastRenderedPosition = adjustedSeconds;

  if (!isScrubbing) {
    elCurrentTime.textContent = formatTime(adjustedSeconds);
    if (currentDuration > 0) {
      const pct = Math.min(100, Math.max(0, (adjustedSeconds / currentDuration) * 100));
      elScrubFill.style.width = `${pct}%`;
    }
  }

  if (!currentLyrics || currentLyrics.length === 0) return;

  // Determine currently active line
  let newIndex = -1;
  for (let i = 0; i < currentLyrics.length; i++) {
    if (currentLyrics[i].time <= adjustedSeconds + 0.12) {
      newIndex = i;
    } else {
      break;
    }
  }

  // Instrumental Solo Break Countdown Detection
  if (newIndex >= 0 && newIndex + 1 < currentLyrics.length) {
    const nextLineTime = currentLyrics[newIndex + 1].time;
    const gap = nextLineTime - adjustedSeconds;
    if (gap > 6.0 && (adjustedSeconds - currentLyrics[newIndex].time) > 2.5) {
      elInstrumentalPill.style.display = 'flex';
      elInstrumentalText.textContent = `Instrumental Solo (${Math.ceil(gap)}s)`;
    } else {
      elInstrumentalPill.style.display = 'none';
    }
  } else {
    elInstrumentalPill.style.display = 'none';
  }

  // Word-by-Word Karaoke Sweep Progress Update
  if (newIndex >= 0 && enableSweep) {
    const curTime = currentLyrics[newIndex].time;
    const nextTime = (newIndex + 1 < currentLyrics.length && currentLyrics[newIndex + 1].time > curTime)
      ? currentLyrics[newIndex + 1].time
      : curTime + 4.0;
    const duration = Math.max(0.6, nextTime - curTime);
    const elapsed = Math.max(0, adjustedSeconds - curTime);
    const progress = Math.min(100, Math.max(0, (elapsed / duration) * 100));

    const activeEl = document.getElementById(`line-${newIndex}`);
    if (activeEl) {
      activeEl.style.setProperty('--line-progress', `${progress}%`);
    }
  }

  // Active Line Change Event
  if (newIndex !== activeIndex) {
    if (activeIndex >= 0) {
      const prevEl = document.getElementById(`line-${activeIndex}`);
      if (prevEl) {
        prevEl.classList.remove('active');
        prevEl.style.removeProperty('--line-progress');
      }

      const prevMini = document.getElementById(`mini-line-${activeIndex}`);
      if (prevMini) prevMini.classList.remove('active');
    }

    activeIndex = newIndex;

    if (activeIndex >= 0) {
      const activeEl = document.getElementById(`line-${activeIndex}`);
      if (activeEl) {
        activeEl.classList.add('active');

        if (!userScrolledRecently) {
          activeEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }

        const item = currentLyrics[activeIndex];
        elIslandOriginal.textContent = item.original || item.text || '';
        elIslandRomaji.textContent = item.romaji || '';
        elIslandTranslation.textContent = item.translation || '';
      }

      const activeMini = document.getElementById(`mini-line-${activeIndex}`);
      if (activeMini) {
        activeMini.classList.add('active');
        if (isMiniExpanded) {
          activeMini.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }
    }
  }
};

// Smooth Playback Loop (Native 60fps/144fps client-side animation, 0% CPU IPC overhead)
function smoothPlaybackLoop() {
  if (isPlaying && baseTimestamp > 0 && currentDuration > 0) {
    const elapsed = (Date.now() - baseTimestamp) / 1000;
    const currentSec = Math.min(currentDuration, Math.max(0, basePosition + elapsed));
    window.updatePosition(currentSec, false);
  }
  requestAnimationFrame(smoothPlaybackLoop);
}
requestAnimationFrame(smoothPlaybackLoop);
