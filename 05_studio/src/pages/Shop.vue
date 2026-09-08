<script setup lang="ts">
import copyText from "../content/pages-Shop.json";
import { say } from "../state";

import { PhArrowRight, PhFlower } from "@phosphor-icons/vue";
import { media, tr } from "../state";
</script>
<template>
  <section class="vision-coming container">
    <div class="vision-coming-copy">
      <PhFlower :size="40" weight="light" />
      <p class="vision-eyebrow">{{ say(copyText.the_little_shop_915927) }}</p>
      <h1>
        {{ say(copyText.little_things_01bed6) }}<br /><em>{{
          say(copyText.worth_waiting_for_23de2b)
        }}</em>
      </h1>
      <p>
        {{ say(copyText.still_in_the_making_coming_soon_2c6744) }}
      </p>
      <RouterLink class="text-link" to="/"
        >{{ say(copyText.back_to_the_studio_8a0eaa) }}<PhArrowRight
      /></RouterLink>
    </div>
    <img
      :src="media('studio-11')"
      :alt="say(copyText.a_collection_of_little_craft_fittings_in_c88f20)"
      width="1080"
      height="1440"
    />
  </section>
</template>
