import { reducedMotion } from "./ui";

// Owner saves are often triggered from a sticky bar or drawer footer far from
// where feedback renders, and Chrome's validation bubble fades within seconds.

/** Visible name of a form control, taken from its label. */
export function fieldName(field: HTMLElement) {
  const label =
    field.closest("label") ||
    (field.id ? document.querySelector(`label[for="${CSS.escape(field.id)}"]`) : null);
  for (const node of label?.childNodes || []) {
    if (node === field) continue;
    if (node instanceof Element && (node.matches("input,select,textarea,small") || node.contains(field))) continue;
    const text = node.textContent?.trim();
    if (text) return text;
  }
  return field.getAttribute("aria-label") || field.getAttribute("placeholder") || "";
}

/** "Field · browser message" for the control that blocked a submit. */
export function invalidFieldMessage(event: Event) {
  const field = event.target as HTMLInputElement;
  return [fieldName(field), field.validationMessage].filter(Boolean).join(" · ");
}

/**
 * Scroll alerts that answer the owner's own action into view when they appear
 * off screen. Background polling updates never move the page.
 */
export function revealAlerts(root: Node = document.body) {
  const shown = new WeakMap<Element, string>();
  let acted = 0;
  const act = (event: Event) => {
    if (event.type !== "keydown" || (event as KeyboardEvent).key === "Enter") acted = Date.now();
  };
  function reveal(alert: Element) {
    const text = alert.textContent?.trim() || "";
    if (!text || shown.get(alert) === text) return;
    shown.set(alert, text);
    if (Date.now() - acted > 30000 || !(alert as HTMLElement).offsetParent) return;
    // Leave the page behind an open drawer alone; its scroll is locked.
    if (!alert.closest("dialog[open]") && document.querySelector("dialog[open]")) return;
    const box = alert.getBoundingClientRect();
    const area = alert.closest(".drawer-body")?.getBoundingClientRect() || { top: 0, bottom: innerHeight };
    if (box.top >= area.top && box.bottom <= area.bottom) return;
    alert.scrollIntoView({ block: "nearest", behavior: reducedMotion() ? "auto" : "smooth" });
  }
  const observer = new MutationObserver((records) => {
    const alerts = new Set<Element>();
    for (const record of records) {
      const target = record.target instanceof Element ? record.target : record.target.parentElement;
      const owner = target?.closest('[role="alert"]');
      if (owner) alerts.add(owner);
      for (const node of record.addedNodes) {
        if (!(node instanceof Element)) continue;
        if (node.matches('[role="alert"]')) alerts.add(node);
        node.querySelectorAll('[role="alert"]').forEach((alert) => alerts.add(alert));
      }
    }
    if (alerts.size) requestAnimationFrame(() => alerts.forEach(reveal));
  });
  observer.observe(root, { childList: true, subtree: true, characterData: true });
  document.addEventListener("click", act, true);
  document.addEventListener("submit", act, true);
  document.addEventListener("keydown", act, true);
  return () => {
    observer.disconnect();
    document.removeEventListener("click", act, true);
    document.removeEventListener("submit", act, true);
    document.removeEventListener("keydown", act, true);
  };
}
