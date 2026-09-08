import { computed, shallowRef } from "vue";
export type JournalPhoto = { src: string; width: number; height: number; sha256?: string };
export type JournalPost = { id: string; title: string; title_en: string; body: string; body_en: string; date: string; source: string; kind: "full"; images: JournalPhoto[]; published_at?: number | null; body_sha256?: string };
const entries = shallowRef<JournalPost[]>([]);
export const journalPosts = computed(() => entries.value.filter(p => p.kind === "full" && p.date > "2026-06-24").sort((a,b) => b.date.localeCompare(a.date) || (b.published_at || 0) - (a.published_at || 0)));
export const journalSource = (src: string) => src.startsWith("/") ? src : `/${src}`;
let pending: Promise<void> | undefined;
export function refreshJournal(): Promise<void> {
  if (pending) return pending;
  pending = fetch("/studio-api/journal", { cache: "no-store", signal: typeof AbortSignal.timeout === "function" ? AbortSignal.timeout(5000) : undefined })
    .then(async response => { if (!response.ok) throw new Error(); const data=await response.json(); entries.value=data.posts; })
    .catch(async () => { if (!entries.value.length) { const fallback=await import("./content/journal-posts.json");entries.value=fallback.default.posts.filter(p=>p.kind==="full" && (p as {date?:string}).date) as unknown as JournalPost[]; } })
    .finally(() => {pending=undefined;});
  return pending;
}
