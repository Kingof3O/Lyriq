  // ---------------------------------------------------------------------------
  // Spotify Queue Modal
  // ---------------------------------------------------------------------------

  var queueLoaded = false;

  function openQueue() {
    closeSettings();
    closeOverflow();
    if (el.historyModal) el.historyModal.hidden = true;
    if (el.vocabModal) el.vocabModal.hidden = true;
    if (el.queueModal) {
      el.queueModal.hidden = false;
      renderQueue();
      var m = el.queueModal.querySelector('.modal');
      if (m) m.focus();
    }
  }

  function closeQueue() {
    if (el.queueModal) el.queueModal.hidden = true;
  }

  function formatQueueDuration(seconds) {
    if (!seconds || seconds < 0) return '--:--';
    var mins = Math.floor(seconds / 60);
    var secs = Math.floor(seconds % 60);
    return mins + ':' + (secs < 10 ? '0' : '') + secs;
  }

  function renderQueue() {
    if (!el.queueList) return;
    el.queueList.replaceChildren(modalEmpty('music', 'Fetching Spotify queue…'));

    if (!hasApi('get_spotify_queue')) {
      el.queueList.replaceChildren(modalEmpty('alert', 'Queue API is not available in this build.'));
      return;
    }

    callApi('get_spotify_queue').then(function (res) {
      if (!res || !res.connected || !Array.isArray(res.items) || res.items.length === 0) {
        var msg = (res && res.message) || 'No upcoming songs in the Spotify queue.';
        var emptyWrap = document.createElement('div');
        emptyWrap.className = 'empty-state';
        emptyWrap.style.cssText = 'padding: 32px 16px; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 12px;';

        var p = document.createElement('p');
        p.className = 'empty-text';
        p.style.cssText = 'color: #94A3B8; font-size: 13px; max-width: 320px; line-height: 1.5; margin: 0;';
        p.textContent = msg;
        emptyWrap.appendChild(p);

        if (!res || !res.connected) {
          var cfgBtn = document.createElement('button');
          cfgBtn.className = 'btn btn-sm';
          cfgBtn.style.cssText = 'margin-top: 8px; font-weight: 500;';
          cfgBtn.innerHTML = '<svg class="icon"><use href="#icon-settings"></use></svg> Configure Spotify Token';
          cfgBtn.addEventListener('click', function () {
            closeQueue();
            openSettings('playback');
          });
          emptyWrap.appendChild(cfgBtn);
        }

        el.queueList.replaceChildren(emptyWrap);
        return;
      }

      var frag = document.createDocumentFragment();
      res.items.forEach(function (item, idx) {
        var row = document.createElement('div');
        row.className = 'history-item';
        row.style.cssText = 'display: flex; align-items: center; gap: 12px; padding: 10px 14px; border-radius: 8px; transition: background 0.15s ease; border-bottom: 1px solid rgba(255,255,255,0.04);';

        var num = document.createElement('span');
        num.style.cssText = 'color: #64748B; font-size: 11px; font-weight: 600; width: 18px; text-align: right; flex-shrink: 0;';
        num.textContent = (idx + 1);
        row.appendChild(num);

        var art = document.createElement('div');
        art.className = 'history-art';
        art.style.cssText = 'width: 38px; height: 38px; border-radius: 6px; overflow: hidden; background: rgba(255,255,255,0.06); flex-shrink: 0; display: flex; align-items: center; justify-content: center;';
        if (item.thumbnail) {
          var img = document.createElement('img');
          img.src = item.thumbnail;
          img.alt = '';
          img.style.cssText = 'width: 100%; height: 100%; object-fit: cover;';
          art.appendChild(img);
        } else {
          art.innerHTML = '<svg class="icon" style="width: 18px; height: 18px; opacity: 0.4;"><use href="#icon-disc"></use></svg>';
        }
        row.appendChild(art);

        var meta = document.createElement('div');
        meta.style.cssText = 'flex: 1; min-width: 0;';
        var t = document.createElement('div');
        t.style.cssText = 'color: #F8FAFC; font-size: 13px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;';
        t.textContent = item.title || 'Unknown Title';
        var a = document.createElement('div');
        a.style.cssText = 'color: #94A3B8; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 2px;';
        a.textContent = item.artist || 'Unknown Artist';
        meta.appendChild(t);
        meta.appendChild(a);
        row.appendChild(meta);

        if (item.duration_seconds) {
          var dur = document.createElement('span');
          dur.style.cssText = 'color: #64748B; font-size: 11px; flex-shrink: 0; font-variant-numeric: tabular-nums;';
          dur.textContent = formatQueueDuration(item.duration_seconds);
          row.appendChild(dur);
        }

        frag.appendChild(row);
      });

      el.queueList.replaceChildren(frag);
    }).catch(function (err) {
      el.queueList.replaceChildren(modalEmpty('alert', 'Error fetching queue: ' + (err.message || err)));
    });
  }

  if (el.btnQueueClose) el.btnQueueClose.addEventListener('click', closeQueue);
  if (el.btnQueueRefresh) el.btnQueueRefresh.addEventListener('click', renderQueue);
  if (el.queueModal) {
    el.queueModal.addEventListener('click', function (e) {
      if (e.target === el.queueModal) closeQueue();
    });
  }
