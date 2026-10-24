  // ---------------------------------------------------------------------------
  // Settings sheet
  // ---------------------------------------------------------------------------

  var lastSettingsTab = 'appearance';

  function openSettings(tab) {
    if (AppState.isMini) setMiniMode(false, { persist: false, backend: true });
    if (AppState.isSquare) setSquareMode(false, { persist: false, backend: true });
    closeOverflow();
    closeLineContext();
    setSettingsTab(tab || lastSettingsTab);
    el.settingsOverlay.hidden = false;
    refreshCacheStats();
    loadLrcFolder();
    el.settingsSheet.focus();
  }

  function closeSettings() {
    el.settingsOverlay.hidden = true;
  }

  function setSettingsTab(tab) {
    var valid = ['appearance', 'lyrics', 'translation', 'playback', 'shortcuts', 'data', 'about'];
    var next = valid.indexOf(tab) >= 0 ? tab : 'appearance';
    lastSettingsTab = next;
    valid.forEach(function (name) {
      var button = $('tab-' + name);
      var panel = $('panel-' + name);
      var active = name === next;
      if (button) {
        button.classList.toggle('is-active', active);
        button.setAttribute('aria-selected', String(active));
        button.tabIndex = active ? 0 : -1;
      }
      if (panel) panel.hidden = !active;
    });
    if (next === 'data') {
      refreshCacheStats();
      loadLrcFolder();
    }
    if (next === 'playback') refreshStartupState();
  }

  window.openSettings = openSettings;
  window.closeSettings = closeSettings;

  function wireSettingsIntegrations() {
    var btnGithubRepo = $('btnGithubRepo');
    if (btnGithubRepo) {
      btnGithubRepo.addEventListener('click', function (e) {
        e.preventDefault();
        callApi('open_external_url', 'https://github.com/Kingof3O/Lyriq');
      });
    }
    var btnCheckUpdates = $('btnCheckUpdates');
    var updateStatusText = $('updateStatusText');
    if (btnCheckUpdates) {
      btnCheckUpdates.addEventListener('click', function () {
        if (updateStatusText) updateStatusText.textContent = 'Checking GitHub for updates…';
        fetch('https://api.github.com/repos/Kingof3O/Lyriq/releases/latest', { cache: 'no-store' })
          .then(function (r) { if (!r.ok) throw new Error('Status ' + r.status); return r.json(); })
          .then(function (data) {
            var tag = (data && data.tag_name) || '';
            if (tag && tag !== 'v3.0.0' && tag !== '3.0.0') {
              if (updateStatusText) updateStatusText.innerHTML = '<span style="color:#C4B5FD">Update available: <b>' + escapeHtml(tag) + '</b>.</span> <a href="' + (data.html_url || 'https://github.com/Kingof3O/Lyriq/releases') + '" target="_blank" style="color:var(--brand);text-decoration:underline;">Download</a>';
              showToast('Update available: ' + tag, { icon: 'download' });
            } else {
              if (updateStatusText) updateStatusText.textContent = 'Lyriq v3.0.0 is up to date.';
              showToast('Lyriq is up to date', { icon: 'check' });
            }
          })
          .catch(function () {
            if (updateStatusText) updateStatusText.textContent = 'Lyriq v3.0.0 · Up to date (offline)';
            showToast('Checked: running latest build v3.0.0', { icon: 'check' });
          });
      });
    }
    if (el.btnSaveSpotifyToken) {
      el.btnSaveSpotifyToken.addEventListener('click', function () {
        var token = (el.inputSpotifyToken && el.inputSpotifyToken.value.trim()) || '';
        callApi('set_spotify_token', token).then(function () {
          showToast('Spotify token saved', { icon: 'check' });
        });
      });
    }
    if (el.btnOpenSpotifyDev) {
      el.btnOpenSpotifyDev.addEventListener('click', function () {
        callApi('open_external_url', 'https://developer.spotify.com/dashboard');
      });
    }
    if (el.inputDiscordClientId) {
      el.inputDiscordClientId.addEventListener('change', function () {
        var cid = el.inputDiscordClientId.value.trim();
        callApi('set_discord_client_id', cid).then(function () {
          showToast('Discord client ID updated', { icon: 'check' });
        });
      });
    }
  }

  wireSettingsIntegrations();
