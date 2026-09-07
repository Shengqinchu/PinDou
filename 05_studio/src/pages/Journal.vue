<script setup lang="ts">
import { ref } from "vue";
import { PhArrowUpRight } from "@phosphor-icons/vue";
import PhotoViewer from "../components/PhotoViewer.vue";
import { gallery, media, socialUrl, tr } from "../state";
const viewer = ref<InstanceType<typeof PhotoViewer>>();
</script>
<template>
  <section class="container page-intro">
    <h1>
      {{ tr("小屋里的，", "Life in our") }}<br /><em>{{
        tr("那些小快乐。", "little studio.")
      }}</em>
    </h1>
    <div>
      <p>
        {{
          tr(
            "墙上的新作品、桌上的新颜色，以及每一个认真拼豆的下午。这里的照片，都是小狗拼豆铺的真实日常。",
            "New pieces on the wall, new colours on the table, and afternoons well spent. Real photographs from everyday life at PinDou Puppy.",
          )
        }}
      </p>
      <a class="text-link" :href="socialUrl" target="_blank" rel="noreferrer"
        >{{ tr("去小红书看更多日常", "More stories on Xiaohongshu")
        }}<PhArrowUpRight
      /></a>
    </div>
  </section>
  <section
    class="container journal-grid section-bottom"
    :aria-label="tr('工作室相册', 'Studio gallery')"
  >
    <button
      class="photo-tile"
      v-for="(photo, i) in gallery"
      :key="photo.image"
      @click="viewer?.open(i)"
    >
      <div class="photo-tile-image">
        <img
          :src="media(photo.image)"
          :alt="tr(photo.zh, photo.en)"
          width="1080"
          height="1440"
          :loading="i < 2 ? 'eager' : 'lazy'"
        /><span class="photo-expand"><PhArrowUpRight /></span>
      </div>
      <span>{{ tr(photo.zh, photo.en) }}</span>
    </button>
  </section>
  <PhotoViewer ref="viewer" :photos="gallery" />
</template>
