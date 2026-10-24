  // ---------------------------------------------------------------------------
  // Sleep timer
  // ---------------------------------------------------------------------------

  var sleepTimerDeadline = 0;
  var sleepTimerTicker = null;

  function setSleepTimer(minutes) {
    var value = Math.max(0, Number(minutes) || 0);
    clearInterval(sleepTimerTicker);
    sleepTimerTicker = null;
    if (sleepSelectInstance) sleepSelectInstance.setValue(String(value), false);

    if (value > 0) {
      sleepTimerDeadline = Date.now() + value * 60000;
      el.sleepTimerBadge.hidden = false;
      updateSleepTimerBadge();
      sleepTimerTicker = setInterval(updateSleepTimerBadge, 1000);
      showToast('Sleep timer set for ' + value + ' minutes', {
        icon: 'timer',
        actionLabel: 'Cancel',
        onAction: function () { setSleepTimer(0); },
        duration: 6000
      });
    } else {
      sleepTimerDeadline = 0;
      el.sleepTimerBadge.hidden = true;
      showToast('Sleep timer cancelled', { icon: 'timer' });
    }
    callApi('set_sleep_timer', value);
  }

  function updateSleepTimerBadge() {
    var remaining = Math.max(0, Math.floor((sleepTimerDeadline - Date.now()) / 1000));
    if (remaining <= 0) {
      clearInterval(sleepTimerTicker);
      sleepTimerTicker = null;
      sleepTimerDeadline = 0;
      el.sleepTimerBadge.hidden = true;
      if (sleepSelectInstance) sleepSelectInstance.setValue('0', false);
      return;
    }
    el.sleepTimerText.textContent = formatTime(remaining);
    el.sleepTimerBadge.setAttribute('aria-label', 'Sleep timer ' + formatTime(remaining) + '. Activate to cancel.');
  }

  function promptSleepTimerCancel() {
    if (sleepTimerDeadline <= 0) return;
    var remaining = Math.max(0, Math.floor((sleepTimerDeadline - Date.now()) / 1000));
    showToast('Sleep timer stops playback in ' + formatTime(remaining), {
      icon: 'timer',
      actionLabel: 'Cancel timer',
      onAction: function () { setSleepTimer(0); },
      duration: 7000
    });
  }

  window.onSleepTimerTriggered = function () {
    clearInterval(sleepTimerTicker);
    sleepTimerTicker = null;
    sleepTimerDeadline = 0;
    el.sleepTimerBadge.hidden = true;
    if (sleepSelectInstance) sleepSelectInstance.setValue('0', false);
    showToast('Sleep timer ended. Spotify paused.', { icon: 'timer' });
  };

