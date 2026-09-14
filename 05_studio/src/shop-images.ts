const widths = [320, 480, 800] as const;
const originalPattern = /^\/studio-api\/media\/([a-f0-9]{64}\.(?:jpg|png|webp))$/;
let foregroundLoads = 0;
const preparedImages = new Set<string>();
export const imagePrepared = (source: string) => preparedImages.has(source);
export const rememberImage = (source: string) => { preparedImages.add(source); };

export function imageWidth(cssWidth: number) {
  const pixels = Math.ceil(cssWidth * Math.min(window.devicePixelRatio || 1, 3));
  return widths.find(width => width >= pixels) || 800;
}
export function previewURL(source: string, width: number) {
  const match = originalPattern.exec(source);
  return match ? `/studio-api/media/previews/v1/${width}/${match[1]}` : source;
}
export function foregroundImage() {
  foregroundLoads++;
  let done = false;
  return () => { if (!done) { done = true; foregroundLoads--; } };
}

type Connection = { saveData?: boolean; effectiveType?: string };
type LowPriorityRequest = RequestInit & { priority?: 'low' };

/** Small, interruptible, public-image-only speculation. The HTTP cache is shared
 * with <img>; no service worker or customer data cache is needed.
 */
export function createImageWarmer() {
  const fetched = new Set<string>();
  const active = new Map<string, AbortController>();
  let queue: string[] = [], bytes = 0, reserved = 0, count = 0, disposed = false;
  let timer: ReturnType<typeof setTimeout> | undefined;
  const budget = 512 * 1024;
  const limited = () => {
    const connection = (navigator as Navigator & { connection?: Connection }).connection;
    return connection?.saveData || /(^|-)2g$|3g/.test(connection?.effectiveType || '');
  };
  const stop = () => { clearTimeout(timer); for (const controller of active.values()) controller.abort(); };
  const schedule = (delay = 500) => { clearTimeout(timer); if (!disposed && queue.length) timer = setTimeout(pump, delay); };
  async function fetchImage(url: string) {
    const controller = new AbortController();
    active.set(url, controller);
    let reservation = 0;
    try {
      const response = await fetch(url, { signal: controller.signal, priority: 'low', credentials: 'omit' } as LowPriorityRequest);
      const length = Number(response.headers.get('Content-Length'));
      // Reserve advertised bytes before reading so simultaneous requests share
      // one cap. Only our finite, same-origin image endpoint is eligible.
      if (!response.ok || !response.headers.get('Content-Type')?.startsWith('image/') || !length || length > budget - bytes - reserved) {
        controller.abort(); return;
      }
      reservation = length; reserved += length;
      const body = await response.arrayBuffer();
      bytes += body.byteLength; count++; fetched.add(url); rememberImage(url);
    } catch { /* A speculative failure must never affect visible images. */ }
    finally { reserved -= reservation; active.delete(url); schedule(); }
  }
  function pump() {
    if (disposed || limited() || document.hidden || count >= 8 || bytes >= budget) return;
    if (document.readyState !== 'complete' || foregroundLoads) { schedule(); return; }
    while (active.size < 2 && queue.length && count + active.size < 8) {
      const url = queue.shift()!;
      if (!fetched.has(url) && !active.has(url)) void fetchImage(url);
    }
  }
  function targets(sources: string[], width: number) {
    if (disposed) return;
    const urls = [...new Set(sources.filter(src => originalPattern.test(src)).map(src => previewURL(src, width)))];
    queue = urls.filter(url => !fetched.has(url));
    for (const [url, controller] of active) if (!urls.includes(url)) controller.abort();
    schedule();
  }
  function visibility() { if (document.hidden) stop(); else schedule(); }
  function interaction() { stop(); schedule(900); }
  document.addEventListener('visibilitychange', visibility);
  document.addEventListener('pointerdown', interaction, { passive: true });
  document.addEventListener('keydown', interaction);
  return {
    targets,
    dispose() {
      disposed = true; stop(); queue = [];
      document.removeEventListener('visibilitychange', visibility);
      document.removeEventListener('pointerdown', interaction);
      document.removeEventListener('keydown', interaction);
    },
  };
}
