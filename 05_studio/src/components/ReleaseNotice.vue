<script setup lang="ts">
import { contentModule } from "../content-store";
const copyText = contentModule("components-ReleaseNotice", copyTextDefault);

import copyTextDefault from "../content/components-ReleaseNotice.json";
import { say } from "../state";

import { onBeforeUnmount, onMounted, ref } from "vue";
import { tr } from "../state";
import { useRoute } from "vue-router";
const route = useRoute();
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
        route.path.startsWith("/manage")
          ? copyText.literal_0fa103ec
          : copyText.literal_c09c9616,
        route.path.startsWith("/manage")
          ? copyText.literal_68796c00
          : copyText.literal_cbd7655c,
      )
    }}</span
    ><button class="text-link" @click="reload">
      {{ say(copyText.reload_page_062f91) }}
    </button>
  </aside>
</template>
