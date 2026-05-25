// shared/components.js
// Mounts the WeChat mini-program frame chrome (status bar + ⋯× capsule + page
// header) into any element with class .frame. The page only declares the
// frame's data attributes; this module fills in the rest so each .html stays
// short and the chrome is consistent across pages.
//
// Markup contract — page HTML writes:
//
//   <div class="frame" data-variant="home" data-title="PinDou 拼豆图纸">
//     <main class="frame__body">
//       ...page content...
//     </main>
//   </div>
//
// or, for inner pages:
//
//   <div class="frame" data-variant="inner" data-title="上传你的照片"
//        data-back="../home/home.html">
//     <main class="frame__body">...</main>
//   </div>
//
// data attributes:
//   data-variant   'home' (logo+title left) | 'inner' (back+centered title)
//   data-title     header text
//   data-back      href the back arrow navigates to (inner variant only)

(function () {
  'use strict';

  // ── Inline SVG snippets used by the chrome ──────────────────────────
  const SVG_SIGNAL = `
    <svg width="17" height="11" viewBox="0 0 17 11" aria-hidden="true">
      <rect x="0"    y="7"   width="3" height="4"   rx="0.5" fill="currentColor"/>
      <rect x="4.5"  y="5"   width="3" height="6"   rx="0.5" fill="currentColor"/>
      <rect x="9"    y="2.5" width="3" height="8.5" rx="0.5" fill="currentColor"/>
      <rect x="13.5" y="0"   width="3" height="11"  rx="0.5" fill="currentColor"/>
    </svg>`;

  const SVG_WIFI = `
    <svg width="15" height="11" viewBox="0 0 15 11" aria-hidden="true">
      <path d="M7.5 2.8C9.6 2.8 11.5 3.6 12.8 5L13.8 4C12.2 2.3 9.9 1.2 7.5 1.2 5.1 1.2 2.8 2.3 1.2 4L2.2 5C3.5 3.6 5.4 2.8 7.5 2.8Z" fill="currentColor"/>
      <path d="M7.5 6C8.7 6 9.8 6.5 10.6 7.3L11.6 6.3C10.5 5.2 9 4.4 7.5 4.4 6 4.4 4.5 5.2 3.4 6.3L4.4 7.3C5.2 6.5 6.3 6 7.5 6Z" fill="currentColor"/>
      <circle cx="7.5" cy="9.5" r="1.3" fill="currentColor"/>
    </svg>`;

  const SVG_BATTERY = `
    <svg width="25" height="12" viewBox="0 0 25 12" aria-hidden="true">
      <rect x="0.5" y="0.5" width="21" height="11" rx="2.8" stroke="currentColor" stroke-opacity="0.4" fill="none"/>
      <rect x="2" y="2" width="18" height="8" rx="1.5" fill="currentColor"/>
      <path d="M22.7 4.3v3.4c.8-.2 1.3-.9 1.3-1.7 0-.8-.5-1.5-1.3-1.7Z" fill="currentColor" fill-opacity="0.4"/>
    </svg>`;

  const SVG_DOTS = `
    <svg width="20" height="6" viewBox="0 0 20 6" aria-hidden="true">
      <circle cx="3"  cy="3" r="1.6" fill="currentColor"/>
      <circle cx="10" cy="3" r="1.6" fill="currentColor"/>
      <circle cx="17" cy="3" r="1.6" fill="currentColor"/>
    </svg>`;

  const SVG_CLOSE = `
    <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
      <path d="M1 1l10 10M11 1L1 11" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
    </svg>`;

  const SVG_BACK = `
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
         stroke="currentColor" stroke-width="2"
         stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M15 18l-6-6 6-6"/>
    </svg>`;

  // ── Builders ────────────────────────────────────────────────────────
  function buildStatusBar() {
    return (
      `<div class="frame__status">` +
        `<span class="frame__time">9:41</span>` +
        `<span class="frame__indicators">${SVG_SIGNAL}${SVG_WIFI}${SVG_BATTERY}</span>` +
      `</div>`
    );
  }

  function buildCapsule() {
    return (
      `<span class="frame__capsule" aria-hidden="true">` +
        `<span class="frame__capsule-btn">${SVG_DOTS}</span>` +
        `<span class="frame__capsule-divider"></span>` +
        `<span class="frame__capsule-btn">${SVG_CLOSE}</span>` +
      `</span>`
    );
  }

  function buildHeader(variant, title, back) {
    if (variant === 'home') {
      return (
        `<header class="frame__header frame__header--home">` +
          `<span class="frame__logo"><span class="frame__logo-dot"></span><span>${escapeHtml(title)}</span></span>` +
          `<span class="frame__right">${buildCapsule()}</span>` +
        `</header>`
      );
    }
    const backAttr = back ? `href="${back}"` : `href="#" data-action="history-back"`;
    return (
      `<header class="frame__header frame__header--inner">` +
        `<a class="frame__back" ${backAttr} aria-label="返回">${SVG_BACK}</a>` +
        `<span class="frame__title">${escapeHtml(title)}</span>` +
        `<span class="frame__right">${buildCapsule()}</span>` +
      `</header>`
    );
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  // ── Public: mount frame chrome ──────────────────────────────────────
  function mountFrame(root) {
    root = root || document.querySelector('.frame');
    if (!root) return;
    const variant = root.dataset.variant || 'inner';
    const title   = root.dataset.title   || '';
    const back    = root.dataset.back    || '';
    root.insertAdjacentHTML('afterbegin',
      buildStatusBar() + buildHeader(variant, title, back)
    );
    // wire "history-back" fallback for inner pages that didn't set data-back
    root.querySelectorAll('[data-action="history-back"]').forEach((el) => {
      el.addEventListener('click', (e) => { e.preventDefault(); history.back(); });
    });
  }

  // Auto-mount on load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => mountFrame());
  } else {
    mountFrame();
  }

  // Export for manual mounting / multi-frame demos
  window.PinDou = window.PinDou || {};
  window.PinDou.mountFrame = mountFrame;
})();
