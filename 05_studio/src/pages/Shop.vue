<script setup lang="ts">
import { computed, ref } from "vue";
import {
  PhArrowDown,
  PhArrowUpRight,
  PhCheck,
  PhMinus,
  PhPlus,
  PhShoppingBagOpen,
} from "@phosphor-icons/vue";
import InquiryForm from "../components/InquiryForm.vue";
import { cart, cartCount, changeQuantity, media, products, tr } from "../state";
const category = ref("all");
const lastAdded = ref("");
const completed = ref(false);
const submitting = ref(false);
const categories = computed(() => [
  { id: "all", label: tr("全部小物", "All the little things") },
  { id: "tools", label: tr("工具与配件", "Tools & fittings") },
  { id: "beads", label: tr("拼豆补充装", "Bead refills") },
  { id: "finished", label: tr("定制成品", "Custom pieces") },
]);
const visible = computed(() =>
  products.filter(
    (p) => category.value === "all" || p.category === category.value,
  ),
);
const selected = computed(() => products.filter((p) => cart.value[p.id]));
const items = computed(() =>
  selected.value.map((p) => ({ id: p.id, quantity: cart.value[p.id] })),
);
const summary = computed(() => [
  ...selected.value.map((p) => `${tr(p.zh, p.en)} × ${cart.value[p.id]}`),
  tr(
    "到店自提 · 款式、库存及价格待确认",
    "Studio pickup · Styles, stock and prices to be confirmed",
  ),
]);
function add(id: string) {
  if (submitting.value || completed.value) return;
  changeQuantity(id, 1);
  lastAdded.value = id;
}
function done() {
  completed.value = true;
  cart.value = {};
}
</script>
<template>
  <section class="container page-intro">
    <h1>
      {{ tr("把喜欢的，", "Little things") }}<br /><em>{{
        tr("一起带回家。", "for your next idea.")
      }}</em>
    </h1>
    <div>
      <p>
        {{
          tr(
            "从第一把镊子，到刚好缺的那个色号。先把心仪的小物放进清单，我们再一起确认款式、价格和自提时间。",
            "From your first pair of tweezers to that missing shade. Make a little list and we will confirm styles, pricing and a time for you to pick it up.",
          )
        }}
      </p>
      <a class="text-link" href="#selection"
        >{{ tr("查看选购清单", "See your selection") }} ({{
          cartCount
        }})<PhArrowDown
      /></a>
    </div>
  </section>
  <section class="container">
    <div
      class="shop-tabs"
      role="group"
      :aria-label="tr('按品类浏览', 'Browse by category')"
    >
      <button
        v-for="tab in categories"
        :key="tab.id"
        :class="{ active: category === tab.id }"
        :aria-pressed="category === tab.id"
        @click="category = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>
    <div class="product-grid">
      <article v-for="product in visible" :key="product.id" class="product">
        <div class="product-image">
          <img
            :src="media(product.image)"
            :alt="tr(product.zh, product.en)"
            loading="lazy"
            width="1080"
            height="1440"
          /><span>{{ tr("到店自提", "Studio pickup") }}</span>
        </div>
        <div class="product-heading">
          <h2>{{ tr(product.zh, product.en) }}</h2>
          <button
            class="add-product icon-button"
            @click="add(product.id)"
            :disabled="(cart[product.id] || 0) >= 20 || completed || submitting"
            :aria-label="
              tr(
                `将${product.zh}加入清单`,
                `Add ${product.en} to your selection`,
              )
            "
          >
            <PhCheck v-if="lastAdded === product.id" /><PhPlus v-else />
          </button>
        </div>
        <p>{{ tr(product.detailZh, product.detailEn) }}</p>
        <div class="product-price">
          {{ tr("款式与价格请询店主", "Ask us about options & pricing") }}
        </div>
      </article>
    </div>
    <p class="sr-only" role="status">
      {{ lastAdded ? tr("已加入选购清单", "Added to your selection") : "" }}
      {{ cartCount }}
    </p>
  </section>
  <section id="selection" class="container selection-section section-space">
    <div class="selection-heading">
      <PhShoppingBagOpen :size="35" weight="light" />
      <h2>{{ tr("你的选购清单", "Your little selection.") }}</h2>
      <p>
        {{
          tr(
            "清单里的小物，等你到店带走。",
            "A few little things to pick up at the studio.",
          )
        }}
      </p>
      <p class="fine-print">
        {{
          tr(
            "当前按需询单，不在线收款。确认款式、库存和价格后再安排自提。",
            "This is a pickup inquiry. There is no online payment. We will confirm options, availability and pricing first.",
          )
        }}
      </p>
    </div>
    <div class="selection-content">
      <div v-if="!cartCount && !completed" class="empty-selection">
        <PhShoppingBagOpen :size="50" weight="light" />
        <h3>{{ tr("这里还空着。", "A little space for your favourites.") }}</h3>
        <p>
          {{
            tr(
              "挑到喜欢的，点一下小加号，就会出现在这里。",
              "Find something you like above and tap the plus to add it here.",
            )
          }}
        </p>
        <a class="text-link" href="#main"
          >{{ tr("继续挑选", "Find a little something") }}<PhArrowUpRight
        /></a>
      </div>
      <template v-else
        ><div v-if="!completed" class="cart-lines">
          <article
            v-for="product in selected"
            :key="product.id"
            class="cart-line"
          >
            <img
              :src="media(product.image)"
              :alt="tr(product.zh, product.en)"
              width="74"
              height="88"
            />
            <div>
              <h3>{{ tr(product.zh, product.en) }}</h3>
              <span>{{ tr("价格待店主确认", "Price to be confirmed") }}</span>
            </div>
            <div class="quantity">
              <button
                type="button"
                class="icon-button"
                @click="changeQuantity(product.id, -1)"
                :disabled="submitting"
                :aria-label="
                  tr(`减少${product.zh}的数量`, `Decrease ${product.en}`)
                "
              >
                <PhMinus :size="16" /></button
              ><span>{{ cart[product.id] }}</span
              ><button
                class="icon-button"
                type="button"
                @click="changeQuantity(product.id, 1)"
                :disabled="cart[product.id] >= 20 || submitting"
                :aria-label="
                  tr(`增加${product.zh}的数量`, `Increase ${product.en}`)
                "
              >
                <PhPlus :size="16" />
              </button>
            </div>
          </article>
        </div>
        <InquiryForm
          kind="pickup"
          :items="items"
          :summary="summary"
          @complete="done"
          @busy="submitting = $event"
      /></template>
    </div>
  </section>
</template>
