// me/me.js — 客服二维码 sheet 打开 / 关闭
(function () {
  'use strict';

  const sheet = document.querySelector('.me__cs-sheet');
  if (!sheet) return;

  function open() {
    sheet.hidden = false;
    sheet.dataset.state = 'open';
  }
  function close() {
    sheet.hidden = true;
    sheet.dataset.state = 'closed';
  }

  document.querySelectorAll('[data-action="show-cs-qr"]').forEach((btn) => {
    btn.addEventListener('click', open);
  });

  sheet.querySelectorAll('[data-action="close-cs"]').forEach((el) => {
    el.addEventListener('click', close);
  });
})();
