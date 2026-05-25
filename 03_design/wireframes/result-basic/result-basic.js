// result-basic/result-basic.js
// Animates the color-bar fills on load — bars start at width:0 in CSS and
// expand to their data-pct value over the standard ease curve. Keeps the
// page from feeling static the moment it appears.
(function () {
  'use strict';

  function animateBars() {
    document.querySelectorAll('.result__color-bar-fill').forEach((el) => {
      const pct = parseFloat(el.dataset.pct || '0');
      // Defer with setTimeout(0) rather than rAF — rAF can stall in
      // throttled / off-screen iframes and never fire, which leaves the
      // bars at width: 0. setTimeout still fires under throttling and the
      // CSS transition handles the visual easing either way.
      setTimeout(() => { el.style.width = pct + '%'; }, 0);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', animateBars);
  } else {
    animateBars();
  }
})();
