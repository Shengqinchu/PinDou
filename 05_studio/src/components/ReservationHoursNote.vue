<script setup lang="ts">
import { contentModule } from '../content-store';
import words from '../content/visit-flow.json';
import { say } from '../state';
const copy=contentModule('visit-flow',words);
</script>
<template><p class="reservation-overtime-note">{{say(copy.overtime_notice)}}</p></template>
<style>
.reservation-overtime-note{font-size:12px;line-height:1.7;color:var(--muted);margin:9px 3px 0;overflow-wrap:anywhere}
</style>
