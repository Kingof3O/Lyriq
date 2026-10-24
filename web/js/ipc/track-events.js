  // ---------------------------------------------------------------------------
  // Backend -> frontend events
  // ---------------------------------------------------------------------------

  var offsetRequestToken = 0;

  window.updateTrack = function (data) {
    if (!data || !data.title) {
      AppState.hasTrack = false;
      AppState.track = { title: '', artist: '', album: '', thumbnail: '', duration: 0 };
      AppState.lyrics = [];
      AppState.activeIndex = -1;
      AppState.duration = 0;
      AppState.basePositionMs = 0;
      AppState.isPlaying = false;
      AppState.offset = 0;
      AppState.preview = null;
      if (editingState) finishLineEdit(false);
      closeLineContext();
      setPlaying(false);
      el.trackTitle.textContent = 'Connecting to Spotify';
      el.trackArtist.textContent = 'Play a song to begin';
      el.trackAlbum.textContent = '';
      el.trackAlbum.hidden = true;
      el.subSep.hidden = true;
      el.stageTitle.textContent = 'No track';
      el.stageArtist.textContent = 'Open Spotify and play a song';
      el.stageAlbum.textContent = '';
      el.stageLang.hidden = true;
      el.stageProvider.hidden = true;
      el.totalTime.textContent = '0:00';
      el.currentTime.textContent = '0:00';
      el.scrubFill.style.width = '0%';
      el.miniProgressFill.style.width = '0%';
      if (el.squareScrubFill) el.squareScrubFill.style.width = '0%';
      if (el.squareTime) el.squareTime.textContent = '0:00';
      if (el.squareTitle) el.squareTitle.textContent = 'Connecting…';
      setTrackImage('');
      setProvider('', true);
      setLanguage('unknown');
      el.previewBanner.hidden = true;
      AppState.favorite = false;
      updateFavoriteUi(false);
      el.miniOriginal.textContent = 'Connecting…';
      el.miniRomaji.textContent = '';
      el.miniTranslation.textContent = '';
      el.lyricsList.replaceChildren();
      el.miniLyricsScroll.replaceChildren();
      hideSkeleton();
      showIdle();
      updateOffsetDisplay();
      return;
    }

    var changed = AppState.track.title !== data.title || AppState.track.artist !== (data.artist || '');
    AppState.hasTrack = true;
    AppState.track = {
      title: String(data.title || ''),
      artist: String(data.artist || ''),
      album: String(data.album || ''),
      thumbnail: String(data.thumbnail || ''),
      duration: Number(data.duration) || 0
    };
    AppState.duration = Number(data.duration) || 0;
    AppState.preview = null;
    el.previewBanner.hidden = true;

    el.trackTitle.textContent = AppState.track.title;
    el.trackArtist.textContent = AppState.track.artist || 'Unknown artist';
    el.trackAlbum.textContent = AppState.track.album;
    el.trackAlbum.hidden = !AppState.track.album;
    el.subSep.hidden = !AppState.track.album;
    el.stageTitle.textContent = AppState.track.title;
    el.stageArtist.textContent = AppState.track.artist || 'Unknown artist';
    el.stageAlbum.textContent = AppState.track.album;
    el.totalTime.textContent = formatTime(AppState.duration);
    if (el.squareTitle) {
      el.squareTitle.textContent = AppState.track.title + (AppState.track.artist ? ' • ' + AppState.track.artist : '');
    }

    var positionMs = data.position_ms !== undefined && data.position_ms !== null
      ? Number(data.position_ms)
      : (Number(data.position) || 0) * 1000;
    if (isFinite(positionMs) && positionMs >= 0) AppState.basePositionMs = positionMs;
    AppState.baseTimestamp = performance.now();

    var rate = Number(data.playback_rate);
    AppState.playbackRate = isFinite(rate) && rate > 0 ? clamp(rate, 0.25, 4) : 1;

    setTrackImage(AppState.track.thumbnail);
    updateMiniArtwork(AppState.track.thumbnail);
    updateFavoriteUi(Boolean(data.is_favorite));

    setPlaying(data.is_playing !== undefined ? Boolean(data.is_playing) : data.status === 4);
    renderPosition(currentPositionSeconds());

    if (changed) {
      AppState.lyrics = [];
      AppState.activeIndex = -1;
      if (editingState) finishLineEdit(false);
      closeLineContext();
      el.lyricsList.replaceChildren();
      el.miniLyricsScroll.replaceChildren();
      setProvider('', true);
      setLanguage('unknown');
      showTranslationStatus(false);
      showSkeleton();
      setMiniFromLine(null);
      loadSongOffset(AppState.track.artist, AppState.track.title);
    }
  };

