<script setup lang="ts">
import { formatCopy } from "../../state";

import copyText from "../../content/components-admin-ProductsPanel.json";
import { say } from "../../state";

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
          {{ say(copyText.little_things_well_arranged_cc4680) }}
        </p>
        <h1>{{ say(copyText.products_experiences_13735c) }}</h1>
        <p>
          {{
            say(copyText.look_after_your_prices_inventory_and_published_2a98fe)
          }}
        </p>
      </div>
      <button class="desk-button primary" @click="create">
        <PhPlus />{{ say(copyText.add_product_439e17) }}
      </button>
    </header>
    <section class="desk-surface product-workspace">
      <div class="order-filterbar">
        <SegmentedControl
          v-model="category"
          :label="say(copyText.product_category_6dec25)"
          :options="[
            { value: 'all', label: say(copyText.all_902ec4) },
            { value: 'experience', label: say(copyText.visits_3059b2) },
            { value: 'physical', label: say(copyText.items_b2522f) },
            { value: 'draft', label: say(copyText.drafts_034400) },
          ]"
        /><label class="desk-search"
          ><PhMagnifyingGlass /><input
            v-model="search"
            :placeholder="say(copyText.search_products_1bc725)"
            :aria-label="say(copyText.search_products_2ea3aa)"
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
                ? say(copyText.studio_experience_8cbb77)
                : say(copyText.studio_pickup_c13b87)
            }}</small></span
          ><span class="desk-product-price"
            ><strong>{{
              p.price_cents === null
                ? say(copyText.not_priced_b9f3bb)
                : money(p.price_cents)
            }}</strong
            ><small>{{
              p.id === "hourly"
                ? say(copyText.person_hour_07ef59)
                : p.kind === "experience"
                  ? say(copyText.pass_63a44a)
                  : formatCopy(copyText.message_f4149935, { v0: p.stock })
            }}</small></span
          ><span :class="['desk-status', p.active ? 'paid' : 'draft']">{{
            p.active
              ? say(copyText.published_34899d)
              : say(copyText.draft_e2df44)
          }}</span
          ><PhArrowUpRight /></button
      ></TransitionGroup>
      <div v-if="!visible.length" class="desk-empty">
        <PhPackage :size="30" />
        <h3>{{ say(copyText.no_matching_products_0e35fb) }}</h3>
        <p>
          {{ say(copyText.try_another_name_or_add_a_new_b5ae79) }}
        </p>
      </div>
    </section>
    <SlideOver
      v-model="open"
      :title="edit?.zh || say(copyText.add_product_439e17)"
      :subtitle="say(copyText.product_editor_draft_kept_while_open_in_e4715a)"
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
            :alt="say(copyText.current_product_photo_cae790)"
          />
          <div>
            <span :class="['desk-status', edit.active ? 'paid' : 'draft']">{{
              edit.active
                ? say(copyText.published_for_sale_ecea53)
                : say(copyText.draft_e2df44)
            }}</span>
            <p>{{ say(copyText.photographed_at_the_studio_e4b259) }}</p>
          </div>
        </div>
        <div class="desk-form-grid">
          <label class="desk-field product-name-field"
            >{{ say(copyText.chinese_name_9df9b3)
            }}<input v-model="edit.zh" maxlength="90" required /></label
          ><label class="desk-field product-name-field"
            >{{ say(copyText.english_name_63f9e2)
            }}<input v-model="edit.en" maxlength="140" required /></label
          ><label class="desk-field"
            >{{ say(copyText.price_ca_d65afe)
            }}<input
              :value="edit.price_cents === null ? '' : edit.price_cents / 100"
              type="number"
              min="0.01"
              max="10000"
              step="0.01"
              :required="edit.active"
              @input="price" /></label
          ><label v-if="edit.kind === 'physical'" class="desk-field"
            >{{ say(copyText.remaining_inventory_5b9914)
            }}<input
              v-model.number="edit.stock"
              type="number"
              min="0"
              max="100000"
              required /></label
          ><label v-if="edit.kind === 'physical'" class="desk-field"
            >{{ say(copyText.category_f7fc04)
            }}<select v-model="edit.category">
              <option value="tools">
                {{ say(copyText.tools_fittings_02d81e) }}
              </option>
              <option value="beads">
                {{ say(copyText.bead_refills_4d7505) }}
              </option>
              <option value="finished">
                {{ say(copyText.finished_pieces_35b338) }}
              </option>
            </select></label
          ><label class="desk-field"
            >{{ say(copyText.product_photo_2024ac)
            }}<select v-model="edit.image">
              <option
                v-for="n in 15"
                :key="n"
                :value="`studio-${String(n).padStart(2, '0')}`"
              >
                {{ say(copyText.studio_108de6) }} {{ n }}
              </option>
              <option
                v-for="n in ['02', '04', '05', '07', '10', '11', '13', '20']"
                :key="n"
                :value="`journal-${n}`"
              >
                {{ say(copyText.journal_ba5107) }} {{ n }}
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
            :aria-label="formatCopy(copyText.message_5872baff, { v0: photo })"
            :aria-pressed="edit.image === photo"
            @click="edit.image = photo"
          >
            <img :src="media(photo)" alt="" />
          </button>
        </div>
        <label class="desk-field"
          >{{ say(copyText.chinese_description_052a41)
          }}<textarea v-model="edit.detailZh" rows="3" maxlength="500" /></label
        ><label class="desk-field"
          >{{ say(copyText.english_description_4b3b3f)
          }}<textarea v-model="edit.detailEn" rows="3" maxlength="700" />
        </label>
        <div class="setting-switch-row">
          <div>
            <strong>{{ say(copyText.publish_for_sale_75afac) }}</strong>
            <p>
              {{ say(copyText.set_a_price_to_publish_physical_items_01ffc8) }}
            </p>
          </div>
          <ToggleSwitch
            v-model="edit.active"
            :label="say(copyText.publish_for_sale_75afac)"
          />
        </div>
        <p v-if="error" class="desk-error" role="alert">{{ error }}</p>
        <button
          v-if="error && products.some((p) => p.id === edit?.id)"
          type="button"
          class="desk-link"
          @click="reloadSaved"
        >
          {{ say(copyText.reload_the_saved_version_ca095e) }}
        </button>
      </form>
      <template #footer
        ><span class="drawer-footnote">{{
          say(copyText.existing_order_prices_stay_unchanged_9345aa)
        }}</span
        ><button
          class="desk-button primary"
          form="product-editor"
          type="submit"
          :disabled="saving"
        >
          <PhCheck />{{
            saving
              ? say(copyText.saving_1bd9fd)
              : say(copyText.save_product_4bb744)
          }}
        </button></template
      ></SlideOver
    >
  </section>
</template>
