  // ---------------------------------------------------------------------------
  // Interaction wiring: scrubber bar
  // ---------------------------------------------------------------------------

  function wireScrubber() {
    var scrubValue = 0;
    var scrubbing = false;
    function scrubFromEvent(event) {
      if (AppState.duration <= 0) return 0;
      var rect = el.scrubTrack.getBoundingClientRect();
      var ratio = clamp((event.clientX - rect.left) / Math.max(1, rect.width), 0, 1);
      scrubValue = ratio * AppState.duration;
      renderPosition(scrubValue);
      return scrubValue;
    }
    el.scrubTrack.addEventListener('pointerdown', function (event) {
      if (AppState.duration <= 0) return;
      scrubbing = true;
      AppState.isScrubbing = true;
      stopFrame();
      el.scrubTrack.setPointerCapture && el.scrubTrack.setPointerCapture(event.pointerId);
      scrubFromEvent(event);
    });
    el.scrubTrack.addEventListener('pointermove', function (event) {
      if (!scrubbing) return;
      scrubFromEvent(event);
    });
    el.scrubTrack.addEventListener('pointerup', function (event) {
      if (!scrubbing) return;
      scrubbing = false;
      AppState.isScrubbing = false;
      scrubFromEvent(event);
      seekTo(scrubValue, true);
      if (AppState.isPlaying) ensureFrame();
    });
    el.scrubTrack.addEventListener('pointercancel', function () {
      scrubbing = false;
      AppState.isScrubbing = false;
      if (AppState.isPlaying) ensureFrame();
    });
    el.scrubTrack.addEventListener('keydown', function (event) {
      if (AppState.duration <= 0) return;
      var position = currentPositionSeconds();
      if (event.key === 'ArrowRight' || event.key === 'ArrowUp') {
        event.preventDefault();
        seekTo(position + 5, true);
      } else if (event.key === 'ArrowLeft' || event.key === 'ArrowDown') {
        event.preventDefault();
        seekTo(position - 5, true);
      } else if (event.key === 'Home') {
        event.preventDefault();
        seekTo(0, true);
      } else if (event.key === 'End') {
        event.preventDefault();
        seekTo(AppState.duration, true);
      }
    });

    if (el.squareScrubTrack) {
      function scrubFromSquare(e) {
        if (AppState.duration <= 0) return 0;
        var r = el.squareScrubTrack.getBoundingClientRect();
        var ratio = clamp((e.clientX - r.left) / Math.max(1, r.width), 0, 1);
        scrubValue = ratio * AppState.duration;
        renderPosition(scrubValue);
        return scrubValue;
      }
      el.squareScrubTrack.addEventListener('pointerdown', function (e) {
        if (AppState.duration <= 0) return;
        scrubbing = true;
        AppState.isScrubbing = true;
        stopFrame();
        el.squareScrubTrack.setPointerCapture && el.squareScrubTrack.setPointerCapture(e.pointerId);
        scrubFromSquare(e);
      });
      el.squareScrubTrack.addEventListener('pointermove', function (e) {
        if (!scrubbing) return;
        scrubFromSquare(e);
      });
      el.squareScrubTrack.addEventListener('pointerup', function (e) {
        if (!scrubbing) return;
        scrubbing = false;
        AppState.isScrubbing = false;
        scrubFromSquare(e);
        seekTo(scrubValue, true);
        if (AppState.isPlaying) ensureFrame();
      });
      el.squareScrubTrack.addEventListener('pointercancel', function () {
        scrubbing = false;
        AppState.isScrubbing = false;
        if (AppState.isPlaying) ensureFrame();
      });
    }
  }
