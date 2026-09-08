<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { PhArrowRight, PhCheck, PhPlus } from "@phosphor-icons/vue";
import { media, tr } from "../state";
import SegmentedControl from "../components/SegmentedControl.vue";
import AutoHeight from "../components/AutoHeight.vue";
import {
  pinLeavingItem,
  clearLeavingItem,
  snapshotLeavingItems,
} from "../motion";
import { addToBag, bagCount, catalog, loadCatalog, money } from "../commerce";
const category = ref("all");
const productsSection = ref<HTMLElement>();
watch(category, () =>
  snapshotLeavingItems(
    productsSection.value?.querySelector(".product-grid") || null,
  ),
);
const lastAdded = ref("");
const error = ref("");
const loading = ref(false);
const categories = computed(() => [
  { id: "all", label: tr("全部", "All") },
  { id: "tools", label: tr("工具配件", "Tools") },
  { id: "beads", label: tr("补充豆", "Beads") },
  { id: "finished", label: tr("手作成品", "Handmade") },
]);
const visible = computed(
  () =>
    catalog.value?.products.filter(
      (p) =>
        p.kind === "physical" &&
        (category.value === "all" || p.category === category.value),
    ) || [],
);
async function reloadProducts() {
  loading.value = true;
  error.value = "";
  try {
    await loadCatalog();
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    loading.value = false;
  }
}
onMounted(reloadProducts);
function add(id: string) {
  addToBag(id);
  lastAdded.value = id;
}
</script>
<template>
  <section class="container page-intro">
    <h1>{{ tr("拼豆小店", "The little shop.") }}</h1>
    <div>
      <p>
        {{
          tr(
            "从第一把镊子，到刚好缺的那个色号。挑好喜欢的小物，放进购物车，付款后到店带走。",
            "From your first pair of tweezers to that missing shade. Choose your favourites, pay online and pick them up at the studio.",
          )
        }}
      </p>
      <RouterLink to="/cart" class="text-link"
        >{{ tr(`打开购物车 · ${bagCount}`, `Your bag · ${bagCount}`)
        }}<PhArrowRight
      /></RouterLink>
    </div>
  </section>
  <section ref="productsSection" class="container section-bottom">
    <SegmentedControl
      class="shop-segments"
      v-model="category"
      :label="tr('商品分类', 'Product categories')"
      :options="categories.map((c) => ({ value: c.id, label: c.label }))"
    />
    <p v-if="error" class="form-error" role="alert">
      {{ error }}
      <button class="text-link" :disabled="loading" @click="reloadProducts">
        {{ tr("重新加载商品", "Reload products") }}
      </button>
    </p>
    <p v-if="loading" class="form-help" role="status">
      {{ tr("正在查看小店里的商品…", "Loading the little shop…") }}
    </p>
    <AutoHeight
      ><TransitionGroup
        name="product-list"
        tag="div"
        class="product-grid"
        @before-leave="pinLeavingItem"
        @after-leave="clearLeavingItem"
        @before-enter="clearLeavingItem"
      >
        <article v-for="p in visible" :key="p.id" class="product-card">
          <div class="product-image">
            <img
              :src="media(p.image)"
              width="1080"
              height="1440"
              :alt="tr(p.zh, p.en)"
              loading="lazy"
            /><span
              v-if="!p.active || p.price_cents === null"
              class="product-status"
              >{{ tr("即将上架", "Coming soon") }}</span
            >
          </div>
          <div class="product-heading">
            <h2>{{ tr(p.zh, p.en) }}</h2>
            <strong
              v-if="p.active && p.price_cents !== null"
              class="product-price"
              >{{ money(p.price_cents) }}</strong
            >
          </div>
          <p>{{ tr(p.detailZh, p.detailEn) }}</p>
          <button
            class="button button-outline full-button"
            :disabled="
              loading ||
              !!error ||
              !p.active ||
              p.price_cents === null ||
              !p.available_stock ||
              !catalog?.checkout_ready
            "
            @click="add(p.id)"
          >
            <template v-if="lastAdded === p.id"
              >{{ tr("再添一件", "Add another") }}<PhCheck /></template
            ><template v-else-if="p.active && p.price_cents !== null"
              >{{
                p.available_stock
                  ? tr("加入购物车", "Add to bag")
                  : tr("暂时售罄", "Sold out")
              }}<PhPlus /></template
            ><template v-else
              >{{ tr("小物整理中", "Coming soon") }}<PhPlus
            /></template>
          </button>
        </article> </TransitionGroup
    ></AutoHeight>
    <div class="shop-visit-bridge">
      <p>
        {{
          tr(
            "想在工作室度过一个下午？",
            "Rather make a little afternoon of it?",
          )
        }}
      </p>
      <RouterLink to="/visit" class="text-link"
        >{{ tr("选一个到店时段", "Choose a studio visit") }}<PhArrowRight
      /></RouterLink>
    </div>
  </section>
</template>
