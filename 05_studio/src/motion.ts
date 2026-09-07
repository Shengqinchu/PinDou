import { gsap } from "gsap";
import { CustomEase } from "gsap/CustomEase";
import { reducedMotion } from "./ui";

// One clock for each interaction family. CSS and GSAP share the actual curves.
// T-Check's parent/child contract is retained; the studio has a slower cadence.
export const motion = {
  control: 0.48,
  state: 0.52,
  panel: 0.68,
  exit: 0.48,
  editorial: 1.12,
  controlCurve: "0.22, 0.1, 0.22, 1",
  travelCurve: "0.22, 0.68, 0, 1",
};
gsap.registerPlugin(CustomEase);
CustomEase.create("studio-control", motion.controlCurve);
CustomEase.create("studio-travel", motion.travelCurve);

export function installMotion() {
  const root = document.documentElement;
  for (const [key, value] of Object.entries({
    "control-duration": `${motion.control}s`,
    "control-ease": `cubic-bezier(${motion.controlCurve})`,
    "surface-duration": `${motion.state}s`,
    "surface-ease": `cubic-bezier(${motion.travelCurve})`,
    "layout-duration": `${motion.panel}s`,
    "exit-duration": `${motion.exit}s`,
  }))
    root.style.setProperty(`--${key}`, value);

  // A quick tap must still show the press. The click is never delayed. Release
  // continues from the current frame, using the same curve as the parent/icon.
  const selectors =
    ".button,.desk-button,.icon-button,.desk-icon-button,.plan-option,.time-chip,.date-chip,.desk-metric,.photo-tile";
  let pressed: HTMLElement | undefined;
  let began = 0;
  let pointer: number | undefined;
  let origin = { x: 0, y: 0 };
  let releaseTimer: ReturnType<typeof setTimeout> | undefined;
  function clear() {
    clearTimeout(releaseTimer);
    pressed?.removeAttribute("data-pressed");
    pressed = undefined;
    pointer = undefined;
  }
  function press(target: EventTarget | null) {
    clear();
    if (reducedMotion() || !(target instanceof Element)) return;
    const control = target.closest<HTMLElement>(selectors);
    if (
      !control ||
      control.matches(":disabled,[aria-disabled=true]") ||
      control.closest("[inert]")
    )
      return;
    pressed = control;
    began = performance.now();
    control.setAttribute("data-pressed", "");
  }
  function release() {
    releaseTimer = setTimeout(
      clear,
      Math.max(0, 180 - (performance.now() - began)),
    );
  }
  const down = (e: PointerEvent) => {
    if (e.button !== 0 || !e.isPrimary) return;
    press(e.target);
    pointer = e.pointerId;
    origin = { x: e.clientX, y: e.clientY };
  };
  const move = (e: PointerEvent) => {
    if (
      e.pointerId === pointer &&
      Math.hypot(e.clientX - origin.x, e.clientY - origin.y) > 10
    )
      clear();
  };
  const keyDown = (e: KeyboardEvent) => {
    if (
      !e.repeat &&
      (e.key === "Enter" || e.key === " ") &&
      (e.target as Element)?.matches("button,a[href]")
    )
      press(e.target);
  };
  const keyUp = (e: KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") release();
  };
  document.addEventListener("pointerdown", down, { passive: true });
  document.addEventListener("pointermove", move, { passive: true });
  document.addEventListener("pointerup", release, { passive: true });
  document.addEventListener("pointercancel", clear, { passive: true });
  document.addEventListener("keydown", keyDown);
  document.addEventListener("keyup", keyUp);
  window.addEventListener("blur", clear);
  return () => {
    clear();
    document.removeEventListener("pointerdown", down);
    document.removeEventListener("pointermove", move);
    document.removeEventListener("pointerup", release);
    document.removeEventListener("pointercancel", clear);
    document.removeEventListener("keydown", keyDown);
    document.removeEventListener("keyup", keyUp);
    window.removeEventListener("blur", clear);
  };
}

/** Animate a workspace in place, without remounting its state or form fields. */
export function arrive(element: Element) {
  if (reducedMotion()) return;
  return gsap.fromTo(
    element,
    { y: 14, opacity: 0.65 },
    {
      y: 0,
      opacity: 1,
      duration: motion.state,
      ease: "studio-travel",
      clearProps: "transform,opacity",
    },
  );
}

const leavingBoxes = new WeakMap<
  Element,
  { width: number; height: number; left: number; top: number }
>();
export function snapshotLeavingItems(container: Element | null) {
  // Capture the entire old grid before Vue starts removing individual cells.
  // Sampling in each before-leave hook alone sees already-reflowed siblings.
  for (const child of container?.children || []) {
    const item = child as HTMLElement;
    const box = item.getBoundingClientRect();
    leavingBoxes.set(item, {
      width: box.width,
      height: box.height,
      left: item.offsetLeft,
      top: item.offsetTop,
    });
  }
}
/** Keep a leaving grid card in its original cell while the remaining cards move. */
export function pinLeavingItem(element: Element) {
  const item = element as HTMLElement;
  const box = leavingBoxes.get(item) || {
    ...item.getBoundingClientRect().toJSON(),
    left: item.offsetLeft,
    top: item.offsetTop,
  };
  Object.assign(item.style, {
    width: `${box.width}px`,
    height: `${box.height}px`,
    left: `${box.left}px`,
    top: `${box.top}px`,
  });
}
export function clearLeavingItem(element: Element) {
  const style = (element as HTMLElement).style;
  for (const property of ["width", "height", "left", "top"])
    style.removeProperty(property);
}
