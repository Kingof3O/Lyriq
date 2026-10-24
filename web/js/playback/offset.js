  // ---------------------------------------------------------------------------
  // Per-song offset
  // ---------------------------------------------------------------------------

  function loadSongOffset(artist, title) {
    var token = ++offsetRequestToken;
    AppState.offset = 0;
    updateOffsetDisplay();
    if (!artist || !title || !hasApi('get_song_offset')) return;
    callApi('get_song_offset', artist, title).then(function (value) {
      if (token !== offsetRequestToken) return;
      if (AppState.track.artist !== artist || AppState.track.title !== title) return;
      var offset = Number(value);
      AppState.offset = isFinite(offset) ? clamp(offset, -30, 30) : 0;
      updateOffsetDisplay();
      if (AppState.isSynced) renderPosition(currentPositionSeconds());
    });
  }

  function updateOffsetDisplay() {
    var text = (AppState.offset > 0 ? '+' : '') + AppState.offset.toFixed(1) + 's';
    el.dockOffset.textContent = text;
    el.nudgeOffsetVal.textContent = text;
    el.offsetSongLabel.textContent = AppState.hasTrack
      ? AppState.track.title + ' — saved for this song'
      : 'No song selected.';
    el.btnNudgeMinus.disabled = !AppState.hasTrack;
    el.btnNudgePlus.disabled = !AppState.hasTrack;
    el.btnNudgeReset.disabled = !AppState.hasTrack;
  }

  function nudgeOffset(delta) {
    if (!AppState.hasTrack) {
      showToast('Play a song before adjusting the offset.', { icon: 'info' });
      return;
    }
    AppState.offset = Math.round((AppState.offset + delta) * 10) / 10;
    AppState.offset = clamp(AppState.offset, -30, 30);
    updateOffsetDisplay();
    if (AppState.isSynced) {
      clearSynchronizedState();
      renderPosition(currentPositionSeconds());
    }
    callApi('set_song_offset', AppState.track.artist, AppState.track.title, AppState.offset);
  }

  function resetOffset() {
    if (!AppState.hasTrack) return;
    AppState.offset = 0;
    updateOffsetDisplay();
    callApi('set_song_offset', AppState.track.artist, AppState.track.title, 0);
    clearSynchronizedState();
    if (AppState.isSynced) renderPosition(currentPositionSeconds());
  }

  function updateFavoriteUi(favorite) {
    AppState.favorite = Boolean(favorite);
    el.heartUse.setAttribute('href', AppState.favorite ? '#icon-heart-filled' : '#icon-heart');
    el.btnHeart.classList.toggle('active', AppState.favorite);
    el.btnHeart.setAttribute('aria-pressed', String(AppState.favorite));
    el.btnHeart.setAttribute('aria-label', AppState.favorite ? 'Remove from favorites' : 'Favorite song');
    el.btnHeart.setAttribute('data-tooltip', AppState.favorite ? 'Remove from favorites' : 'Favorite');
  }

  function toggleFavorite() {
    if (!AppState.hasTrack) return;
    callApi('toggle_favorite', AppState.track.artist, AppState.track.title).then(function (favorite) {
      if (favorite === undefined) {
        favorite = !AppState.favorite;
      }
      updateFavoriteUi(Boolean(favorite));
      showToast(AppState.favorite ? 'Added to favorites' : 'Removed from favorites', { icon: 'heart-filled' });
    });
  }

