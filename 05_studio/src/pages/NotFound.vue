<script setup lang="ts">
import { tr } from "../state";
</script>
<template>
  <section class="container page-intro">
    <div>
      <h1>
        {{ tr("这颗豆子，", "This little bead") }}<br /><em>{{
          tr("好像滚远了。", "rolled away.")
        }}</em>
      </h1>
      <p>
        {{
          tr(
            "没有找到这个页面。回小屋看看吧。",
            "We could not find that page. Let us take you back to the studio.",
          )
        }}
      </p>
      <RouterLink class="button button-primary" to="/">{{
        tr("回到小屋", "Back to the studio")
      }}</RouterLink>
    </div>
  </section>
</template>
