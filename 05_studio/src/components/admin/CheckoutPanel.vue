<script setup lang="ts">
import copyText from "../../content/components-admin-CheckoutPanel.json";
import { say } from "../../state";

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
          {{ say(copyText.clear_prices_simple_checkout_3d511f) }}
        </p>
        <h1>{{ say(copyText.checkout_settings_b08011) }}</h1>
        <p>
          {{
            say(copyText.price_in_canadian_dollars_collect_in_chinese_35f2a3)
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
          <h2>{{ say(copyText.hupijiao_checkout_017d75) }}</h2>
          <p>
            {{ say(copyText.scan_on_desktop_or_open_the_cashier_e2fe8b) }}
          </p>
        </div>
        <span :class="['desk-status', paymentConfigured ? 'paid' : 'draft']">{{
          paymentConfigured
            ? say(copyText.connected_bd103c)
            : say(copyText.not_connected_238174)
        }}</span>
      </section>
      <div class="checkout-settings-grid">
        <section class="desk-surface">
          <h2>{{ say(copyText.display_payment_currency_9d99f4) }}</h2>
          <p class="desk-muted">
            {{ say(copyText.the_rate_is_locked_when_an_order_b8c1b7) }}
          </p>
          <label class="desk-field"
            >{{ say(copyText.cny_per_1_cad_e11b72)
            }}<input
              v-model="settings.fx_cny_per_cad"
              name="fx"
              inputmode="decimal"
              pattern="[0-9]{1,2}(\.[0-9]{1,4})?"
              required
          /></label>
          <div class="currency-example">
            <div>
              <small>{{ say(copyText.example_listed_price_7fc44a) }}</small
              ><strong>CA$10.00</strong>
            </div>
            <PhArrowRight />
            <div>
              <small>{{ say(copyText.converted_amount_5871b3) }}</small
              ><strong>{{
                Number.isFinite(example) ? money(example, "CNY") : "—"
              }}</strong>
            </div>
          </div>
        </section>
        <section class="desk-surface">
          <h2>{{ say(copyText.how_prices_include_tax_bcd6c4) }}</h2>
          <p class="desk-muted">
            {{
              say(copyText.choose_the_tax_treatment_you_use_customers_4bb4b9)
            }}
          </p>
          <label class="desk-field"
            >{{ say(copyText.tax_treatment_b619a7)
            }}<select v-model="settings.tax_mode" name="tax_mode">
              <option value="unconfirmed">
                {{ say(copyText.not_confirmed_bf61ba) }}
              </option>
              <option value="included">
                {{ say(copyText.prices_are_final_tax_included_dc93af) }}
              </option>
              <option value="additional">
                {{ say(copyText.add_tax_to_listed_prices_e4cb3b) }}
              </option>
            </select></label
          ><Transition name="field-reveal"
            ><label v-if="settings.tax_mode === 'additional'" class="desk-field"
              >{{ say(copyText.tax_rate_16a67f)
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
              say(copyText.confirm_this_before_opening_online_purchases_adcdf0)
            }}
          </p>
        </section>
      </div>
      <section class="desk-surface setting-switch-row storefront-switch">
        <div>
          <h2>{{ say(copyText.open_online_purchases_d4629b) }}</h2>
          <p>
            {{
              say(
                copyText.visits_also_require_opening_hours_and_capacity_e05e70,
              )
            }}
          </p>
        </div>
        <ToggleSwitch
          v-model="settings.enabled"
          :label="say(copyText.open_online_purchases_d4629b)"
        />
      </section>
      <div class="desk-savebar">
        <div>
          <span :class="['save-state-dot', { dirty: settingsDirty }]" />{{
            settingsDirty
              ? say(copyText.unsaved_schedule_or_checkout_changes_dbb518)
              : say(copyText.all_changes_saved_05df19)
          }}
        </div>
        <button
          type="submit"
          class="desk-button primary"
          :disabled="saving || !settingsDirty"
        >
          <PhCheck />{{
            saving
              ? say(copyText.saving_1bd9fd)
              : say(copyText.save_settings_3a2a2e)
          }}
        </button>
        <p v-if="error" class="desk-error" role="alert">{{ error }}</p>
      </div>
    </form>
  </section>
</template>
