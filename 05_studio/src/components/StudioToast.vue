<script setup lang="ts">
import { contentModule } from "../content-store";
const copyText = contentModule("components-StudioToast", copyTextDefault);

import copyTextDefault from "../content/components-StudioToast.json";
import { say } from "../state";

import {
  PhCheck,
  PhWarningCircle,
  PhArrowRight,
  PhX,
} from "@phosphor-icons/vue";
import { notice, dismissNotice } from "../ui";
import { tr } from "../state";
import { useRoute } from "vue-router";
const route = useRoute();
</script>
<template>
  <div class="notice-region" aria-live="polite" aria-atomic="true">
    <Transition name="notice"
      ><div
        v-if="notice"
        :key="notice.id"
        :class="['studio-notice', notice.kind, {'shop-cart-notice':notice.action==='shop-cart'}]"
      >
        <span class="notice-seal"
          ><PhCheck
            v-if="notice.kind === 'success'"
            :size="18" /><PhWarningCircle v-else :size="20"
        /></span>
        <span>{{ tr(notice.zh, notice.en) }}</span>
        <RouterLink
          v-if="notice.action === 'cart' && route.path !== '/cart'"
          to="/cart"
          class="notice-action"
          @click="dismissNotice"
          >{{ say(copyText.view_bag_6caa85) }}<PhArrowRight
        /></RouterLink>
        <RouterLink v-if="notice.action==='shop-cart'" to="/shop?view=cart" class="notice-action" @click="dismissNotice">{{say(copyText.view_bag_6caa85)}}<PhArrowRight/></RouterLink>
        <button
          class="icon-button"
          :aria-label="say(copyText.dismiss_notification_a43888)"
          @click="dismissNotice"
        >
          <PhX :size="17" />
        </button></div
    ></Transition>
  </div>
</template>
