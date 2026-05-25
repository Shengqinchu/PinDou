<template>
  <MiniProgramLayout variant="home" title="我的" :scroll="true">
    <div class="me">
      <p class="me__placeholder">个人中心（Phase 2 待完善 — HTML 设计稿见 03_design/wireframes/me/）</p>
    </div>
  </MiniProgramLayout>
</template>

<script setup lang="ts">
import MiniProgramLayout from '../../components/MiniProgramLayout.vue';
</script>

<style lang="scss" scoped>
.me { padding: 32px 24px; }
.me__placeholder { font-size: 14px; color: #8C8C8C; text-align: center; padding-top: 40px; }
</style>
