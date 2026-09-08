type MotionMode = "system" | "full" | "reduced";
const key = "puppy-studio-motion";
const system = matchMedia("(prefers-reduced-motion: reduce)");
const listeners = new Set<() => void>();
const valid = (value: string | null): value is MotionMode =>
  value === "full" || value === "reduced" || value === "system";
function stored(): MotionMode {
  try {
    const value = localStorage.getItem(key);
    return valid(value) ? value : "system";
  } catch {
    return "system";
  }
}
let mode = stored();
// A deliberate per-site choice. Ordinary visits continue to honor the OS.
const requested = new URLSearchParams(location.search).get("motion");
if (valid(requested)) {
  mode = requested;
  try {
    if (mode === "system") localStorage.removeItem(key);
    else localStorage.setItem(key, mode);
  } catch {
    // This page still honors the explicit choice without persistent storage.
  }
}
export const reducedMotion = () =>
  mode === "reduced" || (mode === "system" && system.matches);

export function onMotionPreferenceChange(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function installMotionPreference() {
  let previous = reducedMotion();
  function sync() {
    const reduced = reducedMotion();
    const root = document.documentElement;
    root.dataset.motion = reduced ? "reduced" : "full";
    root.dataset.motionSource = mode;
    root.dataset.systemMotion = system.matches ? "reduced" : "full";
    root.dataset.studioBuild = __STUDIO_BUILD__;
    if (previous !== reduced) {
      previous = reduced;
      for (const listener of listeners) listener();
    }
  }
  function storage(event: StorageEvent) {
    if (event.key !== key && event.key !== null) return;
    mode = stored();
    sync();
  }
  sync();
  system.addEventListener("change", sync);
  window.addEventListener("storage", storage);
  return () => {
    system.removeEventListener("change", sync);
    window.removeEventListener("storage", storage);
  };
}
