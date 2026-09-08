<script setup lang="ts">
withDefaults(defineProps<{ kind?: "puppy" | "star" | "heart" | "bone" }>(), {
  kind: "puppy",
});
const base = import.meta.env.BASE_URL;
</script>
<template>
  <span class="puppy-motif" :class="kind" aria-hidden="true"
    ><img
      :src="`${base}studio-brand/logo-zh.jpg`"
      alt=""
      width="1267"
      height="1267"
  /></span>
</template>
<style scoped>
:where(.puppy-motif) {
  position: relative;
  display: inline-block;
  width: 80px;
  aspect-ratio: 360/205;
  overflow: hidden;
  mix-blend-mode: multiply;
  flex-shrink: 0;
}
.puppy-motif img {
  position: absolute;
  width: 351.94%;
  max-width: none;
  top: -225%;
  left: -67%;
  height: auto;
}
:where(.star) {
  width: 48px;
  aspect-ratio: 190/190;
}
.star img {
  width: 666.84%;
  top: -282%;
  left: -21%;
}
:where(.heart) {
  width: 42px;
  aspect-ratio: 126/108;
}
.heart img {
  width: 1005.55%;
  top: -603.7%;
  left: -896.8%;
}
:where(.bone) {
  width: 75px;
  aspect-ratio: 277/175;
}
.bone img {
  width: 457.4%;
  top: -309%;
  left: -224%;
}
</style>
