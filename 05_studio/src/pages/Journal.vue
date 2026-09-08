<script setup lang="ts">
import copyText from "../content/pages-Journal.json";
import { say } from "../state";

import { PhArrowUpRight, PhArrowRight } from "@phosphor-icons/vue";
import { socialUrl, tr } from "../state";
import journal from "../content/journal-posts.json";
import BrandMotif from "../components/BrandMotif.vue";
import FlagText from "../components/FlagText.vue";
const base = import.meta.env.BASE_URL;
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
      v-for="(post, i) in journal.posts"
      :key="post.id"
      class="journal-story"
      :class="{ featured: i === 0 }"
    >
      <RouterLink :to="'/journal/' + post.id" class="journal-story-link">
        <div class="journal-story-cover">
          <img
            :src="base + post.images[0].src"
            :alt="post.title"
            :width="post.images[0].width"
            :height="post.images[0].height"
            :loading="i < 2 ? 'eager' : 'lazy'"
          />
        </div>
        <div class="journal-story-copy">
          <span class="journal-story-source"
            >{{ say(copyText.xiaogou_shuangji_xiaohongshu_380bde)
            }}<span v-if="post.kind === 'excerpt'">{{
              say(copyText.excerpt_040d41)
            }}</span></span
          >
          <h2><FlagText :text="post.title" /></h2>
          <p>
            <FlagText
              :text="
                post.body
                  .replace(/\[.*?R\]/g, '')
                  .slice(0, post.kind === 'full' ? 90 : 60)
              "
            />{{ post.kind === "full" ? "…" : "" }}
          </p>
          <span class="journal-read"
            >{{ say(copyText.open_this_story_b4bd90) }}<PhArrowRight
          /></span>
        </div>
      </RouterLink>
    </article>
    <a
      class="journal-collection"
      :href="journal.collection_url"
      target="_blank"
      rel="noreferrer"
      ><BrandMotif kind="heart" /><span>{{ journal.collection_title }}</span
      ><span class="text-link"
        >{{ say(copyText.browse_the_full_collection_on_xiaohongshu_f762be)
        }}<PhArrowUpRight /></span
    ></a>
  </section>
</template>
