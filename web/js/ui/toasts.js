  // ---------------------------------------------------------------------------
  // Toasts
  // ---------------------------------------------------------------------------

  function showToast(message, options) {
    var opts = options || {};
    var toast = document.createElement('div');
    toast.className = 'toast' + (opts.tone === 'danger' ? ' tone-danger' : '');
    toast.setAttribute('role', 'status');

    var iconWrap = document.createElement('span');
    iconWrap.className = 'toast-icon';
    iconWrap.appendChild(icon(opts.icon || (opts.tone === 'danger' ? 'alert' : 'check')));
    toast.appendChild(iconWrap);

    var copy = document.createElement('span');
    copy.className = 'toast-message';
    copy.textContent = String(message || '');
    toast.appendChild(copy);

    if (opts.actionLabel && typeof opts.onAction === 'function') {
      var action = document.createElement('button');
      action.type = 'button';
      action.className = 'toast-action';
      action.textContent = opts.actionLabel;
      action.addEventListener('click', function () {
        removeToast(toast);
        opts.onAction();
      });
      toast.appendChild(action);
    }

    var close = document.createElement('button');
    close.type = 'button';
    close.className = 'toast-close';
    close.setAttribute('aria-label', 'Dismiss notification');
    close.setAttribute('data-tooltip', 'Dismiss');
    close.appendChild(icon('close'));
    close.addEventListener('click', function () { removeToast(toast); });
    toast.appendChild(close);

    el.toastContainer.appendChild(toast);
    while (el.toastContainer.children.length > 3) {
      el.toastContainer.removeChild(el.toastContainer.firstElementChild);
    }

    var duration = opts.duration || (opts.actionLabel ? 6500 : 3000);
    var timer = setTimeout(function () { removeToast(toast); }, duration);
    toast.__timer = timer;
  }

  function removeToast(toast) {
    if (!toast || !toast.parentNode) return;
    clearTimeout(toast.__timer);
    toast.classList.add('is-leaving');
    setTimeout(function () {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, prefersReducedMotion() ? 0 : 180);
  }

