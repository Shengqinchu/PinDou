<script setup lang="ts">
import { computed } from "vue";
import {
  PhCheck,
  PhWallet,
  PhArrowRight,
  PhCurrencyCircleDollar,
} from "@phosphor-icons/vue";
import { useDesk } from "../../admin";
import { money } from "../../commerce";
import { tr } from "../../state";
import ToggleSwitch from "../ToggleSwitch.vue";
const {
  settings,
  settingsDirty,
  saving,
  error,
  paymentConfigured,
  saveSettings,
} = useDesk();
const example = computed(() =>
  Math.round(1000 * Number(settings.value?.fx_cny_per_cad || 0)),
);
function setTax(e: Event) {
  if (settings.value)
    settings.value.tax_bps = Math.round(
      Number((e.target as HTMLInputElement).value) * 100,
    );
}
</script>
<template>
  <section>
    <header class="desk-page-heading">
      <div>
        <p class="desk-eyebrow">
          {{ tr("让每一次付款，清清楚楚", "CLEAR PRICES, SIMPLE CHECKOUT") }}
        </p>
        <h1>{{ tr("收款设置", "Checkout settings") }}</h1>
        <p>
          {{
            tr(
              "加元标价、人民币付款。确认好最终金额，再开放小店。",
              "Price in Canadian dollars, collect in Chinese yuan. Confirm the final amounts before opening.",
            )
          }}
        </p>
      </div>
    </header>
    <form
      v-if="settings"
      class="checkout-settings"
      @submit.prevent="saveSettings"
    >
      <section class="desk-surface provider-setting">
        <div class="provider-symbol"><PhWallet :size="30" /></div>
        <div>
          <h2>{{ tr("虎皮椒收银台", "Hupijiao checkout") }}</h2>
          <p>
            {{
              tr(
                "电脑扫码，手机进入收银台；支付结果自动核实。",
                "Scan on desktop or open the cashier on mobile. Payment is verified automatically.",
              )
            }}
          </p>
        </div>
        <span :class="['desk-status', paymentConfigured ? 'paid' : 'draft']">{{
          paymentConfigured
            ? tr("已连接", "Connected")
            : tr("尚未连接", "Not connected")
        }}</span>
      </section>
      <div class="checkout-settings-grid">
        <section class="desk-surface">
          <h2>{{ tr("标价与付款汇率", "Display & payment currency") }}</h2>
          <p class="desk-muted">
            {{
              tr(
                "每笔订单创建时固定汇率，之后修改不会改变旧订单。",
                "The rate is locked when an order is created. Later changes do not affect existing orders.",
              )
            }}
          </p>
          <label class="desk-field"
            >{{ tr("1 加元兑换人民币", "CNY per 1 CAD")
            }}<input
              v-model="settings.fx_cny_per_cad"
              name="fx"
              inputmode="decimal"
              pattern="[0-9]{1,2}(\.[0-9]{1,4})?"
              required
          /></label>
          <div class="currency-example">
            <div>
              <small>{{ tr("示例标价", "Example listed price") }}</small
              ><strong>CA$10.00</strong>
            </div>
            <PhArrowRight />
            <div>
              <small>{{ tr("换算金额", "Converted amount") }}</small
              ><strong>{{
                Number.isFinite(example) ? money(example, "CNY") : "—"
              }}</strong>
            </div>
          </div>
        </section>
        <section class="desk-surface">
          <h2>{{ tr("售价的税费方式", "How prices include tax") }}</h2>
          <p class="desk-muted">
            {{
              tr(
                "请选择实际经营使用的计税方式，客人会在结账前看到最终金额。",
                "Choose the tax treatment you use. Customers see the final amount before payment.",
              )
            }}
          </p>
          <label class="desk-field"
            >{{ tr("税费方式", "Tax treatment")
            }}<select v-model="settings.tax_mode" name="tax_mode">
              <option value="unconfirmed">
                {{ tr("尚未确认", "Not confirmed") }}
              </option>
              <option value="included">
                {{
                  tr(
                    "标价就是最终价（含税）",
                    "Prices are final (tax included)",
                  )
                }}
              </option>
              <option value="additional">
                {{ tr("标价另加税费", "Add tax to listed prices") }}
              </option>
            </select></label
          ><Transition name="field-reveal"
            ><label v-if="settings.tax_mode === 'additional'" class="desk-field"
              >{{ tr("税率 %", "Tax rate %")
              }}<input
                :value="settings.tax_bps / 100"
                type="number"
                min="0"
                max="30"
                step="0.01"
                required
                @input="setTax" /></label
          ></Transition>
          <p v-if="settings.tax_mode === 'unconfirmed'" class="settings-hint">
            {{
              tr(
                "确认后才能开放网上购买。",
                "Confirm this before opening online purchases.",
              )
            }}
          </p>
        </section>
      </div>
      <section class="desk-surface setting-switch-row storefront-switch">
        <div>
          <h2>{{ tr("开放网上购买", "Open online purchases") }}</h2>
          <p>
            {{
              tr(
                "体验还需设置真实营业时间和接待人数；实物需要已上架且有库存。",
                "Visits also require opening hours and capacity. Physical products must be published and in stock.",
              )
            }}
          </p>
        </div>
        <ToggleSwitch
          v-model="settings.enabled"
          :label="tr('开放网上购买', 'Open online purchases')"
        />
      </section>
      <div class="desk-savebar">
        <div>
          <span :class="['save-state-dot', { dirty: settingsDirty }]" />{{
            settingsDirty
              ? tr(
                  "排班／收款设置有未保存的修改",
                  "Unsaved schedule or checkout changes",
                )
              : tr("所有修改已保存", "All changes saved")
          }}
        </div>
        <button
          type="submit"
          class="desk-button primary"
          :disabled="saving || !settingsDirty"
        >
          <PhCheck />{{
            saving ? tr("保存中…", "Saving…") : tr("保存设置", "Save settings")
          }}
        </button>
        <p v-if="error" class="desk-error" role="alert">{{ error }}</p>
      </div>
    </form>
  </section>
</template>
