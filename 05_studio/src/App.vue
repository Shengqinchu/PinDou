<script setup lang="ts">
import copyText from "./content/App.json";
import { say } from "./state";

import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { useRoute } from "vue-router";
import {
  PhArrowRight,
  PhArrowUpRight,
  PhFlower,
  PhList,
} from "@phosphor-icons/vue";
import { locale, socialUrl, tr, wechat, phone, phoneHref } from "./state";
import { gsap } from "gsap";
import { arrive } from "./motion";
import StudioToast from "./components/StudioToast.vue";
import SlideOver from "./components/SlideOver.vue";
import ReleaseNotice from "./components/ReleaseNotice.vue";
import BrandMark from "./components/BrandMark.vue";
import BrandMotif from "./components/BrandMotif.vue";
const route = useRoute();
const isDesk = computed(() => route.path.startsWith("/manage"));
const menu = ref(false);
const main = ref<HTMLElement>();
let arrival: gsap.core.Tween | undefined;
const navigation = computed(() => [
  { path: "/", label: say(copyText.home_76c92b) },
  { path: "/visit", label: say(copyText.come_create_2eee81) },
  { path: "/shop", label: say(copyText.little_shop_c97261) },
  { path: "/journal", label: say(copyText.studio_journal_7b860e) },
]);
onBeforeUnmount(() => arrival?.kill());
watch(
  () => route.fullPath,
  async () => {
    menu.value = false;
    await nextTick();
    main.value?.focus({ preventScroll: true });
    if (!isDesk.value && route.path !== "/" && main.value?.firstElementChild) {
      arrival?.progress(1).kill();
      arrival = arrive(main.value.firstElementChild, { stationary: true });
    }
  },
);
</script>
<template>
  <a class="skip-link" href="#main">{{
    say(copyText.skip_to_content_1760ff)
  }}</a>
  <div v-if="!isDesk" class="vision-announcement">
    {{ say(copyText.a_little_creative_space_in_hamilton_book_5cf34e) }}
  </div>
  <header v-if="!isDesk" class="vision-header">
    <RouterLink
      to="/"
      class="vision-brand"
      :aria-label="say(copyText.pindo_puppy_home_69051e)"
    >
      <BrandMotif kind="puppy" /><BrandMark compact />
    </RouterLink>
    <nav
      class="vision-navigation"
      :aria-label="say(copyText.main_navigation_b48c67)"
    >
      <RouterLink
        v-for="item in navigation"
        :key="item.path"
        :to="item.path"
        :class="{ selected: route.path === item.path }"
        >{{ item.label }}</RouterLink
      >
    </nav>
    <div class="vision-header-actions">
      <button
        class="language-button"
        @click="locale = locale === 'zh' ? 'en' : 'zh'"
        :aria-label="say(copyText.switch_to_chinese_6c04c2)"
      >
        {{ say(copyText.label_dd0e77) }}
      </button>
      <button
        class="icon-button"
        :aria-label="say(copyText.site_menu_40ed87)"
        :aria-expanded="menu"
        @click="menu = true"
      >
        <PhList :size="25" />
      </button>
    </div>
  </header>
  <SlideOver
    v-model="menu"
    :title="say(copyText.a_little_time_to_explore_7313f5)"
    :close-label="say(copyText.close_menu_d36a12)"
  >
    <nav class="vision-menu" :aria-label="say(copyText.site_navigation_d091f4)">
      <RouterLink
        v-for="(item, index) in navigation"
        :key="item.path"
        :to="item.path"
        @click="menu = false"
      >
        <span class="vision-menu-number">{{
          String(index + 1).padStart(2, "0")
        }}</span
        ><span>{{ item.label }}</span
        ><PhArrowRight :size="20" />
      </RouterLink>
      <RouterLink to="/details" @click="menu = false"
        >{{ say(copyText.studio_details_7c4089) }}<PhArrowUpRight :size="20"
      /></RouterLink>
    </nav>
    <div class="vision-menu-extra">
      <a href="/upload"
        >{{ say(copyText.pattern_maker_7db57b) }}<PhArrowUpRight
      /></a>
      <RouterLink to="/manage" @click="menu = false"
        >{{ say(copyText.studio_desk_4f230e) }}<PhArrowRight
      /></RouterLink>
    </div>
  </SlideOver>
  <main
    ref="main"
    id="main"
    tabindex="-1"
    :class="{ 'studio-admin-main': isDesk }"
  >
    <RouterView />
  </main>
  <footer v-if="!isDesk" class="vision-footer">
    <div class="vision-footer-inner container">
      <div class="vision-footer-brand">
        <RouterLink to="/"><BrandMark /></RouterLink>
        <p>
          {{ say(copyText.a_beadmaking_experience_uniquely_yours_cf90ad) }}
        </p>
      </div>
      <div class="vision-footer-links">
        <span>{{ say(copyText.come_by_6b27fe) }}</span>
        <RouterLink to="/visit">{{
          say(copyText.book_a_visit_8c72a6)
        }}</RouterLink>
        <RouterLink to="/details">{{
          say(copyText.studio_details_7c4089)
        }}</RouterLink>
      </div>
      <div class="vision-footer-links">
        <span>{{ say(copyText.say_hello_bdf90f) }}</span>
        <a :href="socialUrl" target="_blank" rel="noreferrer"
          >{{ say(copyText.xiaohongshu_e1e6c0) }}<PhArrowUpRight :size="16"
        /></a>
        <span class="contact-id"
          >{{ say(copyText.wechat_b2cc69) }}{{ wechat }}</span
        ><a :href="phoneHref">{{ phone }}</a>
      </div>
      <div class="vision-footer-links">
        <span>{{ say(copyText.the_toolbox_df33f0) }}</span>
        <a href="/upload"
          >{{ say(copyText.pattern_maker_7db57b) }}<PhArrowUpRight :size="16"
        /></a>
        <a href="/tutorial"
          >{{ say(copyText.pattern_maker_guide_c1f795)
          }}<PhArrowUpRight :size="16"
        /></a>
      </div>
    </div>
  </footer>
  <ReleaseNotice />
  <StudioToast />
</template>
