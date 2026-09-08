<script setup lang="ts">
import { computed, ref } from "vue";
import {
  PhPlus,
  PhArrowUpRight,
  PhMagnifyingGlass,
  PhCheck,
  PhPackage,
} from "@phosphor-icons/vue";
import { useDesk } from "../../admin";
import { type Product, money } from "../../commerce";
import { media, tr } from "../../state";
import SlideOver from "../SlideOver.vue";
import SegmentedControl from "../SegmentedControl.vue";
import ToggleSwitch from "../ToggleSwitch.vue";
const { products, saving, error, saveProduct, request } = useDesk();
const category = ref("all");
const search = ref("");
const edit = ref<Product>();
const open = ref(false);
const drafts = new Map<string, Product>();
const visible = computed(() =>
  products.value.filter(
    (p) =>
      (category.value === "all" ||
        (category.value === "draft" ? !p.active : p.kind === category.value)) &&
      `${p.zh} ${p.en}`.toLowerCase().includes(search.value.toLowerCase()),
  ),
);
const photos = [
  "studio-04",
  "studio-07",
  "studio-06",
  "studio-11",
  "journal-05",
  "journal-13",
];
function editProduct(p: Product) {
  edit.value = drafts.get(p.id) || JSON.parse(JSON.stringify(p));
  drafts.set(p.id, edit.value!);
  error.value = "";
  open.value = true;
}
function create() {
  editProduct({
    id: "item-" + crypto.randomUUID().slice(0, 8),
    kind: "physical",
    category: "tools",
    zh: "",
    en: "",
    detailZh: "",
    detailEn: "",
    image: "studio-07",
    price_cents: null,
    stock: 0,
    active: false,
    version: 1,
  });
}
function price(e: Event) {
  if (edit.value) {
    const value = (e.target as HTMLInputElement).value;
    edit.value.price_cents =
      value === "" ? null : Math.round(Number(value) * 100);
  }
}
async function save() {
  if (!edit.value) return;
  const result = await saveProduct(edit.value);
  if (result) {
    drafts.delete(result.id);
    edit.value = JSON.parse(JSON.stringify(result));
    open.value = false;
  }
}
async function reloadSaved() {
  if (!edit.value) return;
  try {
    const data = await request<{ products: Product[] }>("/manage/commerce");
    const value = data.products.find((p) => p.id === edit.value?.id);
    if (value) {
      edit.value = JSON.parse(JSON.stringify(value));
      drafts.set(value.id, edit.value!);
      error.value = "";
    }
  } catch (e) {
    error.value = (e as Error).message;
  }
}
</script>
<template>
  <section>
    <header class="desk-page-heading">
      <div>
        <p class="desk-eyebrow">
          {{ tr("每件小物，都有自己的位置", "LITTLE THINGS, WELL ARRANGED") }}
        </p>
        <h1>{{ tr("商品与体验", "Products & experiences") }}</h1>
        <p>
          {{
            tr(
              "定价、库存、上架状态，在这里一起照看。",
              "Look after your prices, inventory and published products in one place.",
            )
          }}
        </p>
      </div>
      <button class="desk-button primary" @click="create">
        <PhPlus />{{ tr("添加商品", "Add product") }}
      </button>
    </header>
    <section class="desk-surface product-workspace">
      <div class="order-filterbar">
        <SegmentedControl
          v-model="category"
          :label="tr('商品类别', 'Product category')"
          :options="[
            { value: 'all', label: tr('全部', 'All') },
            { value: 'experience', label: tr('到店体验', 'Visits') },
            { value: 'physical', label: tr('小物', 'Items') },
            { value: 'draft', label: tr('待上架', 'Drafts') },
          ]"
        /><label class="desk-search"
          ><PhMagnifyingGlass /><input
            v-model="search"
            :placeholder="tr('搜索商品名称', 'Search products')"
            :aria-label="tr('搜索商品', 'Search products')"
        /></label>
      </div>
      <TransitionGroup name="product-list" tag="div" class="desk-product-list"
        ><button
          v-for="p in visible"
          :key="p.id"
          class="desk-product-row"
          @click="editProduct(p)"
        >
          <img
            :src="media(p.image)"
            width="1080"
            height="1440"
            :alt="tr(p.zh, p.en)"
          /><span class="desk-product-name"
            ><strong>{{ tr(p.zh, p.en) }}</strong
            ><small>{{
              p.kind === "experience"
                ? tr("到店体验", "Studio experience")
                : tr("到店自提", "Studio pickup")
            }}</small></span
          ><span class="desk-product-price"
            ><strong>{{
              p.price_cents === null
                ? tr("待定价", "Not priced")
                : money(p.price_cents)
            }}</strong
            ><small>{{
              p.id === "hourly"
                ? tr("/ 人 / 小时", "/ person / hour")
                : p.kind === "experience"
                  ? tr("/ 套餐", "/ pass")
                  : tr(`库存 ${p.stock}`, `${p.stock} in stock`)
            }}</small></span
          ><span :class="['desk-status', p.active ? 'paid' : 'draft']">{{
            p.active ? tr("已上架", "Published") : tr("待上架", "Draft")
          }}</span
          ><PhArrowUpRight /></button
      ></TransitionGroup>
      <div v-if="!visible.length" class="desk-empty">
        <PhPackage :size="30" />
        <h3>{{ tr("没有找到这件小物", "No matching products") }}</h3>
        <p>
          {{
            tr(
              "换个名字搜搜，或者添加一件新商品。",
              "Try another name or add a new product.",
            )
          }}
        </p>
      </div>
    </section>
    <SlideOver
      v-model="open"
      :title="edit?.zh || tr('添加商品', 'Add product')"
      :subtitle="
        tr(
          '商品编辑 · 关闭后保留本次草稿',
          'PRODUCT EDITOR · DRAFT KEPT WHILE OPEN IN THIS DESK',
        )
      "
      :busy="saving"
      ><form
        v-if="edit"
        id="product-editor"
        class="product-editor"
        @submit.prevent="save"
      >
        <div class="product-editor-preview">
          <img
            :src="media(edit.image)"
            :alt="tr('当前商品图片', 'Current product photo')"
          />
          <div>
            <span :class="['desk-status', edit.active ? 'paid' : 'draft']">{{
              edit.active
                ? tr("上架出售", "Published for sale")
                : tr("待上架", "Draft")
            }}</span>
            <p>{{ tr("使用工作室实拍", "Photographed at the studio") }}</p>
          </div>
        </div>
        <div class="desk-form-grid">
          <label class="desk-field product-name-field"
            >{{ tr("中文名称", "Chinese name")
            }}<input v-model="edit.zh" maxlength="90" required /></label
          ><label class="desk-field product-name-field"
            >{{ tr("英文名称", "English name")
            }}<input v-model="edit.en" maxlength="140" required /></label
          ><label class="desk-field"
            >{{ tr("售价 · CA$", "Price · CA$")
            }}<input
              :value="edit.price_cents === null ? '' : edit.price_cents / 100"
              type="number"
              min="0.01"
              max="10000"
              step="0.01"
              :required="edit.active"
              @input="price" /></label
          ><label v-if="edit.kind === 'physical'" class="desk-field"
            >{{ tr("剩余库存", "Remaining inventory")
            }}<input
              v-model.number="edit.stock"
              type="number"
              min="0"
              max="100000"
              required /></label
          ><label v-if="edit.kind === 'physical'" class="desk-field"
            >{{ tr("分类", "Category")
            }}<select v-model="edit.category">
              <option value="tools">
                {{ tr("工具与配件", "Tools & fittings") }}
              </option>
              <option value="beads">
                {{ tr("拼豆补充装", "Bead refills") }}
              </option>
              <option value="finished">
                {{ tr("手作成品", "Finished pieces") }}
              </option>
            </select></label
          ><label class="desk-field"
            >{{ tr("商品照片", "Product photo")
            }}<select v-model="edit.image">
              <option
                v-for="n in 15"
                :key="n"
                :value="`studio-${String(n).padStart(2, '0')}`"
              >
                {{ tr("工作室", "Studio") }} {{ n }}
              </option>
              <option
                v-for="n in ['02', '04', '05', '07', '10', '11', '13', '20']"
                :key="n"
                :value="`journal-${n}`"
              >
                {{ tr("日记", "Journal") }} {{ n }}
              </option>
            </select></label
          >
        </div>
        <div class="photo-choices">
          <button
            v-for="photo in photos"
            :key="photo"
            type="button"
            :class="{ selected: edit.image === photo }"
            :aria-label="tr(`选择照片 ${photo}`, `Choose photo ${photo}`)"
            :aria-pressed="edit.image === photo"
            @click="edit.image = photo"
          >
            <img :src="media(photo)" alt="" />
          </button>
        </div>
        <label class="desk-field"
          >{{ tr("中文说明", "Chinese description")
          }}<textarea v-model="edit.detailZh" rows="3" maxlength="500" /></label
        ><label class="desk-field"
          >{{ tr("英文说明", "English description")
          }}<textarea v-model="edit.detailEn" rows="3" maxlength="700" />
        </label>
        <div class="setting-switch-row">
          <div>
            <strong>{{ tr("上架出售", "Publish for sale") }}</strong>
            <p>
              {{
                tr(
                  "填写售价后即可上架；实物还需要有库存。",
                  "Set a price to publish. Physical items also need stock.",
                )
              }}
            </p>
          </div>
          <ToggleSwitch
            v-model="edit.active"
            :label="tr('上架出售', 'Publish for sale')"
          />
        </div>
        <p v-if="error" class="desk-error" role="alert">{{ error }}</p>
        <button
          v-if="error && products.some((p) => p.id === edit?.id)"
          type="button"
          class="desk-link"
          @click="reloadSaved"
        >
          {{ tr("重新载入已保存版本", "Reload the saved version") }}
        </button>
      </form>
      <template #footer
        ><span class="drawer-footnote">{{
          tr("订单中的历史价格保持不变", "Existing order prices stay unchanged")
        }}</span
        ><button
          class="desk-button primary"
          form="product-editor"
          type="submit"
          :disabled="saving"
        >
          <PhCheck />{{
            saving ? tr("保存中…", "Saving…") : tr("保存商品", "Save product")
          }}
        </button></template
      ></SlideOver
    >
  </section>
</template>
