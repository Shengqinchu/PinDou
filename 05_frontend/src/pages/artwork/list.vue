<template>
  <MiniProgramLayout variant="home" title="我的作品" :scroll="true">
    <div class="works">
      <p class="works__placeholder">作品列表（Phase 2 待完善 — HTML 设计稿见 03_design/wireframes/works/）</p>
    </div>
  </MiniProgramLayout>
</template>

<script setup lang="ts">
import MiniProgramLayout from '../../components/MiniProgramLayout.vue';
</script>

<style lang="scss" scoped>
.works { padding: 32px 24px; }
.works__placeholder { font-size: 14px; color: #8C8C8C; text-align: center; padding-top: 40px; }
</style>
