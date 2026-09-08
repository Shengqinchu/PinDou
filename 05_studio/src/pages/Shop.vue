<script setup lang="ts">
import { PhArrowRight, PhFlower } from "@phosphor-icons/vue";
import { media, tr } from "../state";
</script>
<template>
  <section class="vision-coming container">
    <div class="vision-coming-copy">
      <PhFlower :size="40" weight="light" />
      <p class="vision-eyebrow">{{ tr("拼豆小店", "THE LITTLE SHOP") }}</p>
      <h1>
        {{ tr("把小小的喜欢，", "Little things,") }}<br /><em>{{
          tr("慢慢准备好。", "worth waiting for.")
        }}</em>
      </h1>
      <p>
        {{ tr("尚在开发，敬请期待。", "Still in the making. Coming soon.") }}
      </p>
      <RouterLink class="text-link" to="/"
        >{{ tr("回首页逛逛", "Back to the studio") }}<PhArrowRight
      /></RouterLink>
    </div>
    <img
      :src="media('studio-11')"
      :alt="
        tr(
          '拼豆铺里分类收纳的手作配件',
          'A collection of little craft fittings in the studio',
        )
      "
      width="1080"
      height="1440"
    />
  </section>
</template>
