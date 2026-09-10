<script setup lang="ts">
import LiftTitle from '../components/LiftTitle.vue';
import { contentModule } from "../content-store";
const copyText = contentModule("pages-Shop", copyTextDefault);

import copyTextDefault from "../content/pages-Shop.json";
import { say } from "../state";

import BrandMotif from "../components/BrandMotif.vue";
import { PhArrowRight, PhFlower } from "@phosphor-icons/vue";
import { media, tr } from "../state";
</script>
<template>
  <section class="vision-coming container">
    <div class="vision-coming-copy">
      <BrandMotif interactive />
      <p class="vision-eyebrow">{{ say(copyText.the_little_shop_915927) }}</p>
      <LiftTitle as="h1" :text="[say(copyText.little_things_01bed6),say(copyText.worth_waiting_for_23de2b)]" emphasis-last/>
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
