// error/error.js — 三个 variant 切换 + fallback 自动重试进度条
(function () {
  'use strict';

  const buttons = document.querySelectorAll('.error__variant-btn');
  const sections = document.querySelectorAll('.error[data-state]');
  if (buttons.length === 0 || sections.length === 0) return;

  function show(variant) {
    sections.forEach((s) => { s.hidden = s.dataset.state !== variant; });
    buttons.forEach((b) => {
      b.classList.toggle('error__variant-btn--active', b.dataset.variant === variant);
    });
    // fallback 状态：触发进度条 0 → 100%
    if (variant === 'fallback') {
      const fill = document.querySelector('[data-role="retry-fill"]');
      if (fill) {
        fill.style.width = '0';
        // 用 setTimeout(..., 0) 确保 transition 触发（throttled iframe 下 rAF 不可靠）
        setTimeout(() => { fill.style.width = '100%'; }, 0);
      }
    }
  }

  buttons.forEach((b) => {
    b.addEventListener('click', () => show(b.dataset.variant));
  });

  // 真实小程序通过 URL query ?variant=network|fallback|quota 指定，prototype 同样支持
  const params = new URLSearchParams(window.location.search);
  const initial = params.get('variant');
  if (initial && ['network', 'fallback', 'quota'].includes(initial)) {
    show(initial);
  }
})();
