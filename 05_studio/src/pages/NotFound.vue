<script setup lang="ts">
import copyText from "../content/pages-NotFound.json";
import { say } from "../state";

import { tr } from "../state";
</script>
<template>
  <section class="container page-intro">
    <div>
      <h1>
        {{ say(copyText.this_little_bead_6335af) }}<br /><em>{{
          say(copyText.rolled_away_9759a2)
        }}</em>
      </h1>
      <p>
        {{ say(copyText.we_could_not_find_that_page_let_05f3f9) }}
      </p>
      <RouterLink class="button button-primary" to="/">{{
        say(copyText.back_to_the_studio_9f318a)
      }}</RouterLink>
    </div>
  </section>
</template>
