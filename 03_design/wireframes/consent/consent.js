// consent/consent.js — 两个 checkbox 全勾才能点同意
(function () {
  'use strict';

  const cta = document.querySelector('[data-action="accept"]');
  const checks = document.querySelectorAll('.consent__check-input');
  if (!cta || checks.length === 0) return;

  function refresh() {
    const allChecked = Array.from(checks).every((c) => c.checked);
    cta.disabled = !allChecked;
  }

  checks.forEach((c) => c.addEventListener('change', refresh));

  cta.addEventListener('click', () => {
    if (cta.disabled) return;
    // Phase 2 后端：写入用户协议同意时间 + 敏感信息单独同意时间
    // 这里 prototype 直接跳首页
    window.location.href = '../home/home.html';
  });
})();
