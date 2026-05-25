// cdk-redeem/cdk-redeem.js
// Input behaviour:
//   - Strip non-alphanumeric; uppercase the rest
//   - Cap at 18 characters of actual content
//   - Auto-format as "XXXXXX  XXXXXX  XXXXXX" (two spaces between groups)
//   - Submit button is disabled until length === 18
//   - On submit: any 18-char code "wins" in the prototype → success state
//     (Real backend will reject unknown codes via the same error path.)
(function () {
  'use strict';

  const MAX = 18;
  const GROUP = 6;

  const input    = document.querySelector('[data-role="cdk"]');
  const counter  = document.querySelector('[data-role="counter"]');
  const errorBox = document.querySelector('[data-role="error"]');
  const errorMsg = document.querySelector('[data-role="error-msg"]');
  const submit   = document.querySelector('[data-role="submit"]');
  const usedCode = document.querySelector('[data-role="used-code"]');
  const entry    = document.querySelector('[data-state="entry"]');
  const success  = document.querySelector('[data-state="success"]');
  if (!input || !submit) return;

  // ── helpers ───────────────────────────────────────────────────────
  function clean(s) {
    return String(s || '')
      .toUpperCase()
      .replace(/[^A-Z0-9]/g, '')
      .slice(0, MAX);
  }
  function format(raw) {
    // Insert two spaces between groups of GROUP chars.
    return raw.match(/.{1,6}/g)?.join('  ') || '';
  }
  function setError(msg) {
    if (!msg) {
      errorBox.hidden = true;
      input.classList.remove('cdk__input--error');
      return;
    }
    errorMsg.textContent = msg;
    errorBox.hidden = false;
    input.classList.add('cdk__input--error');
  }

  // ── input handler ─────────────────────────────────────────────────
  input.addEventListener('input', () => {
    const raw = clean(input.value);
    input.value = format(raw);
    counter.textContent = `${raw.length} / ${MAX}`;

    // Reset error styling on edit, mark valid at 18 chars
    setError(null);
    input.classList.toggle('cdk__input--valid', raw.length === MAX);
    submit.disabled = raw.length !== MAX;
  });

  // ── submit handler ────────────────────────────────────────────────
  submit.addEventListener('click', () => {
    const raw = clean(input.value);
    if (raw.length !== MAX) {
      setError('需要 18 位字母数字');
      return;
    }
    // success
    if (usedCode) usedCode.textContent = format(raw);
    entry.hidden = true;
    success.hidden = false;
  });

  // also support Enter key
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !submit.disabled) submit.click();
  });
})();
