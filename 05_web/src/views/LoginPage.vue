<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router';

import AuthPanel from '../components/AuthPanel.vue';

const route = useRoute();
const router = useRouter();

async function handleSuccess(): Promise<void> {
  await router.replace(readRedirectPath());
}

function readRedirectPath(): string {
  const redirect = route.query.redirect;
  if (typeof redirect === 'string' && redirect.startsWith('/') && !redirect.startsWith('//')) {
    return redirect;
  }
  return '/upload';
}
</script>

<template>
  <section class="login-page">
    <AuthPanel @success="handleSuccess" />
  </section>
</template>

<style scoped>
.login-page {
  min-height: calc(100vh - var(--app-header-height));
  display: grid;
  place-items: center;
  padding: clamp(18px, 4vw, 44px);
}
</style>
