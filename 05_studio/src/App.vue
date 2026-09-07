<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { useRoute } from "vue-router";
import {
  PhArrowUpRight,
  PhFlower,
  PhList,
  PhShoppingBagOpen,
  PhX,
} from "@phosphor-icons/vue";
import { locale, socialUrl, tr, wechat } from "./state";
import { bagCount as cartCount } from "./commerce";
import { gsap } from "gsap";
import { arrive } from "./motion";
import StudioToast from "./components/StudioToast.vue";

const route = useRoute();
const isDesk = computed(() => route.path.startsWith("/manage"));
const menu = ref(false);
const main = ref<HTMLElement>();
let arrival: gsap.core.Tween | undefined;
onBeforeUnmount(() => arrival?.kill());
watch(
  () => route.fullPath,
  async () => {
    menu.value = false;
    await nextTick();
    main.value?.focus({ preventScroll: true });
    if (!isDesk.value && route.path !== "/" && main.value?.firstElementChild) {
      arrival?.kill();
      arrival = arrive(main.value.firstElementChild);
    }
  },
);
</script>

<template>
  <a class="skip-link" href="#main">{{
    tr("跳到主要内容", "Skip to content")
  }}</a>
  <div v-if="!isDesk" class="announcement">
    {{
      tr(
        "Hamilton 的小小手作空间 · 提前约好，慢慢拼豆",
        "A little creative space in Hamilton · Visits by appointment",
      )
    }}
  </div>
  <header v-if="!isDesk" class="site-header">
    <RouterLink
      to="/"
      class="wordmark"
      :aria-label="tr('小狗拼豆铺首页', 'PinDou Puppy home')"
    >
      <PhFlower :size="32" weight="light" aria-hidden="true" />
      <span
        >pindou puppy<span class="wordmark-sub">{{
          tr("小狗拼豆铺", "a little creative studio")
        }}</span></span
      >
    </RouterLink>
    <nav class="desktop-nav" :aria-label="tr('主要导航', 'Main navigation')">
      <RouterLink to="/#space">{{ tr("我们的空间", "The studio") }}</RouterLink>
      <RouterLink to="/visit">{{ tr("来拼豆吧", "Come create") }}</RouterLink>
      <RouterLink to="/shop">{{ tr("拼豆小店", "Little shop") }}</RouterLink>
      <RouterLink to="/journal">{{
        tr("小狗日记", "Studio journal")
      }}</RouterLink>
    </nav>
    <div class="header-actions">
      <button
        class="language-button"
        @click="locale = locale === 'zh' ? 'en' : 'zh'"
        :aria-label="tr('Switch to English', '切换为中文')"
      >
        {{ locale === "zh" ? "EN" : "中文" }}
      </button>
      <RouterLink
        class="bag-button"
        to="/cart"
        :aria-label="
          tr(`购物车，${cartCount} 件`, `Your bag, ${cartCount} items`)
        "
        ><PhShoppingBagOpen :size="23" weight="light" /><Transition
          name="bag-count"
          ><span
            v-if="cartCount"
            :key="cartCount"
            class="bag-count"
            aria-hidden="true"
            >{{ cartCount }}</span
          ></Transition
        ></RouterLink
      >
      <button
        class="menu-button"
        :aria-expanded="menu"
        aria-controls="mobile-nav"
        @click="menu = !menu"
        :aria-label="tr('导航菜单', 'Navigation menu')"
      >
        <PhX v-if="menu" :size="25" /><PhList v-else :size="25" />
      </button>
    </div>
    <Transition name="mobile-menu"
      ><nav
        v-if="menu"
        id="mobile-nav"
        class="mobile-nav"
        :aria-label="tr('手机导航', 'Mobile navigation')"
        @keydown.esc="menu = false"
        :inert="!menu"
      >
        <RouterLink to="/#space">{{
          tr("我们的空间", "The studio")
        }}</RouterLink
        ><RouterLink to="/visit">{{ tr("来拼豆吧", "Come create") }}</RouterLink
        ><RouterLink to="/shop">{{ tr("拼豆小店", "Little shop") }}</RouterLink
        ><RouterLink to="/journal">{{
          tr("小狗日记", "Studio journal")
        }}</RouterLink
        ><a href="/upload"
          >{{ tr("拼豆图纸工具", "Pattern maker") }} <PhArrowUpRight
        /></a></nav
    ></Transition>
  </header>

  <main
    ref="main"
    id="main"
    tabindex="-1"
    :class="{ 'studio-admin-main': isDesk }"
  >
    <div :key="route.path">
      <RouterView />
    </div>
  </main>

  <footer v-if="!isDesk" class="site-footer">
    <div class="footer-top">
      <div>
        <RouterLink class="footer-brand" to="/">pindou puppy.</RouterLink>
        <p>
          {{
            tr(
              "把喜欢的小事，慢慢做成生活。",
              "A little colour. A little time. Something of your own.",
            )
          }}
        </p>
      </div>
      <div class="footer-column">
        <span>{{ tr("来这里", "Come by") }}</span
        ><RouterLink to="/visit">{{
          tr("预约到店", "Plan a visit")
        }}</RouterLink
        ><RouterLink to="/#find-us"
          >8 Hughson St N<br />Hamilton, Ontario</RouterLink
        >
      </div>
      <div class="footer-column">
        <span>{{ tr("保持联系", "Say hello") }}</span
        ><a :href="socialUrl" target="_blank" rel="noreferrer"
          >{{ tr("小红书 · 小狗双吉", "Xiaohongshu · 小狗双吉") }}
          <PhArrowUpRight /></a
        ><span class="footer-contact"
          >{{ tr("微信", "WeChat") }}: {{ wechat }}</span
        >
      </div>
      <div class="footer-column">
        <span>{{ tr("小小工具箱", "The toolbox") }}</span
        ><a href="/upload"
          >{{ tr("拼豆图纸生成器", "Pattern maker") }} <PhArrowUpRight /></a
        ><a href="/tutorial"
          >{{ tr("图纸工具教程", "Pattern maker guide") }} <PhArrowUpRight
        /></a>
      </div>
    </div>
    <div class="footer-bottom">
      <span>© {{ new Date().getFullYear() }} PinDou Puppy Studio</span
      ><span>Made slowly. Made happily.</span
      ><RouterLink to="/manage">{{ tr("店主入口", "Studio desk") }}</RouterLink>
    </div>
  </footer>
  <StudioToast />
</template>
