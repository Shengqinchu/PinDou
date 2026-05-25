<template>
  <MiniProgramLayout title="用户授权与隐私" backUrl="/pages/index/index" :scroll="true">
    <div class="consent">
      <p class="consent__placeholder">隐私授权页（Phase 2 待完善 — HTML 设计稿见 03_design/wireframes/consent/）</p>
    </div>
  </MiniProgramLayout>
</template>

<script setup lang="ts">
import MiniProgramLayout from '../../components/MiniProgramLayout.vue';
</script>

<style lang="scss" scoped>
.consent { padding: 32px 24px; }
.consent__placeholder { font-size: 14px; color: #8C8C8C; text-align: center; padding-top: 40px; }
</style>
