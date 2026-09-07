import { nextTick, onBeforeUnmount, type Ref } from "vue";
import { gsap } from "gsap";
import { lockPageScroll } from "./browser";
import { motion } from "./motion";
import { reducedMotion } from "./ui";

export function useStudioModal(
  dialog: Ref<HTMLDialogElement | undefined>,
  kind: "drawer" | "photo",
) {
  let animation: gsap.core.Timeline | undefined;
  let unlock: (() => void) | undefined;
  let revision = 0;
  let trigger: HTMLElement | undefined;
  function parts() {
    return {
      panel: dialog.value?.querySelector<HTMLElement>(".modal-panel"),
      shade: dialog.value?.querySelector<HTMLElement>(".modal-shade"),
    };
  }
  function away() {
    if (kind === "photo") return { x: 0, y: 24, scale: 0.975 };
    return matchMedia("(max-width: 600px) and (orientation: portrait)").matches
      ? { x: 0, y: "104%", scale: 1 }
      : { x: "104%", y: 0, scale: 1 };
  }
  async function open() {
    const version = ++revision;
    await nextTick();
    if (version !== revision || !dialog.value) return;
    const { panel, shade } = parts();
    if (!panel || !shade) return;
    animation?.kill();
    if (!dialog.value.open) {
      trigger =
        document.activeElement instanceof HTMLElement
          ? document.activeElement
          : undefined;
      unlock = lockPageScroll();
      dialog.value.showModal();
      gsap.set(panel, reducedMotion() ? { x: 0, y: 0, scale: 1 } : away());
      gsap.set(shade, { opacity: 0 });
      gsap.set(panel, { opacity: kind === "photo" ? 0 : 1 });
    }
    dialog.value.dataset.phase = "opening";
    animation = gsap
      .timeline({
        defaults: {
          duration: reducedMotion() ? 0 : motion.panel,
          ease: "studio-travel",
        },
        onComplete() {
          if (dialog.value) dialog.value.dataset.phase = "open";
        },
      })
      .to(
        panel,
        { x: 0, y: 0, scale: 1, opacity: 1, clearProps: "transform,opacity" },
        0,
      )
      .to(shade, { opacity: 1 }, 0);
  }
  function close() {
    revision++;
    animation?.kill();
    if (!dialog.value?.open) return;
    const { panel, shade } = parts();
    if (!panel || !shade) return;
    dialog.value.dataset.phase = "closing";
    animation = gsap
      .timeline({
        defaults: {
          duration: reducedMotion() ? 0 : motion.exit,
          ease: "studio-control",
        },
        onComplete() {
          dialog.value?.close();
          if (dialog.value) dialog.value.dataset.phase = "closed";
          unlock?.();
          unlock = undefined;
          if (trigger?.isConnected) trigger.focus({ preventScroll: true });
        },
      })
      .to(
        panel,
        reducedMotion()
          ? { opacity: 0 }
          : { ...away(), opacity: kind === "photo" ? 0 : 1 },
        0,
      )
      .to(shade, { opacity: 0 }, 0);
  }
  onBeforeUnmount(() => {
    revision++;
    animation?.kill();
    dialog.value?.close();
    unlock?.();
    unlock = undefined;
  });
  return { open, close };
}
