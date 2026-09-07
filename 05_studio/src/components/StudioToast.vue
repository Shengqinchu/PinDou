<script setup lang="ts">
import {
  PhCheck,
  PhWarningCircle,
  PhArrowRight,
  PhX,
} from "@phosphor-icons/vue";
import { notice, dismissNotice } from "../ui";
import { tr } from "../state";
</script>
<template>
  <div class="notice-region" aria-live="polite" aria-atomic="true">
    <Transition name="notice"
      ><div
        v-if="notice"
        :key="notice.id"
        :class="['studio-notice', notice.kind]"
      >
        <span class="notice-seal"
          ><PhCheck
            v-if="notice.kind === 'success'"
            :size="18" /><PhWarningCircle v-else :size="20"
        /></span>
        <span>{{ tr(notice.zh, notice.en) }}</span>
        <RouterLink
          v-if="notice.action === 'cart'"
          to="/cart"
          class="notice-action"
          @click="dismissNotice"
          >{{ tr("去看看", "View bag") }}<PhArrowRight
        /></RouterLink>
        <button
          class="icon-button"
          :aria-label="tr('关闭提示', 'Dismiss notification')"
          @click="dismissNotice"
        >
          <PhX :size="17" />
        </button></div
    ></Transition>
  </div>
</template>
