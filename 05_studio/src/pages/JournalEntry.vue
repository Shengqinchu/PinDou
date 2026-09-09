<script setup lang="ts">
import { contentModule } from "../content-store";
const copyText = contentModule("pages-JournalEntry", copyTextDefault);

import copyTextDefault from "../content/pages-JournalEntry.json";
import { say } from "../state";

import { computed, ref, onMounted } from "vue";
import { useRoute } from "vue-router";
import { PhArrowLeft, PhArrowUpRight } from "@phosphor-icons/vue";
import { journalPosts, refreshJournal, journalSource } from "../journal";
import PhotoViewer from "../components/PhotoViewer.vue";
import FlagText from "../components/FlagText.vue";
import { tr, locale } from "../state";
const route = useRoute();
const post = computed(() =>
  journalPosts.value.find((p) => p.id === route.params.id),
);
const loading=ref(true);
onMounted(async()=>{await refreshJournal();loading.value=false;});
const base = import.meta.env.BASE_URL;
const viewer = ref<InstanceType<typeof PhotoViewer>>();
const photographs = computed(
  () =>
    post.value?.images.map((photo, i) => ({
      image: photo.src,
      src: journalSource(photo.src),
      zh: post.value!.title + " · " + (i + 1),
      en: post.value!.title_en + " · " + (i + 1),
    })) || [],
);
// Decode platform markup; the original source stays archived verbatim.
const body = computed(() =>
  (post.value ? tr(post.value.body,post.value.body_en) : '')
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
      <p><time :datetime="post.date">{{ post.date.slice(5) }}</time> · {{ say(copyText.xiaogou_shuangji_from_xiaohongshu_f76c2b) }}</p>
      <h1><FlagText :text="tr(post.title,post.title_en)" /></h1>
    </header>
    <div class="journal-entry-layout">
      <div class="journal-entry-text">
        <p class="journal-original" :lang="locale==='zh'?'zh-CN':'en-CA'">
          <FlagText :text="body || ''" />
        </p>
        <p class="journal-excerpt-note">
          {{ say(copyText.this_journal_preserves_the_original_post_see_7d2ccb)
          }}<RouterLink to="/details" class="text-link">{{
            say(copyText.studio_details_7c4089)
          }}<PhArrowUpRight /></RouterLink>
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
              :src="journalSource(photo.src)"
              :alt="tr(post.title,post.title_en) + ' · ' + (i + 1)"
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
  <section v-else-if="!loading" class="container page-intro">
    <h1>{{ say(copyText.this_story_is_not_here_1ceff6) }}</h1>
    <RouterLink class="text-link" to="/journal">{{
      say(copyText.back_to_the_journal_b75447)
    }}<PhArrowUpRight /></RouterLink>
  </section>
  <PhotoViewer v-if="post" ref="viewer" :photos="photographs" />
</template>
