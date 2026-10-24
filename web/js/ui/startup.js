  // ---------------------------------------------------------------------------
  // Startup with Windows (optional backend support)
  // ---------------------------------------------------------------------------

  function refreshStartupState() {
    var startupSupported = hasApi('set_start_with_windows') || hasApi('get_startup_state');
    if (!startupSupported) {
      el.checkStartup.setAttribute('aria-checked', 'false');
      el.checkStartup.setAttribute('aria-disabled', 'true');
      el.startupHelp.textContent = 'Not available in this build yet.';
      return;
    }
    el.checkStartup.removeAttribute('aria-disabled');
    el.startupHelp.textContent = 'Launch the companion at sign-in.';
    if (!hasApi('get_startup_state')) return;
    callApi('get_startup_state').then(function (result) {
      var enabled = typeof result === 'boolean' ? result : !!(result && (result.enabled || result.start_with_windows));
      el.checkStartup.setAttribute('aria-checked', String(enabled));
    });
  }

  function toggleStartup() {
    var next = el.checkStartup.getAttribute('aria-checked') !== 'true';
    if (!hasApi('set_start_with_windows')) {
      showToast('Start with Windows is not available in this build.', { icon: 'window', tone: 'danger' });
      return;
    }
    var done = function (ok) {
      if (ok === false) {
        showToast('Windows rejected the startup change.', { icon: 'alert', tone: 'danger' });
        el.checkStartup.setAttribute('aria-checked', String(!next));
        return;
      }
      el.checkStartup.setAttribute('aria-checked', String(next));
      showToast(next ? 'Will start with Windows' : 'Will not start with Windows', { icon: 'window' });
    };
    try {
      var result = getApi().set_start_with_windows(next);
      if (result && typeof result.then === 'function') result.then(done).catch(function () { done(false); });
      else done(result);
    } catch (err) {
      done(false);
    }
  }

