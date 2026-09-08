<script setup lang="ts">
import copyText from "../content/pages-JournalEntry.json";
import { say } from "../state";

import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import { PhArrowLeft, PhArrowUpRight } from "@phosphor-icons/vue";
import journal from "../content/journal-posts.json";
import PhotoViewer from "../components/PhotoViewer.vue";
import { tr } from "../state";
const route = useRoute();
const post = computed(() =>
  journal.posts.find((p) => p.id === route.params.id),
);
const base = import.meta.env.BASE_URL;
const viewer = ref<InstanceType<typeof PhotoViewer>>();
const photographs = computed(() => post.value?.images.map((photo, i) => ({image: photo.src, src: base + photo.src, zh: post.value!.title + ' · ' + (i+1), en: post.value!.title + ' · ' + (i+1)})) || []);
// Decode platform markup; the original source stays archived verbatim.
const body = computed(() =>
  post.value?.body
    .replace(/\[话题\]#/g, "")
    .replace(/\[([^\]]+)R\]/g, "（$1）"),
);
</script>
<template>
  <article v-if="post" class="journal-entry container">
    <RouterLink class="text-link" to="/journal"
      ><PhArrowLeft />{{ say(copyText.back_to_the_journal_b75447) }}</RouterLink
    >
    <header>
      <p>{{ say(copyText.xiaogou_shuangji_from_xiaohongshu_f76c2b) }}</p>
      <h1>{{ post.title }}</h1>
    </header>
    <div class="journal-entry-layout">
      <div class="journal-entry-text">
        <p class="journal-original" lang="zh-CN">{{ body }}</p>
        <p v-if="post.kind === 'excerpt'" class="journal-excerpt-note">
          {{ say(copyText.an_excerpt_from_the_original_post_find_e242d1) }}
        </p>
        <p v-else class="journal-excerpt-note">
          {{ say(copyText.this_journal_preserves_the_original_post_see_7d2ccb)
          }}<RouterLink to="/details" class="text-link">{{
            say(copyText.studio_details_7c4089)
          }}</RouterLink>
        </p>
        <a
          class="text-link"
          :href="post.source"
          target="_blank"
          rel="noreferrer"
          >{{ say(copyText.read_on_xiaohongshu_0456f8) }}<PhArrowUpRight
        /></a>
      </div>
      <div class="journal-entry-photos">
        <figure v-for="(photo, i) in post.images" :key="photo.src">
          <button class="journal-image-button" @click="viewer?.open(i)">
          <img
            :src="base + photo.src"
            :alt="post.title + ' · ' + (i + 1)"
            :width="photo.width"
            :height="photo.height"
            :loading="i === 0 ? 'eager' : 'lazy'"
          />
          </button>
          <figcaption>{{ i + 1 }} / {{ post.images.length }}</figcaption>
        </figure>
      </div>
    </div>
  </article>
  <section v-else class="container page-intro">
    <h1>{{ say(copyText.this_story_is_not_here_1ceff6) }}</h1>
    <RouterLink class="text-link" to="/journal">{{
      say(copyText.back_to_the_journal_b75447)
    }}</RouterLink>
  </section>
  <PhotoViewer v-if="post" ref="viewer" :photos="photographs" />
</template>
