<script setup lang="ts">
import LiftTitle from '../components/LiftTitle.vue';
import { contentModule } from "../content-store";
const copyText = contentModule("pages-NotFound", copyTextDefault);

import copyTextDefault from "../content/pages-NotFound.json";
import { say } from "../state";

import { tr } from "../state";
</script>
<template>
  <section class="container page-intro">
    <div>
      <LiftTitle as="h1" :text="[say(copyText.this_little_bead_6335af),say(copyText.rolled_away_9759a2)]" emphasis-last/>
      <p>
        {{ say(copyText.we_could_not_find_that_page_let_05f3f9) }}
      </p>
      <RouterLink class="button button-primary" to="/">{{
        say(copyText.back_to_the_studio_9f318a)
      }}</RouterLink>
    </div>
  </section>
</template>
