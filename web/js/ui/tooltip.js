  // ---------------------------------------------------------------------------
  // Tooltip positioning (fixed coordinates, never clipped)
  // ---------------------------------------------------------------------------

  function positionTooltip(target) {
    if (!target) return;
    var rect = target.getBoundingClientRect();
    if (!rect.width && !rect.height) return;
    var x = clamp(rect.left + rect.width / 2, 136, Math.max(136, window.innerWidth - 136));
    var y = rect.bottom + 8;
    var above = y + 38 > window.innerHeight && rect.top > 44;
    if (above) {
      y = rect.top - 8;
      target.classList.add('tip-above');
    } else {
      target.classList.remove('tip-above');
    }
    target.style.setProperty('--tip-x', x + 'px');
    target.style.setProperty('--tip-y', y + 'px');
  }

  document.addEventListener('pointerover', function (event) {
    var target = event.target.closest && event.target.closest('[data-tooltip]');
    if (target) positionTooltip(target);
  });
  document.addEventListener('focusin', function (event) {
    var target = event.target.closest && event.target.closest('[data-tooltip]');
    if (target) positionTooltip(target);
  });

