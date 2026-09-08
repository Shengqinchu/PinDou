import { contentModule } from "./content-store";
const contentLabels = contentModule("data-ui-labels", contentLabelsDefault);
import contentLabelsDefault from "./content/data-ui-labels.json";
import { ref } from "vue";

export const notice = ref<{
  id: number;
  zh: string;
  en: string;
  kind: "success" | "error";
  action?: "cart";
}>();
let noticeTimer: ReturnType<typeof setTimeout>;
export function notify(
  zh: string,
  en: string,
  kind: "success" | "error" = "success",
  action?: "cart",
) {
  clearTimeout(noticeTimer);
  notice.value = { id: Date.now(), zh, en, kind, action };
  noticeTimer = setTimeout(
    () => (notice.value = undefined),
    kind === "error" ? 7000 : 4500,
  );
}
export function dismissNotice() {
  clearTimeout(noticeTimer);
  notice.value = undefined;
}
export { reducedMotion } from "./motion-preference";

export function eventLabel(event: string, zh: boolean) {
  const labels: Record<string, string[]> = contentLabels as Record<
    string,
    string[]
  >;
  return labels[event]?.[zh ? 0 : 1] || event;
}
