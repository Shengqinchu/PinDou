<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const isAuthPage = computed(() => route.name === 'login');
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <RouterLink class="brand" to="/" aria-label="PinDou 首页">
        <img class="brand__logo" src="/brand/logo.png" alt="" aria-hidden="true" />
        <span class="brand__text">PinDou 拼豆</span>
      </RouterLink>
      <nav class="app-nav" aria-label="主导航">
        <RouterLink to="/">首页</RouterLink>
        <RouterLink to="/works">作品集</RouterLink>
        <RouterLink to="/me">我的</RouterLink>
      </nav>
    </header>

    <main class="app-main" :class="{ 'app-main--auth': isAuthPage }">
      <RouterView />
    </main>
  </div>
</template>
