  // ---------------------------------------------------------------------------
  // Utilities
  // ---------------------------------------------------------------------------

  function clamp(value, min, max) { return Math.min(max, Math.max(min, value)); }

  var RTL_REGEX = /[\u0590-\u08FF\uFB1D-\uFDFF\uFE70-\uFEFC]/;
  function isRtlText(value) {
    if (!value || typeof value !== 'string') return false;
    return RTL_REGEX.test(value);
  }

  function formatTime(seconds) {
    var value = Number(seconds);
    if (!isFinite(value) || value < 0) return '0:00';
    var mins = Math.floor(value / 60);
    var secs = Math.floor(value % 60);
    return mins + ':' + (secs < 10 ? '0' : '') + secs;
  }

  function formatSrtTime(seconds) {
    var value = Math.max(0, Number(seconds) || 0);
    var hrs = Math.floor(value / 3600);
    var mins = Math.floor((value % 3600) / 60);
    var secs = Math.floor(value % 60);
    var ms = Math.floor((value % 1) * 1000);
    return String(hrs).padStart(2, '0') + ':' + String(mins).padStart(2, '0') + ':' +
      String(secs).padStart(2, '0') + ',' + String(ms).padStart(3, '0');
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function getApi() { return (window.pywebview && window.pywebview.api) || null; }

  function hasApi(name) {
    var api = getApi();
    return !!(api && typeof api[name] === 'function');
  }

  function callApi(name) {
    var api = getApi();
    if (!api || typeof api[name] !== 'function') return Promise.resolve(undefined);
    var args = Array.prototype.slice.call(arguments, 1);
    try {
      return Promise.resolve(api[name].apply(api, args));
    } catch (err) {
      return Promise.resolve(undefined);
    }
  }

  function debounce(fn, wait) {
    var timer = null;
    return function () {
      var args = arguments;
      var self = this;
      clearTimeout(timer);
      timer = setTimeout(function () { fn.apply(self, args); }, wait);
    };
  }

  function icon(name, extraClass) {
    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'icon' + (extraClass ? ' ' + extraClass : ''));
    svg.setAttribute('aria-hidden', 'true');
    var use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
    use.setAttribute('href', '#icon-' + name);
    svg.appendChild(use);
    return svg;
  }

  function copyText(text) {
    var value = String(text == null ? '' : text);
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(value).catch(function () {
        return legacyCopy(value);
      });
    }
    return Promise.resolve(legacyCopy(value));
  }

  function legacyCopy(value) {
    try {
      var area = document.createElement('textarea');
      area.value = value;
      area.setAttribute('readonly', '');
      area.style.position = 'fixed';
      area.style.opacity = '0';
      document.body.appendChild(area);
      area.select();
      document.execCommand('copy');
      document.body.removeChild(area);
      return true;
    } catch (err) {
      return false;
    }
  }

  function prefersReducedMotion() {
    return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }

  function isOnline() { return navigator.onLine !== false; }

