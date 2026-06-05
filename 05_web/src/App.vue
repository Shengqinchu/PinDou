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
      <RouterLink class="brand" to="/" aria-label="PinDou 首页">
        <img class="brand__logo" src="/brand/logo.png" alt="" aria-hidden="true" />
        <span class="brand__text">PinDou 拼豆</span>
      </RouterLink>
      <nav class="app-nav" aria-label="主导航">
        <RouterLink class="nav-link nav-link--home" to="/">首页</RouterLink>
        <AccountMenu />
      </nav>
    </header>

    <main class="app-main" :class="{ 'app-main--auth': isAuthPage, 'app-main--editor': isEditorPage }">
      <RouterView />
    </main>
  </div>
</template>
