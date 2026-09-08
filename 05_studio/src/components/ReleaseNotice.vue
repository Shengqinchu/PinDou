<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { tr } from "../state";
const current = __STUDIO_BUILD__;
const newer = ref(false);
function reload() {
  window.location.reload();
}
let timer: ReturnType<typeof setInterval>;
let checking = false;
let missingChunk = false;
function chunkFailed(event: Event) {
  event.preventDefault();
  missingChunk = true;
  newer.value = true;
}
async function check() {
  if (import.meta.env.DEV || checking || document.hidden) return;
  checking = true;
  try {
    const response = await fetch(import.meta.env.BASE_URL + "version.json", {
      cache: "no-store",
    });
    if (response.ok) {
      const data = await response.json();
      newer.value =
        missingChunk ||
        (typeof data.build === "string" && data.build !== current);
    }
  } catch {
    /* A version probe never interrupts the current task. */
  } finally {
    checking = false;
  }
}
onMounted(() => {
  document.addEventListener("visibilitychange", check);
  window.addEventListener("pageshow", check);
  window.addEventListener("vite:preloadError", chunkFailed);
  timer = setInterval(check, 60000);
  check();
});
onBeforeUnmount(() => {
  clearInterval(timer);
  document.removeEventListener("visibilitychange", check);
  window.removeEventListener("pageshow", check);
  window.removeEventListener("vite:preloadError", chunkFailed);
});
</script>
<template>
  <aside v-if="newer" class="vision-update" role="status">
    <span>{{
      tr(
        "页面有更新，方便时重新载入即可。",
        "An updated page is ready when you are.",
      )
    }}</span
    ><button class="text-link" @click="reload">
      {{ tr("重新载入", "Reload page") }}
    </button>
  </aside>
</template>
