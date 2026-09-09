<script setup lang="ts">
import { contentModule } from "../content-store";
const copyText = contentModule("pages-Journal", copyTextDefault);

import copyTextDefault from "../content/pages-Journal.json";
import { say } from "../state";

import { PhArrowUpRight, PhArrowRight } from "@phosphor-icons/vue";
import { socialUrl, tr } from "../state";
import { onMounted, onBeforeUnmount } from "vue";
import { journalPosts, refreshJournal, journalSource } from "../journal";
import journalMetaDefault from "../content/journal-collection.json";
const journalMeta=contentModule('journal-collection',journalMetaDefault);
import BrandMotif from "../components/BrandMotif.vue";
import FlagText from "../components/FlagText.vue";
const base = import.meta.env.BASE_URL;
let refresh: ReturnType<typeof setInterval>;
onMounted(() => { void refreshJournal(); refresh=setInterval(() => { if(document.visibilityState==='visible') void refreshJournal(); },60000); });
onBeforeUnmount(() => clearInterval(refresh));
</script>
<template>
  <section class="container page-intro journal-intro">
    <h1>
      {{ say(copyText.life_in_our_1d9155) }}<br /><em>{{
        say(copyText.little_studio_902113)
      }}</em>
    </h1>
    <div>
      <p>{{ say(copyText.new_pieces_on_the_wall_new_colours_0e0a4b) }}</p>
      <a class="text-link" :href="socialUrl" target="_blank" rel="noreferrer"
        >{{ say(copyText.more_stories_on_xiaohongshu_d10ec3) }}<PhArrowUpRight
      /></a>
    </div>
  </section>
  <section
    class="container journal-stories section-bottom"
    :aria-label="say(copyText.beadmaking_stories_by_xiaogou_shuangji_efb72f)"
  >
    <article
      v-for="(post, i) in journalPosts"
      :key="post.id"
      class="journal-story"
      :class="{ featured: i === 0 }"
    >
      <RouterLink :to="'/journal/' + post.id" class="journal-story-link">
        <div class="journal-story-cover">
          <img
            :src="journalSource(post.images[0].src)"
            :alt="tr(post.title, post.title_en)"
            :width="post.images[0].width"
            :height="post.images[0].height"
            :loading="i < 2 ? 'eager' : 'lazy'"
          />
        </div>
        <div class="journal-story-copy">
          <time class="journal-story-source" :datetime="post.date">{{ post.date.slice(5) }}</time>
          <h2><FlagText :text="tr(post.title, post.title_en)" /></h2>
          <p>
            <FlagText
              :text="
                tr(post.body,post.body_en)
                  .replace(/\[.*?R\]/g, '')
                  .slice(0, 100)
              "
            />…
          </p>
          <span class="journal-read"
            >{{ say(copyText.open_this_story_b4bd90) }}<PhArrowRight
          /></span>
        </div>
      </RouterLink>
    </article>
    <a
      class="journal-collection"
      :href="say(journalMeta.url)"
      target="_blank"
      rel="noreferrer"
      ><BrandMotif kind="heart" /><span>{{ say(journalMeta.title) }}</span
      ><span class="text-link"
        >{{ say(copyText.browse_the_full_collection_on_xiaohongshu_f762be)
        }}<PhArrowUpRight /></span
    ></a>
  </section>
</template>
