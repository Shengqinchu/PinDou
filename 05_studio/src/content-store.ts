import { shallowRef } from "vue";
import defaults from "./media-assets.json";

export type MediaAsset = { src: string; width: number; height: number; srcset?: string };
function initialContent(): Record<string, Record<string, unknown>> {
  try { return JSON.parse(document.getElementById("studio-published-content")?.textContent || "{}").modules || {}; }
  catch { return {}; }
}
export const publishedModules = shallowRef<Record<string, Record<string, unknown>>>(initialContent());
export const previewModules = shallowRef<Record<string, Record<string, unknown>> | null>(null);
export function contentModule<T extends object>(name: string, original: T): T {
  return new Proxy(original, {
    get(target, key, receiver) {
      const override = (previewModules.value || publishedModules.value)[name];
      return typeof key === "string" && override && Object.prototype.hasOwnProperty.call(override, key)
        ? override[key]
        : Reflect.get(target, key, receiver);
    },
  });
}
export function contentValues<T extends object>(name: string, original: T): T {
  return new Proxy(original, { get(target,key,receiver) {
    const value=(previewModules.value || publishedModules.value)[name]?.[String(key)];
    return Array.isArray(value) ? value[0] : Reflect.get(target,key,receiver);
  }});
}
export function contentPhotos<T extends {image:string;zh:string;en:string}>(name:string, original:T[]):T[] {
  return new Proxy(original,{get(target,key,receiver){
    const item=Reflect.get(target,key,receiver);
    if(typeof key!=='string'||!/^\d+$/.test(key)||!item)return item;
    const value=(previewModules.value || publishedModules.value)[name]?.[item.image];
    return Array.isArray(value)?{...item,zh:value[0],en:value[1]}:item;
  }});
}
export function asset(name: string): MediaAsset {
  const override = (previewModules.value || publishedModules.value).media?.[name] as MediaAsset | undefined;
  return override || (defaults as Record<string, MediaAsset>)[name] || {
    src: `/studio-media/${name}.jpg`, width: 1080, height: 1440,
  };
}
let pending: Promise<void> | undefined;
export function refreshContent(): Promise<void> {
  if (pending) return pending;
  pending = fetch("/studio-api/content", { cache: "no-store", signal: typeof AbortSignal.timeout === "function" ? AbortSignal.timeout(3500) : undefined })
    .then(async response => {
      if (!response.ok) return;
      const data = await response.json();
      if (data.modules && typeof data.modules === "object") {
        publishedModules.value = data.modules;
      }
    }).catch(() => {}).finally(() => { pending = undefined; });
  return pending;
}
export function installContent() {
  if (!document.getElementById("studio-published-content")) void refreshContent();
  const refresh = () => { if (document.visibilityState === "visible") void refreshContent(); };
  document.addEventListener("visibilitychange", refresh);
  const timer = setInterval(refresh, 60000);
  const preview = new URLSearchParams(location.search).has("content-preview") && parent !== window;
  const receive = (event: MessageEvent) => {
    if (!preview || event.origin !== location.origin || event.source !== parent || event.data?.type !== "studio-content-preview") return;
    previewModules.value = event.data.modules;
  };
  const blockActions = (event: Event) => {
    if (preview && ((event.target as Element).closest("a,button") || event.type === "submit")) {
      event.preventDefault();event.stopImmediatePropagation();
    }
  };
  if (preview) {
    window.addEventListener("message", receive);
    document.addEventListener("click", blockActions, true);
    document.addEventListener("submit", blockActions, true);
    parent.postMessage({ type: "studio-preview-ready" }, location.origin);
  }
  return () => {
    clearInterval(timer);document.removeEventListener("visibilitychange", refresh);
    window.removeEventListener("message", receive);
    document.removeEventListener("click", blockActions, true);
    document.removeEventListener("submit", blockActions, true);
  };
}
