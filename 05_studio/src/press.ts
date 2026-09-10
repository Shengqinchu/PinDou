// Complete a short tap visually without delaying its native click or form action.
// CSS handles hover/held press. A single, replaceable WAAPI effect handles release.
import { reducedMotion, onMotionPreferenceChange } from "./motion-preference";
const controls = [
  ".button",
  ".desk-button",
  ".icon-button",
  ".desk-icon-button",
  ".language-button",
  ".desk-language",
  ".reservation-desk-days > button",
  ".reservation-grid td > button",
  ".reservation-plans > label",
  ".photo-tile",
  ".journal-story-link",
  ".desk-metric",
  ".reservation-desk-metrics > button",
  ".reservation-desk-row",
  ".member-row",
  ".home-journal-card",
  ".account-methods > button",
  ".wallet-history-tabs > button",
  ".wallet-pagination > button",
  ".generator-workspace button",
  ".generator-workspace [role=button]",
  ".visit-guests button",
  ".visit-plans > label",
  ".visit-duo-offer",
  ".visit-dates button",
  ".visit-duration button",
  ".visit-times button",
  ".auth-method-choice",
].join(",");

type Frame = { transform: string; boxShadow: string };
type Press = { element: HTMLElement; at: number; x: number; y: number };

export function installPressFeedback(clock: {
  duration: number;
  ease: string;
}) {
  if (!Element.prototype.animate) return () => {};
  const effects = new Map<HTMLElement, Animation>();
  const pointers = new Map<number, Press>();
  let key: { element: HTMLElement; at: number; value: string } | undefined;
  const available = (element: HTMLElement) =>
    element.isConnected &&
    !element.matches(
      ":disabled,[aria-disabled=true],label:has(input:disabled)",
    ) &&
    !element.closest("[inert]");
  const target = (event: Event) =>
    event.target instanceof Element
      ? event.target.closest<HTMLElement>(controls)
      : null;
  const frame = (element: HTMLElement): Frame => {
    const style = getComputedStyle(element);
    return { transform: style.transform, boxShadow: style.boxShadow };
  };
  const state = (element: HTMLElement, which: "rest" | "press"): Frame => {
    const style = getComputedStyle(element);
    return {
      transform:
        style.getPropertyValue(`--tactile-${which}-transform`).trim() || "none",
      boxShadow:
        style.getPropertyValue(`--tactile-${which}-shadow`).trim() || "none",
    };
  };
  function cancel(element: HTMLElement) {
    effects.get(element)?.cancel();
    effects.delete(element);
  }
  function play(element: HTMLElement, frames: Keyframe[]) {
    cancel(element);
    const effect = element.animate(frames, {
      duration: clock.duration,
      easing: "linear",
      id: "studio-press-feedback",
    });
    effects.set(element, effect);
    effect.onfinish = () => {
      if (effects.get(element) === effect) effects.delete(element);
    };
  }
  function begin(element: HTMLElement) {
    if (!effects.has(element)) return;
    const current = frame(element);
    play(element, [
      { ...current, easing: clock.ease },
      state(element, "press"),
    ]);
  }
  function release(element: HTMLElement, at: number, completed: boolean) {
    if (reducedMotion() || !available(element)) return cancel(element);
    const short = completed && performance.now() - at < clock.duration * 0.6;
    if (!short && !effects.has(element)) return;
    const current = frame(element);
    const frames: Keyframe[] = [{ ...current, offset: 0, easing: clock.ease }];
    if (short)
      frames.push({
        ...state(element, "press"),
        offset: 0.28,
        easing: clock.ease,
      });
    frames.push({ ...state(element, "rest"), offset: 1 });
    play(element, frames);
  }
  function down(event: PointerEvent) {
    const element = target(event);
    if (
      event.button !== 0 ||
      !event.isPrimary ||
      reducedMotion() ||
      !element ||
      !available(element)
    )
      return;
    pointers.set(event.pointerId, {
      element,
      at: performance.now(),
      x: event.clientX,
      y: event.clientY,
    });
    begin(element);
  }
  function up(event: PointerEvent) {
    const press = pointers.get(event.pointerId);
    pointers.delete(event.pointerId);
    if (!press) return;
    const over = document.elementFromPoint(event.clientX, event.clientY);
    release(press.element, press.at, !!over && press.element.contains(over));
  }
  function move(event: PointerEvent) {
    const press = pointers.get(event.pointerId);
    if (
      !press ||
      Math.hypot(event.clientX - press.x, event.clientY - press.y) <= 12
    )
      return;
    pointers.delete(event.pointerId);
    release(press.element, press.at, false);
  }
  function pointerCancel(event: PointerEvent) {
    const press = pointers.get(event.pointerId);
    pointers.delete(event.pointerId);
    if (press) release(press.element, press.at, false);
  }
  function boundary(event: PointerEvent) {
    // Touch sends pointerout on every lift; it is not a hover destination change.
    if (event.pointerType === "touch") return;
    const element = target(event);
    if (
      !element ||
      !effects.has(element) ||
      (event.relatedTarget instanceof Node &&
        element.contains(event.relatedTarget))
    )
      return;
    if ([...pointers.values()].some((press) => press.element === element))
      return;
    // The destination may change while the release is running (hover -> idle).
    release(element, performance.now(), false);
  }
  function keyDown(event: KeyboardEvent) {
    if (event.repeat || ![" ", "Enter"].includes(event.key) || reducedMotion())
      return;
    const element = target(event);
    if (!element || !available(element)) return;
    key = { element, at: performance.now(), value: event.key };
    begin(element);
  }
  function keyUp(event: KeyboardEvent) {
    if (!key || key.value !== event.key) return;
    const press = key;
    key = undefined;
    release(
      press.element,
      press.at,
      !!document.activeElement &&
        press.element.contains(document.activeElement),
    );
  }
  function reset() {
    for (const element of effects.keys()) cancel(element);
    pointers.clear();
    key = undefined;
  }
  function hidden() {
    if (document.hidden) reset();
  }
  const observer = new MutationObserver(() => {
    for (const element of effects.keys())
      if (!available(element)) cancel(element);
  });
  observer.observe(document.documentElement, {
    subtree: true,
    childList: true,
    attributes: true,
    attributeFilter: ["disabled", "aria-disabled", "inert"],
  });
  document.addEventListener("pointerdown", down, {
    capture: true,
    passive: true,
  });
  document.addEventListener("pointerup", up, { capture: true, passive: true });
  document.addEventListener("pointermove", move, {
    capture: true,
    passive: true,
  });
  document.addEventListener("pointercancel", pointerCancel, {
    capture: true,
    passive: true,
  });
  document.addEventListener("pointerover", boundary, {
    capture: true,
    passive: true,
  });
  document.addEventListener("pointerout", boundary, {
    capture: true,
    passive: true,
  });
  document.addEventListener("keydown", keyDown, true);
  document.addEventListener("keyup", keyUp, true);
  document.addEventListener("visibilitychange", hidden);
  window.addEventListener("blur", reset);
  window.addEventListener("pagehide", reset);
  const stopPreference = onMotionPreferenceChange(reset);
  return () => {
    reset();
    observer.disconnect();
    document.removeEventListener("pointerdown", down, true);
    document.removeEventListener("pointerup", up, true);
    document.removeEventListener("pointermove", move, true);
    document.removeEventListener("pointercancel", pointerCancel, true);
    document.removeEventListener("pointerover", boundary, true);
    document.removeEventListener("pointerout", boundary, true);
    document.removeEventListener("keydown", keyDown, true);
    document.removeEventListener("keyup", keyUp, true);
    document.removeEventListener("visibilitychange", hidden);
    window.removeEventListener("blur", reset);
    window.removeEventListener("pagehide", reset);
    stopPreference();
  };
}
