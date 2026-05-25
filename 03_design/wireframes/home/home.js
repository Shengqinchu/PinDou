// home/home.js — carousel + dot navigation for the home banner.
(function () {
  'use strict';

  const SLIDE_W = 327;        // matches .home__banner width in CSS
  const GAP     = 12;
  const PADDING = 24;
  const INTERVAL = 4000;

  const track = document.querySelector('[data-role="track"]');
  const dots  = Array.from(document.querySelectorAll('[data-role="dots"] .home__dot'));
  if (!track || dots.length === 0) return;

  let idx = 0;
  let timer = null;

  function render() {
    track.style.transform =
      `translateX(${PADDING - idx * (SLIDE_W + GAP)}px)`;
    dots.forEach((d, i) => d.classList.toggle('home__dot--active', i === idx));
  }

  function next() {
    idx = (idx + 1) % dots.length;
    render();
  }

  function goTo(i) {
    idx = i;
    render();
    restart();
  }

  function start() {
    timer = setInterval(next, INTERVAL);
  }
  function stop() {
    if (timer) clearInterval(timer);
    timer = null;
  }
  function restart() {
    stop();
    start();
  }

  dots.forEach((d) => {
    d.addEventListener('click', () => {
      goTo(parseInt(d.dataset.index, 10));
    });
  });

  // Pause auto-advance while user is interacting with the carousel
  track.addEventListener('pointerdown', stop);
  track.addEventListener('pointerup', start);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) stop(); else start();
  });

  render();
  start();
})();
