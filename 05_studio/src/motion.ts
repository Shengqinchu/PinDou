import { gsap } from "gsap";
import { CustomEase } from "gsap/CustomEase";
import { reducedMotion } from "./ui";

// One clock for each interaction family. CSS and GSAP share the actual curves.
// T-Check control timing is the baseline; narrative/panel clocks remain separate.
export const motion = {
  control: 0.3,
  state: 0.3,
  panel: 0.68,
  exit: 0.48,
  editorial: 1.12,
  controlCurve: "0.42, 0, 0.58, 1",
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
    "surface-ease": `cubic-bezier(${motion.controlCurve})`,
    "layout-duration": `${motion.panel}s`,
    "exit-duration": `${motion.exit}s`,
  }))
    root.style.setProperty(`--${key}`, value);

  // Native :active follows the actual pointer/key lifetime. No delayed visual latch.
  return () => {};
}

/** Animate a workspace in place, without remounting its state or form fields. */
export function arrive(
  element: Element,
  options: { stationary?: boolean } = {},
) {
  if (reducedMotion()) return;
  if (options.stationary)
    return gsap.fromTo(
      element,
      { opacity: 0.9 },
      {
        opacity: 1,
        duration: motion.state,
        ease: "studio-control",
        clearProps: "opacity",
      },
    );
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
