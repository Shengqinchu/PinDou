<script setup lang="ts">
const beads = [
  [2, 0],
  [3, 0],
  [1, 1],
  [2, 1],
  [3, 1],
  [4, 1],
  [0, 2],
  [1, 2],
  [2, 2],
  [3, 2],
  [4, 2],
  [5, 2],
  [0, 3],
  [1, 3],
  [2, 3],
  [3, 3],
  [4, 3],
  [5, 3],
  [1, 4],
  [2, 4],
  [3, 4],
  [4, 4],
  [2, 5],
  [3, 5],
];
</script>
<template>
  <span class="bead-mark" aria-hidden="true"
    ><i
      v-for="([x, y], index) in beads"
      :key="index"
      :style="{
        '--x': x,
        '--y': y,
        '--origin-x': `${(x - 2.5) * 9}px`,
        '--origin-y': `${(y - 2.5) * 9}px`,
      }"
      :class="{ center: x >= 2 && x <= 3 && y >= 2 && y <= 3 }"
  /></span>
</template>

<style scoped>
.bead-mark {
  display: grid;
  flex-shrink: 0;
  grid-template: repeat(6, 7px) / repeat(6, 7px);
  gap: 2px;
  width: 52px;
  height: 52px;
  transform: rotate(-9deg);
}
.bead-mark i {
  grid-column: calc(var(--x) + 1);
  grid-row: calc(var(--y) + 1);
  border: 2px solid #a65d48;
  background: #e0b79d;
  border-radius: 50%;
  box-shadow: 0 1px 1px #75403136;
}
.bead-mark i.center {
  border-color: #c39a4e;
  background: #eddb95;
}
</style>
