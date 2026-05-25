// preview-loading/preview-loading.js
// Drives the progress ring + percent + ETA + rotating status copy.
//
// Timing model:
//   0–30 s:   ring fills 0 → 100 %; status copy rotates through STATUS_LINES
//             every 8 s.
//   30 s+:    ring sits at 99 %; status copy switches to the "还有 30 秒哦,
//             你的作品 99% 完成" reassurance line in pink.
(function () {
  'use strict';

  const STATUS_LINES = [
    'AI 正在画你的拼豆…',
    '正在挑选最美色号…',
    '马上就好啦~',
  ];
  const REASSURE = '还有 30 秒哦，你的作品 99% 完成';

  const TOTAL = 30;                    // seconds for the ring to "fill"
  const CIRC  = 2 * Math.PI * 94;      // matches r=94 in the SVG
  const TICK  = 200;                   // ms per tick — smooth enough
  const ROTATE_MS = 8000;              // status copy cadence

  const ringEl    = document.querySelector('[data-role="ring-progress"]');
  const pctEl     = document.querySelector('[data-role="percent"]');
  const etaEl     = document.querySelector('[data-role="eta"]');
  const statusEl  = document.querySelector('[data-role="status"]');
  if (!ringEl || !pctEl || !etaEl || !statusEl) return;

  const start = performance.now();
  let lineIdx = 0;

  function renderStatus(overTime) {
    statusEl.classList.remove('loading__status-line--reassure');
    if (overTime) {
      statusEl.textContent = REASSURE;
      statusEl.classList.add('loading__status-line--reassure');
    } else {
      statusEl.textContent = STATUS_LINES[lineIdx];
    }
    // restart fade-in animation
    statusEl.style.animation = 'none';
    void statusEl.offsetWidth;
    statusEl.style.animation = '';
  }

  function tick() {
    const elapsed = (performance.now() - start) / 1000;
    const overTime = elapsed > TOTAL;
    const pct = overTime ? 99 : Math.min(100, (elapsed / TOTAL) * 100);

    ringEl.style.strokeDasharray = `${(CIRC * pct / 100).toFixed(2)} ${CIRC.toFixed(2)}`;
    pctEl.textContent = Math.floor(pct) + '%';
    etaEl.textContent = overTime
      ? '稍等一下下'
      : '约 ' + Math.max(1, Math.ceil(TOTAL - elapsed)) + ' 秒';

    if (overTime && !statusEl.classList.contains('loading__status-line--reassure')) {
      renderStatus(true);
    }
  }

  // Status rotation — only fires while still under 30 s
  setInterval(() => {
    const elapsed = (performance.now() - start) / 1000;
    if (elapsed > TOTAL) return;
    lineIdx = (lineIdx + 1) % STATUS_LINES.length;
    renderStatus(false);
  }, ROTATE_MS);

  setInterval(tick, TICK);
  tick();
})();
