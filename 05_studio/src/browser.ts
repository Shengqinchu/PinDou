// The visual viewport, unlike 100vh/dvh alone, reflects WebView keyboards.
// No maximum-scale / user-scalable restrictions: customers can still zoom.
export const inWeChat = /MicroMessenger/i.test(navigator.userAgent);
export const handheldCashier =
  /Android|iPhone|iPad|iPod/i.test(navigator.userAgent) ||
  (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1) ||
  (inWeChat &&
    navigator.maxTouchPoints > 0 &&
    !/Windows|Macintosh/i.test(navigator.userAgent));

export function installViewport() {
  const root = document.documentElement;
  const viewport = window.visualViewport;
  let frame = 0;
  let fullHeight = window.innerHeight;
  let width = window.innerWidth;
  let priorVisibleHeight = window.innerHeight;
  let priorFocus: Element | null = null;
  function update() {
    frame = 0;
    // Do not resize/reposition a dialog to cancel the user's pinch zoom.
    if (viewport && Math.abs(viewport.scale - 1) > 0.05) return;
    const focused = document.activeElement?.matches(
      "input,textarea,select,[contenteditable=true]",
    );
    if (!focused || Math.abs(width - innerWidth) > 80) fullHeight = innerHeight;
    width = innerWidth;
    const visibleHeight = viewport?.height || innerHeight;
    root.style.setProperty(
      "--visible-height",
      `${Math.round(visibleHeight)}px`,
    );
    root.style.setProperty(
      "--visible-top",
      `${Math.round(viewport?.offsetTop || 0)}px`,
    );
    root.style.setProperty("--window-height", `${innerHeight}px`);
    root.classList.toggle(
      "keyboard-open",
      !!focused && fullHeight - visibleHeight > 120,
    );
    const active = document.activeElement;
    // Keyboard resizing must keep the field above the footer, not merely keep
    // the footer above the keyboard. Do not fight a user's ordinary scrolling.
    if (
      focused &&
      (visibleHeight !== priorVisibleHeight || active !== priorFocus)
    ) {
      const scroller = active?.closest<HTMLElement>(".drawer-body");
      if (scroller && active) {
        const field = active.getBoundingClientRect();
        const body = scroller.getBoundingClientRect();
        if (field.bottom > body.bottom - 14)
          scroller.scrollTop += field.bottom - body.bottom + 14;
        else if (field.top < body.top + 14)
          scroller.scrollTop -= body.top + 14 - field.top;
      }
    }
    priorVisibleHeight = visibleHeight;
    priorFocus = active;
  }
  function schedule() {
    if (!frame) frame = requestAnimationFrame(update);
  }
  update();
  root.classList.toggle("in-wechat", inWeChat);
  viewport?.addEventListener("resize", schedule);
  viewport?.addEventListener("scroll", schedule);
  window.addEventListener("resize", schedule);
  window.addEventListener("pageshow", schedule);
  document.addEventListener("focusin", schedule);
  document.addEventListener("focusout", schedule);
  return () => {
    cancelAnimationFrame(frame);
    viewport?.removeEventListener("resize", schedule);
    viewport?.removeEventListener("scroll", schedule);
    window.removeEventListener("resize", schedule);
    window.removeEventListener("pageshow", schedule);
    document.removeEventListener("focusin", schedule);
    document.removeEventListener("focusout", schedule);
  };
}

let locks = 0;
let lockedY = 0;
export const pageScrollY = () => (locks ? lockedY : window.scrollY);
let restore: (() => void) | undefined;
/** Fixed body also locks iOS/WKWebView. Each overlay owns one idempotent release. */
export function lockPageScroll() {
  if (locks++ === 0) {
    const body = document.body;
    const properties = [
      "position",
      "top",
      "left",
      "width",
      "overflow",
    ] as const;
    const prior = properties.map((property) => body.style[property]);
    const x = window.scrollX,
      y = window.scrollY;
    lockedY = y;
    // Snapshot before position:fixed removes the root scrollbar from layout.
    const contentWidth = document.documentElement.clientWidth;
    const scrollbarWidth = Math.max(0, innerWidth - contentWidth);
    let lockedWidth = innerWidth;
    const resizeLockedBody = () => {
      if (innerWidth === lockedWidth) return;
      lockedWidth = innerWidth;
      body.style.width = `${Math.max(0, innerWidth - scrollbarWidth)}px`;
    };
    window.addEventListener("resize", resizeLockedBody);
    body.style.position = "fixed";
    body.style.top = `${-y}px`;
    body.style.left = `${-x}px`;
    body.style.width = `${contentWidth}px`;
    body.style.overflow = "hidden";
    document.documentElement.classList.add("modal-open");
    restore = () => {
      window.removeEventListener("resize", resizeLockedBody);
      properties.forEach((property, i) => {
        body.style[property] = prior[i];
      });
      const root = document.documentElement;
      const behavior = root.style.scrollBehavior;
      root.style.scrollBehavior = "auto";
      window.scrollTo(x, y);
      root.style.scrollBehavior = behavior;
      root.classList.remove("modal-open");
    };
  }
  let released = false;
  return () => {
    if (released) return;
    released = true;
    if (--locks === 0) {
      restore?.();
      restore = undefined;
    }
  };
}
