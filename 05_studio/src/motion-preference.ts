export type MotionMode = "system" | "full" | "reduced";
const key = "puppy-studio-motion";
// Owner requirement (2026-09-09): the first visit includes the brand's motion,
// including private browsing and browsers that cannot persist site settings.
// Only an explicit visitor choice opts into reduced or system motion.
const defaultMode: MotionMode = "full";
const system = matchMedia("(prefers-reduced-motion: reduce)");
const listeners = new Set<() => void>();
const valid = (value: string | null): value is MotionMode =>
  value === "full" || value === "reduced" || value === "system";
function stored(): MotionMode {
  try {
    const value = localStorage.getItem(key);
    return valid(value) ? value : defaultMode;
  } catch {
    return defaultMode;
  }
}
let mode = stored();
const settingsListeners = new Set<() => void>();
export const getMotionMode = () => mode;
export const systemReducesMotion = () => system.matches;
export function onMotionSettingsChange(listener: () => void) {
  settingsListeners.add(listener); return () => { settingsListeners.delete(listener); };
}
export function setMotionMode(value: MotionMode) {
  if (!valid(value)) return;
  mode = value;
  // An in-page choice supersedes an older diagnostic link on the next reload.
  const url = new URL(location.href);
  if (url.searchParams.has('motion')) {
    url.searchParams.delete('motion');
    history.replaceState(history.state, '', url.pathname + url.search + url.hash);
  }
  try { localStorage.setItem(key,value); } catch {}
  window.dispatchEvent(new Event('studio-motion-change'));
}
// A deliberate per-site choice overrides the full-motion first-visit default.
const requested = new URLSearchParams(location.search).get("motion");
if (valid(requested)) {
  mode = requested;
  try {
    localStorage.setItem(key, mode);
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
    for (const listener of settingsListeners) listener();
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
  window.addEventListener('studio-motion-change',sync);
  window.addEventListener("storage", storage);
  return () => {
    system.removeEventListener("change", sync);
    window.removeEventListener('studio-motion-change',sync);
    window.removeEventListener("storage", storage);
  };
}
