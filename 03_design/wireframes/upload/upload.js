// upload/upload.js — toggle between empty + selected states.
// Real upload (camera / album) is out of scope for the design prototype; both
// entry buttons just switch the page into the selected state.
(function () {
  'use strict';

  const empty    = document.querySelector('[data-state="empty"]');
  const selected = document.querySelector('[data-state="selected"]');
  if (!empty || !selected) return;

  function show(state) {
    if (state === 'selected') {
      empty.hidden = true;
      selected.hidden = false;
    } else {
      empty.hidden = false;
      selected.hidden = true;
    }
  }

  document.querySelectorAll('[data-action="pick"]').forEach((btn) => {
    btn.addEventListener('click', () => show('selected'));
  });

  document.querySelectorAll('[data-action="retry"]').forEach((btn) => {
    btn.addEventListener('click', () => show('empty'));
  });
})();
