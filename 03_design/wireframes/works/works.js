// works/works.js — action sheet 打开 / 关闭 + 空态切换 demo
(function () {
  'use strict';

  const sheet = document.querySelector('.works__sheet');
  if (!sheet) return;

  function openSheet() {
    sheet.hidden = false;
    sheet.dataset.state = 'open';
  }
  function closeSheet() {
    sheet.hidden = true;
    sheet.dataset.state = 'closed';
  }

  document.querySelectorAll('[data-action="menu"]').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      openSheet();
    });
  });

  sheet.querySelectorAll('[data-action="close-menu"]').forEach((el) => {
    el.addEventListener('click', closeSheet);
  });

  // Demo: 分享 / 删除暂时只关闭 sheet。Phase 2 后端实现时接入真实接口。
  sheet.querySelectorAll('[data-action="share"], [data-action="delete"]').forEach((btn) => {
    btn.addEventListener('click', closeSheet);
  });
})();
