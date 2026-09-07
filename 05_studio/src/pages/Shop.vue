<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { PhArrowRight, PhCheck, PhPlus } from "@phosphor-icons/vue";
import { media, tr } from "../state";
import { addToBag, bagCount, catalog, loadCatalog, money } from "../commerce";
const category = ref("all");
const lastAdded = ref("");
const error = ref("");
const categories = computed(() => [
  { id: "all", label: tr("全部小物", "All the little things") },
  { id: "tools", label: tr("工具与配件", "Tools & fittings") },
  { id: "beads", label: tr("拼豆补充装", "Bead refills") },
  { id: "finished", label: tr("手作成品", "Finished pieces") },
]);
const visible = computed(
  () =>
    catalog.value?.products.filter(
      (p) =>
        p.kind === "physical" &&
        (category.value === "all" || p.category === category.value),
    ) || [],
);
onMounted(async () => {
  try {
    await loadCatalog();
  } catch (e) {
    error.value = (e as Error).message;
  }
});
function add(id: string) {
  addToBag(id);
  lastAdded.value = id;
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
  <section class="container section-bottom">
    <div class="shop-tabs" :aria-label="tr('商品分类', 'Product categories')">
      <button
        v-for="c in categories"
        :key="c.id"
        :class="{ active: category === c.id }"
        :aria-pressed="category === c.id"
        @click="category = c.id"
      >
        {{ c.label }}
      </button>
    </div>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <div class="product-grid">
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
            !p.active ||
            p.price_cents === null ||
            !p.available_stock ||
            !catalog?.checkout_ready
          "
          @click="add(p.id)"
        >
          <template v-if="lastAdded === p.id"
            >{{ tr("已加入，再添一件", "Added · Add another")
            }}<PhCheck /></template
          ><template v-else-if="p.active && p.price_cents !== null"
            >{{
              p.available_stock
                ? tr("加入购物车", "Add to bag")
                : tr("暂时售罄", "Sold out")
            }}<PhPlus /></template
          ><template v-else
            >{{ tr("小物整理中", "Getting things ready") }}<PhPlus
          /></template>
        </button>
      </article>
    </div>
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
