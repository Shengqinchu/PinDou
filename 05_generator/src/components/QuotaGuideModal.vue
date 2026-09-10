<script setup lang="ts">
import LiftTitle from "../../../05_studio/src/components/LiftTitle.vue";
import { gt } from '../i18n';
import { vToolDialog } from '../dialog';
import { computed } from 'vue';

const props = withDefaults(defineProps<{
  open: boolean;
  kind?: 'ai' | 'script' | string;
  message?: string;
}>(), {
  kind: 'ai',
  message: ''
});

const emit = defineEmits<{
  close: [];
  redeem: [];
  register: [];
  recharge: [];
}>();

const isAi = computed(() => props.kind === 'ai');
const title = computed(() => isAi.value ? 'AI 积分还差一点' : '普通生成权益不足');
const lead = computed(() => {
  if (props.message) {
    return props.message;
  }
  return isAi.value
    ? 'AI 模式需要可用积分。你可以兑换 CDK、注册领取免费额度，或充值后继续生成。'
    : '普通模式需要时间卡或普通额度。你可以兑换 CDK、注册领取免费额度，或开通时间卡。';
});
const rechargeLabel = computed(() => isAi.value ? '充值积分' : '开通时间卡');
</script>

<template>
  <Teleport to="body"><div class="generator-workspace generator-portal">
    <Transition name="quota-guide-fade">
      <div v-if="open" class="quota-guide-backdrop" role="presentation" @click.self="emit('close')">
        <dialog class="quota-guide" v-tool-dialog="()=>emit('close')" role="dialog" aria-modal="true" aria-labelledby="quota-guide-title">
          <button class="quota-guide__close" type="button" :aria-label='gt("关闭额度引导")' @click="emit('close')">×</button>
          <p class="quota-guide__eyebrow">{{ gt("继续生成") }}</p>
          <LiftTitle id="quota-guide-title" as="h2" :text="gt(title)"/>
          <p class="quota-guide__lead">{{ gt(lead) }}</p>

          <div class="quota-guide__choices" :aria-label='gt("选择继续方式")'>
            <button class="quota-choice" type="button" @click="emit('redeem')">
              <span class="quota-choice__icon" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <path d="M5 8h14v12H5z" />
                  <path d="M7 8c-1.3-2.5.8-4.3 2.7-3 1 .7 1.6 2.1 2.3 3 .7-.9 1.3-2.3 2.3-3 1.9-1.3 4 .5 2.7 3" />
                  <path d="M12 8v12" />
                </svg>
              </span>
              <strong>{{ gt("兑换 CDK 直接用") }}</strong>
              <em>{{ gt("游客也可兑换到本设备") }}</em>
            </button>

            <button class="quota-choice quota-choice--featured" type="button" @click="emit('register')">
              <span class="quota-choice__badge">{{ gt("推荐") }}</span>
              <span class="quota-choice__icon" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z" />
                  <path d="M4 21a8 8 0 0 1 16 0" />
                </svg>
              </span>
              <strong>{{ gt("注册领免费额度") }}</strong>
              <em>{{ gt("3 次普通 + 188 积分") }}</em>
            </button>

            <button class="quota-choice" type="button" @click="emit('recharge')">
              <span class="quota-choice__icon" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <path d="M4 7h16v10H4z" />
                  <path d="M7 11h5" />
                  <path d="M16 14h1" />
                </svg>
              </span>
              <strong>{{ gt(rechargeLabel) }}</strong>
              <em>{{ gt("登录后购买，权益绑账号") }}</em>
            </button>
          </div>

          <p class="quota-guide__note">{{ gt("生成成功才会扣额度，失败不会扣。") }}</p>
        </dialog>
      </div>
    </Transition>
  </div></Teleport>
</template>

<style scoped>
.quota-guide-backdrop {
  position: fixed;
  inset: 0;
  z-index: 86;
  display: grid;
  place-items: center;
  background: rgba(45, 36, 30, 0.34);
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
  padding: 18px;
}

.quota-guide {
  position: relative;
  width: min(100%, 620px);
  border: 1px solid rgba(242, 247, 250, 0.42);
  border-radius: 28px;
  background:
    radial-gradient(circle at 18% 0%, rgba(242, 247, 250, 0.62), transparent 42%),
    linear-gradient(135deg, #f7f9fb 0%, #f7f9fb 100%);
  box-shadow: var(--pd-shadow-float);
  padding: clamp(22px, 4vw, 34px);
}

.quota-guide__close {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(134, 162, 184, 0.22);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.82);
  color: var(--pd-fg-2);
  cursor: pointer;
  font: inherit;
  font-size: 21px;
  font-weight: 600;
  line-height: 1;
  transition: transform 180ms var(--pd-ease-out), box-shadow 180ms var(--pd-ease-out), color 180ms var(--pd-ease-out);
}

.quota-guide__close:hover {
  color: var(--pd-orange);
  box-shadow: 0 12px 24px rgba(134, 162, 184, 0.16);
  transform: translateY(-1px);
}

.quota-guide__eyebrow,
.quota-guide__lead,
.quota-guide__note {
  margin: 0;
}

.quota-guide__eyebrow {
  width: fit-content;
  border-radius: var(--pd-r-tag);
  background: rgba(242, 247, 250, 0.34);
  color: var(--pd-orange);
  font-size: 12px;
  font-weight: 600;
  padding: 5px 9px;
}

.quota-guide h2 {
  margin: 10px 38px 8px 0;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-body);
  font-size: clamp(28px, 5vw, 40px);
  font-weight: 600;
  line-height: 1.12;
}

.quota-guide__lead {
  max-width: 520px;
  color: var(--pd-fg-2);
  font-size: 14px;
  font-weight: 500;
  line-height: 1.65;
}

.quota-guide__choices {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 18px;
}

.quota-choice {
  position: relative;
  min-width: 0;
  min-height: 152px;
  display: grid;
  justify-items: center;
  align-content: center;
  gap: 8px;
  border: 1px solid rgba(242, 247, 250, 0.38);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 12px 28px rgba(45, 65, 80, 0.1);
  color: var(--pd-fg-1);
  cursor: pointer;
  font: inherit;
  padding: 16px 12px;
  text-align: center;
  transition:
    border-color 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    transform 180ms var(--pd-ease-out);
}

.quota-choice:hover {
  border-color: rgba(134, 162, 184, 0.72);
  box-shadow: 0 18px 34px rgba(134, 162, 184, 0.18);
  transform: translateY(-2px);
}

.quota-choice--featured {
  border-width: 2px;
  border-color: rgba(134, 162, 184, 0.84);
  background:
    radial-gradient(circle at 50% 0%, rgba(235, 243, 249, 0.88), transparent 44%),
    #fff;
  box-shadow: 0 18px 42px rgba(134, 162, 184, 0.2);
}

.quota-choice__badge {
  position: absolute;
  top: 10px;
  right: 10px;
  border-radius: var(--pd-r-tag);
  background: rgba(242, 247, 250, 0.4);
  color: var(--pd-fg-1);
  font-size: 11px;
  font-weight: 600;
  padding: 4px 7px;
}

.quota-choice__icon {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  background: rgba(235, 243, 249, 0.12);
  color: var(--pd-orange);
}

.quota-choice__icon svg {
  width: 23px;
  height: 23px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 2;
}

.quota-choice strong,
.quota-choice em {
  display: block;
  min-width: 0;
}

.quota-choice strong {
  color: var(--pd-fg-1);
  font-size: 15px;
  font-weight: 600;
  line-height: 1.3;
}

.quota-choice em {
  color: var(--pd-fg-2);
  font-size: 12px;
  font-style: normal;
  font-weight: 500;
  line-height: 1.45;
}

.quota-guide__note {
  margin-top: 14px;
  color: var(--pd-fg-2);
  font-size: 12px;
  font-weight: 500;
  text-align: center;
}

.quota-guide-fade-enter-active,
.quota-guide-fade-leave-active {
  transition: opacity 180ms var(--pd-ease-out), transform 180ms var(--pd-ease-out);
}

.quota-guide-fade-enter-from,
.quota-guide-fade-leave-to {
  opacity: 0;
}

@media (max-width: 640px) {
  .quota-guide-backdrop {
    align-items: end;
    padding: 10px;
  }

  .quota-guide {
    border-radius: 24px;
    padding: 20px;
  }

  .quota-guide__choices {
    grid-template-columns: 1fr;
  }

  .quota-choice {
    min-height: 96px;
    grid-template-columns: auto 1fr;
    justify-items: start;
    text-align: left;
    align-content: center;
  }

  .quota-choice__badge {
    top: 8px;
    right: 8px;
  }
}
</style>
