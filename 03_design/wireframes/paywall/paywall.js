// paywall/paywall.js — sheet state machine + plan selection.
//   1. Tapping a .paywall__plan tile selects it (visual active).
//   2. "加客服扫码付" swaps the sheet to the QR sub-state, populating
//      the order's "selected plan" line with whichever plan is active.
//   3. "返回选择套餐" swaps back.
(function () {
  'use strict';

  const PLAN_LABELS = {
    single:  '单次 · ¥9.9',
    monthly: '月卡 · ¥28',
    artisan: '人工精修 · ¥99 起',
  };

  const plans    = Array.from(document.querySelectorAll('.paywall__plan'));
  const sheetA   = document.querySelector('[data-state="plans"]');
  const sheetB   = document.querySelector('[data-state="qr"]');
  const planSlot = document.querySelector('[data-role="selected-plan"]');
  let selected = 'monthly';   // recommended default

  function setSelected(plan) {
    selected = plan;
    plans.forEach((el) => {
      el.classList.toggle('paywall__plan--active',
        el.dataset.plan === plan && plan !== 'monthly');
      // Don't decorate "active" on the recommended plan — it's always
      // already highlighted by the gradient border.
    });
  }

  plans.forEach((el) => {
    el.addEventListener('click', () => setSelected(el.dataset.plan));
  });

  function show(state) {
    if (state === 'qr') {
      if (planSlot) planSlot.textContent = PLAN_LABELS[selected] || PLAN_LABELS.monthly;
      sheetA.hidden = true;
      sheetB.hidden = false;
    } else {
      sheetA.hidden = false;
      sheetB.hidden = true;
    }
  }

  document.querySelectorAll('[data-action="show-qr"]').forEach((b) =>
    b.addEventListener('click', () => show('qr')));
  document.querySelectorAll('[data-action="back-to-plans"]').forEach((b) =>
    b.addEventListener('click', () => show('plans')));

  // Trigger the slide-in transition by briefly setting the off-screen state
  // and clearing it on the next tick. If JS doesn't run, sheets stay at their
  // CSS default (visible) — no off-screen stall.
  const visibleSheet = () =>
    sheetA && !sheetA.hidden ? sheetA :
    sheetB && !sheetB.hidden ? sheetB : null;
  const s = visibleSheet();
  if (s) {
    s.classList.add('paywall__sheet--enter-init');
    setTimeout(() => s.classList.remove('paywall__sheet--enter-init'), 16);
  }
})();
