  // ---------------------------------------------------------------------------
  // Copy and exports
  // ---------------------------------------------------------------------------

  function copyCurrentLine() {
    if (AppState.activeIndex < 0 || !AppState.lyrics[AppState.activeIndex]) {
      showToast('No active lyric line to copy.', { icon: 'info' });
      return;
    }
    copyText(lineText(AppState.lyrics[AppState.activeIndex])).then(function () {
      showToast('Line copied', { icon: 'copy' });
    });
  }

  function copyAllLyrics() {
    if (!AppState.lyrics.length) {
      showToast('No lyrics to copy.', { icon: 'info' });
      return;
    }
    var text = '=== ' + AppState.track.title + ' - ' + AppState.track.artist + ' ===\n\n';
    AppState.lyrics.forEach(function (line) {
      if (line.time >= 0) text += '[' + formatTime(line.time) + '] ' + line.original + '\n';
      else text += line.original + '\n';
      if (line.translation) text += '       ' + line.translation + '\n';
    });
    copyText(text).then(function () {
      showToast('All lyrics copied', { icon: 'copy' });
    });
  }

  function exportLrc() {
    if (!AppState.lyrics.length) {
      showToast('No lyrics loaded to export.', { icon: 'info' });
      return;
    }
    var content = '[ti:' + AppState.track.title + ']\n[ar:' + AppState.track.artist + ']\n';
    AppState.lyrics.forEach(function (line) {
      if (line.time < 0) return;
      var mins = Math.floor(line.time / 60);
      var secs = (line.time % 60).toFixed(2);
      var stamp = '[' + String(mins).padStart(2, '0') + ':' + (Number(secs) < 10 ? '0' : '') + secs + ']';
      content += stamp + ' ' + line.original + '\n';
      if (line.translation) content += stamp + ' (' + line.translation + ')\n';
    });
    var filename = AppState.track.artist + ' - ' + AppState.track.title + '.lrc';
    callApi('export_lyrics', content, filename).then(function (message) {
      showToast(message || 'Exported LRC to Desktop', { icon: 'download' });
    });
  }

  function exportSrt() {
    if (!AppState.lyrics.length) {
      showToast('No lyrics loaded to export.', { icon: 'info' });
      return;
    }
    var srt = '';
    var index = 1;
    AppState.lyrics.forEach(function (line, i) {
      if (line.time < 0) return;
      var start = line.time;
      var next = i + 1 < AppState.lyrics.length ? AppState.lyrics[i + 1].time : -1;
      var end = next > start ? next : start + 3.5;
      srt += index + '\n' + formatSrtTime(start) + ' --> ' + formatSrtTime(end) + '\n' + line.original + '\n';
      if (line.translation) srt += '(' + line.translation + ')\n';
      srt += '\n';
      index++;
    });
    var filename = AppState.track.artist + ' - ' + AppState.track.title + '.srt';
    callApi('export_srt', srt, filename).then(function (message) {
      showToast(message || 'Exported SRT to Desktop', { icon: 'download' });
    });
  }

  function exportPoster() {
    if (!AppState.lyrics.length) {
      showToast('No lyrics loaded to export.', { icon: 'info' });
      return;
    }
    var rows = AppState.lyrics.map(function (line) {
      var romaji = line.romaji ? '<div class="rom">' + escapeHtml(line.romaji) + '</div>' : '';
      return '<tr><td class="ts">' + (line.time >= 0 ? formatTime(line.time) : '') + '</td>' +
        '<td class="orig"><div>' + escapeHtml(line.original) + '</div>' + romaji + '</td>' +
        '<td class="trans">' + escapeHtml(line.translation) + '</td></tr>';
    }).join('');
    var title = escapeHtml(AppState.track.title);
    var artist = escapeHtml(AppState.track.artist);
    var thumb = AppState.track.thumbnail
      ? '<img src="' + escapeHtml(AppState.track.thumbnail) + '" class="art" alt="">'
      : '';
    var html = '<!DOCTYPE html><html><head><meta charset="utf-8"><title>' + title + ' — Lyrics</title>' +
      '<style>body{font-family:"Segoe UI",system-ui,sans-serif;background:#0f1218;color:#fff;padding:40px;margin:0}' +
      '.card{max-width:820px;margin:0 auto;background:#161b24;padding:30px;border-radius:20px;box-shadow:0 10px 40px rgba(0,0,0,.5)}' +
      '.hdr{display:flex;align-items:center;gap:20px;border-bottom:1px solid rgba(255,255,255,.1);padding-bottom:20px;margin-bottom:25px}' +
      '.art{width:92px;height:92px;border-radius:12px;object-fit:cover}h1{margin:0;font-size:24px}h2{margin:4px 0 0;font-size:15px;color:#9db8e8;font-weight:500}' +
      'table{width:100%;border-collapse:collapse}td{padding:11px 10px;border-bottom:1px solid rgba(255,255,255,.06);vertical-align:top}' +
      '.ts{font-size:11px;color:#64748b;width:52px;font-weight:700;font-variant-numeric:tabular-nums}.orig{font-size:16px;font-weight:700;width:46%}' +
      '.rom{font-size:12px;font-style:italic;color:#a5b4fc;margin-top:3px;font-weight:400}.trans{font-size:15px;color:#93c5fd;width:46%;font-weight:500}' +
      '@media print{body{background:#fff!important;color:#000!important}.card{box-shadow:none;padding:0}.orig,.trans,.rom,h1,h2{color:#000!important}}</style></head><body><div class="card">' +
      '<div class="hdr">' + thumb + '<div><h1>' + title + '</h1><h2>' + artist + '</h2></div></div>' +
      '<table>' + rows + '</table></div></body></html>';
    var filename = AppState.track.artist + ' - ' + AppState.track.title + ' (Poster).html';
    callApi('export_lyric_sheet', html, filename).then(function (message) {
      showToast(message || 'Poster exported to Desktop', { icon: 'download' });
    });
  }

