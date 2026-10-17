<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';

import AccountMenu from './components/AccountMenu.vue';

const route = useRoute();
const isAuthPage = computed(() => route.name === 'login');
const isEditorPage = computed(() => route.name === 'editor');
</script>

<template>
  <div class="app-shell">
    <header v-if="!isEditorPage" class="app-header">
      <a class="brand" href="/" aria-label="PinDou 首页">
        <img class="brand__logo" src="/brand/logo.png" alt="" aria-hidden="true" />
        <span class="brand__text">PinDou 拼豆</span>
      </a>
      <nav class="app-nav" aria-label="主导航">
        <a class="nav-link nav-link--home" href="/">首页</a>
        <RouterLink class="nav-link nav-link--tutorial" to="/tutorial">教程</RouterLink>
        <AccountMenu />
      </nav>
    </header>

    <main class="app-main" :class="{ 'app-main--auth': isAuthPage, 'app-main--editor': isEditorPage }">
      <RouterView />
    </main>
  </div>
</template>
