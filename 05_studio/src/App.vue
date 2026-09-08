<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { useRoute } from "vue-router";
import {
  PhArrowRight,
  PhArrowUpRight,
  PhFlower,
  PhList,
} from "@phosphor-icons/vue";
import { locale, socialUrl, tr, wechat } from "./state";
import { gsap } from "gsap";
import { arrive } from "./motion";
import StudioToast from "./components/StudioToast.vue";
import SlideOver from "./components/SlideOver.vue";
import ReleaseNotice from "./components/ReleaseNotice.vue";
const route = useRoute();
const isDesk = computed(() => route.path.startsWith("/manage"));
const menu = ref(false);
const main = ref<HTMLElement>();
let arrival: gsap.core.Tween | undefined;
const navigation = computed(() => [
  { path: "/", label: tr("首页", "Home") },
  { path: "/visit", label: tr("来拼豆吧", "Come create") },
  { path: "/shop", label: tr("拼豆小店", "Little shop") },
  { path: "/journal", label: tr("小狗日记", "Studio journal") },
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
    tr("跳到主要内容", "Skip to content")
  }}</a>
  <div v-if="!isDesk" class="vision-announcement">
    {{
      tr(
        "汉密尔顿的小小手作空间，请约好时间，欢迎来玩！",
        "A little creative space in Hamilton. Book a time and come make something!",
      )
    }}
  </div>
  <header v-if="!isDesk" class="vision-header">
    <RouterLink
      to="/"
      class="vision-brand"
      :aria-label="tr('小狗拼豆铺首页', 'Pindo Puppy home')"
    >
      <PhFlower :size="30" weight="light" aria-hidden="true" />
      <span>{{ tr("小狗拼豆铺", "Pindo Puppy") }}</span>
    </RouterLink>
    <nav
      class="vision-navigation"
      :aria-label="tr('主要导航', 'Main navigation')"
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
        :aria-label="tr('切换为英文', 'Switch to Chinese')"
      >
        {{ tr("英文", "中文") }}
      </button>
      <button
        class="icon-button"
        :aria-label="tr('网站菜单', 'Site menu')"
        :aria-expanded="menu"
        @click="menu = true"
      >
        <PhList :size="25" />
      </button>
    </div>
  </header>
  <SlideOver
    v-model="menu"
    :title="tr('慢慢逛，慢慢拼。', 'A little time to explore.')"
    :close-label="tr('关闭菜单', 'Close menu')"
  >
    <nav class="vision-menu" :aria-label="tr('网站导航', 'Site navigation')">
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
        >{{ tr("拼豆铺详细信息", "Studio details") }}<PhArrowUpRight :size="20"
      /></RouterLink>
    </nav>
    <div class="vision-menu-extra">
      <a href="/upload"
        >{{ tr("拼豆图纸生成器", "Pattern maker") }}<PhArrowUpRight
      /></a>
      <RouterLink to="/manage" @click="menu = false"
        >{{ tr("店主管理", "Studio desk") }}<PhArrowRight
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
        <RouterLink to="/"
          >{{ tr("小狗拼豆铺", "Pindo Puppy")
          }}<PhFlower :size="28" weight="light"
        /></RouterLink>
        <p>
          {{
            tr(
              "属于你，独一无二的拼豆体验",
              "A bead-making experience, uniquely yours.",
            )
          }}
        </p>
      </div>
      <div class="vision-footer-links">
        <span>{{ tr("来这里", "Come by") }}</span>
        <RouterLink to="/visit">{{
          tr("预约到店", "Book a visit")
        }}</RouterLink>
        <RouterLink to="/details">{{
          tr("拼豆铺详细信息", "Studio details")
        }}</RouterLink>
      </div>
      <div class="vision-footer-links">
        <span>{{ tr("保持联系", "Say hello") }}</span>
        <a :href="socialUrl" target="_blank" rel="noreferrer"
          >{{ tr("小红书 · 小狗双吉", "Xiaohongshu")
          }}<PhArrowUpRight :size="16"
        /></a>
        <span class="contact-id"
          >{{ tr("微信号：", "WeChat: ") }}{{ wechat }}</span
        >
      </div>
      <div class="vision-footer-links">
        <span>{{ tr("小小工具箱", "The toolbox") }}</span>
        <a href="/upload"
          >{{ tr("拼豆图纸生成器", "Pattern maker")
          }}<PhArrowUpRight :size="16"
        /></a>
        <a href="/tutorial"
          >{{ tr("图纸工具教程", "Pattern maker guide")
          }}<PhArrowUpRight :size="16"
        /></a>
      </div>
    </div>
  </footer>
  <ReleaseNotice />
  <StudioToast />
</template>
