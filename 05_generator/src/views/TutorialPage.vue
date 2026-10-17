<script setup lang="ts">
import LiftTitle from "../../../05_studio/src/components/LiftTitle.vue";
import { gt,generatorLocale } from '../i18n';
import { RouterLink } from 'vue-router';
import { computed } from 'vue';

const uploadImage = computed(()=>generatorLocale.value==='zh'?new URL('../assets/tutorial/upload-page-zh.png',import.meta.url).href:new URL('../assets/tutorial/upload-page-en.png',import.meta.url).href);
const optionsImage = computed(()=>generatorLocale.value==='zh'?new URL('../assets/tutorial/options-panel-zh.png',import.meta.url).href:new URL('../assets/tutorial/options-panel-en.png',import.meta.url).href);
const loadingImage = computed(()=>generatorLocale.value==='zh'?new URL('../assets/tutorial/loading-page-zh.png',import.meta.url).href:new URL('../assets/tutorial/loading-page-en.png',import.meta.url).href);
const resultImage = computed(()=>generatorLocale.value==='zh'?new URL('../assets/tutorial/result-page-zh.png',import.meta.url).href:new URL('../assets/tutorial/result-page-en.png',import.meta.url).href);
const editorImage = computed(()=>generatorLocale.value==='zh'?new URL('../assets/tutorial/editor-page-zh.png',import.meta.url).href:new URL('../assets/tutorial/editor-page-en.png',import.meta.url).href);
const pricingImage = computed(()=>generatorLocale.value==='zh'?new URL('../assets/tutorial/pricing-modal-zh.png',import.meta.url).href:new URL('../assets/tutorial/pricing-modal-en.png',import.meta.url).href);
const cdkImage = computed(()=>generatorLocale.value==='zh'?new URL('../assets/tutorial/cdk-redeem-zh.png',import.meta.url).href:new URL('../assets/tutorial/cdk-redeem-en.png',import.meta.url).href);
const quotaImage = computed(()=>generatorLocale.value==='zh'?new URL('../assets/tutorial/pricing-modal-zh.png',import.meta.url).href:new URL('../assets/tutorial/pricing-modal-en.png',import.meta.url).href);

const flowSteps = computed(()=>[
  {
    title: '上传照片',
    text: '选一张主体清楚、光线干净的照片。白底卡通和正脸照片最容易出清爽图纸。',
    image: uploadImage.value,
    alt: 'Pindou Puppy 上传页截图'
  },
  {
    title: '选模式和尺寸',
    text: '卡通原图用普通模式秒出；真人、宠物、实物照片建议 AI 模式，先转 Q 版再量化。',
    image: optionsImage.value,
    alt: 'Pindou Puppy 模式和目标格数选择截图'
  },
  {
    title: '等待生成',
    text: '生成中会显示阶段进度。AI 模式稍慢一点，普通模式通常更快。',
    image: loadingImage.value,
    alt: 'Pindou Puppy 生成中页面截图'
  },
  {
    title: '检查图纸',
    text: '看图纸、豆数、色号清单和占比。觉得某块颜色不对，就进入编辑器微调。',
    image: resultImage.value,
    alt: 'Pindou Puppy 结果页截图'
  },
  {
    title: '编辑和下载',
    text: '点格改色、全局替换色号，保存后下载 PNG。手机端可分享或长按保存。',
    image: editorImage.value,
    alt: 'Pindou Puppy 图纸编辑器截图'
  }
]);

const modeCards = [
  {
    title: '普通模式',
    badge: '秒出',
    points: ['适合本来就是卡通、线稿、图标的图片', '直接量化原图，保留原始构图', '普通生成免费不限次'],
    hint: '想快速试尺寸、看豆数，先用它。'
  },
  {
    title: 'AI 模式',
    badge: '推荐真人/宠物',
    points: ['先把照片变成 Q 版卡通，再转拼豆图纸', '更容易少色、干净、轮廓清楚', '统一 128 积分/张，成功才扣'],
    hint: '真实照片、实物、杂色背景，优先用它。'
  }
];

const walletItems = computed(()=>[
  {
    title: 'AI 积分',
    text: 'AI 模式统一 128 积分/张。生成成功才扣，失败不扣。',
    image: pricingImage.value,
    alt: 'Pindou Puppy 充值中心截图'
  },
  {
    title: '时间卡会员',
    text: '时间卡解锁普通模式不限次，并随卡赠送积分；AI 仍按积分扣。',
    image: pricingImage.value,
    alt: 'Pindou Puppy 时间卡会员截图'
  },
  {
    title: 'CDK 兑换',
    text: '有兑换码时可以直接兑换。游客也能把 CDK 兑到当前设备钱包。',
    image: cdkImage.value,
    alt: 'Pindou Puppy CDK 兑换截图'
  },
  {
    title: '额度不足',
    text: '额度不够时会给你三条路：兑换 CDK、注册领礼、充值。',
    image: quotaImage.value,
    alt: 'Pindou Puppy 额度不足三选一引导截图'
  }
]);
</script>

<template>
  <section class="tutorial-page">
    <header class="tutorial-hero">
      <div class="tutorial-hero__copy">
        <span class="tutorial-kicker">{{ gt("新手教程") }}</span>
        <LiftTitle as="h1" :text="gt('从照片到拼豆图纸，一页看懂')"/>
        <p>{{ gt("照着这条流程走：上传照片、选择模式、生成图纸、编辑配色、下载保存。第一次用也不会乱。") }}</p>
        <div class="tutorial-hero__actions">
          <RouterLink class="pd-btn pd-btn--primary" to="/tools">{{ gt("现在去上传") }}<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              <path d="M5 12h14" />
              <path d="m13 6 6 6-6 6" />
            </svg>
          </RouterLink>
          <a class="tutorial-secondary" href="#faq">{{ gt("先看避坑") }}</a>
        </div>
      </div>
      <div class="tutorial-hero__media">
        <img :src="resultImage" :alt='gt("Pindou Puppy 结果页预览")' />
      </div>
    </header>

    <nav class="tutorial-anchor-nav" :aria-label='gt("教程小节")'>
      <a href="#generate">{{ gt("生成图纸") }}</a>
      <a href="#mode">{{ gt("普通 vs AI") }}</a>
      <a href="#wallet">{{ gt("积分会员") }}</a>
      <a href="#faq">FAQ</a>
    </nav>

    <section id="generate" class="tutorial-section">
      <div class="tutorial-section__heading">
        <span class="tutorial-kicker">01</span>
        <LiftTitle as="h2" :text="gt('怎么生成图纸')"/>
        <p>{{ gt("上传、选择、生成、编辑、下载，五步就能拿到可照着摆的图纸。") }}</p>
      </div>

      <div class="flow-grid">
        <article v-for="(step, index) in flowSteps" :key="step.title" class="flow-card">
          <span class="flow-card__index">{{ gt(index + 1) }}</span>
          <img :src="step.image" :alt="gt(step.alt)" loading="lazy" />
          <div>
            <h3>{{ gt(step.title) }}</h3>
            <p>{{ gt(step.text) }}</p>
          </div>
        </article>
      </div>
    </section>

    <section id="mode" class="tutorial-section">
      <div class="tutorial-section__heading">
        <span class="tutorial-kicker">02</span>
        <LiftTitle as="h2" :text="gt('普通 vs AI 怎么选')"/>
        <p>{{ gt("不需要纠结参数。看原图类型，选对模式就行。") }}</p>
      </div>

      <div class="mode-grid">
        <article v-for="card in modeCards" :key="card.title" class="mode-guide-card">
          <div class="mode-guide-card__title">
            <h3>{{ gt(card.title) }}</h3>
            <span>{{ gt(card.badge) }}</span>
          </div>
          <ul>
            <li v-for="point in card.points" :key="point">{{ gt(point) }}</li>
          </ul>
          <p>{{ gt(card.hint) }}</p>
        </article>
      </div>

      <div class="tutorial-screenshot-pair">
        <img :src="optionsImage" :alt='gt("Pindou Puppy 模式和尺寸选择")' loading="lazy" />
        <img :src="loadingImage" :alt='gt("Pindou Puppy 生成进度")' loading="lazy" />
      </div>
    </section>

    <section id="wallet" class="tutorial-section">
      <div class="tutorial-section__heading">
        <span class="tutorial-kicker">03</span>
        <LiftTitle as="h2" :text="gt('积分 / 会员 / CDK 怎么用')"/>
        <p>{{ gt("一句话：AI 用积分，普通模式免费不限次，CDK 可直接兑换到账户或设备。") }}</p>
      </div>

      <div class="wallet-grid">
        <article v-for="item in walletItems" :key="item.title" class="wallet-card">
          <img :src="item.image" :alt="gt(item.alt)" loading="lazy" />
          <div>
            <h3>{{ gt(item.title) }}</h3>
            <p>{{ gt(item.text) }}</p>
          </div>
        </article>
      </div>
    </section>

    <section id="faq" class="tutorial-section faq-section">
      <div class="tutorial-section__heading">
        <span class="tutorial-kicker">04</span>
        <LiftTitle as="h2" :text="gt('避坑 / FAQ')"/>
        <p>{{ gt("先把容易翻车的点记住，后面就省很多豆。") }}</p>
      </div>

      <div class="faq-list">
        <article>
          <h3>{{ gt("尺寸怎么选？") }}</h3>
          <p>{{ gt("第一次建议 52 格起步。26 格豆少但细节糊；78/104 更精细，豆数和时间也更高。") }}</p>
        </article>
        <article>
          <h3>{{ gt("为什么不像本人？") }}</h3>
          <p>{{ gt("拼豆是低分辨率图纸，发型、眼睛、嘴巴和标志性衣服最重要。真人照片建议用 AI 模式。") }}</p>
        </article>
        <article>
          <h3>{{ gt("颜色不满意怎么办？") }}</h3>
          <p>{{ gt("进编辑器点格改色，或者用“全局替换”把某个色号一次性换掉。") }}</p>
        </article>
        <article>
          <h3>{{ gt("下载后怎么保存？") }}</h3>
          <p>{{ gt("电脑会下载 PNG；手机端优先用分享面板保存，浏览器不支持时可打开高清图后长按保存。") }}</p>
        </article>
      </div>
    </section>

    <section class="tutorial-cta">
      <span class="tutorial-kicker">Ready</span>
      <LiftTitle as="h2" :text="gt('现在做一张自己的拼豆图纸')"/>
      <p>{{ gt("先上传一张你喜欢的照片，Pindou Puppy 会帮你整理成可编辑、可下载、可保存的图纸。") }}</p>
      <RouterLink class="pd-btn pd-btn--primary" to="/tools">{{ gt("现在去上传") }}</RouterLink>
    </section>
  </section>
</template>

<style scoped>
.tutorial-page {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: clamp(18px, 3vw, 28px);
  padding-bottom: 36px;
}

.tutorial-hero,
.tutorial-section,
.tutorial-cta {
  min-width: 0;
  border: 1px solid rgba(242, 247, 250, 0.88);
  border-radius: 30px;
  background:
    radial-gradient(circle at 14% 10%, rgba(242, 247, 250, 0.75), transparent 28%),
    radial-gradient(circle at 92% 4%, rgba(237, 246, 232, 0.82), transparent 30%),
    rgba(255, 255, 255, 0.9);
  box-shadow: var(--pd-shadow-float);
}

.tutorial-hero {
  display: grid;
  grid-template-columns: minmax(0, 0.92fr) minmax(320px, 1.08fr);
  gap: clamp(20px, 4vw, 42px);
  align-items: center;
  padding: clamp(24px, 5vw, 48px);
}

.tutorial-hero__copy {
  display: grid;
  min-width: 0;
  grid-template-columns: minmax(0, 1fr);
  gap: 16px;
  align-content: center;
}

.tutorial-kicker {
  width: fit-content;
  border: 1px solid rgba(255, 255, 255, 0.62);
  border-radius: var(--pd-r-tag);
  background: rgba(242, 247, 250, 0.34);
  color: var(--pd-orange);
  font-size: 12px;
  font-weight: 600;
  padding: 6px 10px;
  -webkit-backdrop-filter: blur(6px);
  backdrop-filter: blur(6px);
}

.tutorial-hero h1,
.tutorial-section h2,
.tutorial-cta h2 {
  margin: 0;
  color: var(--pd-fg-1);
  font-family: var(--pd-font-body);
  font-weight: 600;
  line-height: 1.16;
  letter-spacing: 0;
}

.tutorial-hero h1 {
  font-size: clamp(38px, 6vw, 68px);
}

.tutorial-hero p,
.tutorial-section__heading p,
.tutorial-cta p {
  margin: 0;
  color: var(--pd-fg-2);
  font-size: clamp(15px, 1.8vw, 18px);
  font-weight: 500;
  line-height: 1.8;
}

.tutorial-hero__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-top: 8px;
}

.tutorial-hero__actions .pd-btn {
  min-height: 48px;
  padding: 0 22px;
}

.tutorial-hero__actions svg {
  width: 18px;
  height: 18px;
  stroke: currentColor;
  stroke-width: 2.4;
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.tutorial-secondary {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(134, 162, 184, 0.28);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--pd-fg-1);
  font-weight: 600;
  text-decoration: none;
  padding: 0 18px;
  transition:
    transform 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out),
    border-color 180ms var(--pd-ease-out);
}

.tutorial-secondary:hover {
  border-color: rgba(134, 162, 184, 0.48);
  box-shadow: 0 12px 22px rgba(134, 162, 184, 0.14);
  transform: translateY(-1px);
}

.tutorial-hero__media,
.flow-card,
.mode-guide-card,
.wallet-card,
.faq-list article {
  border: 1px solid rgba(242, 247, 250, 0.78);
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 16px 38px rgba(45, 45, 45, 0.08);
}

.tutorial-hero__media {
  overflow: hidden;
  border-radius: 24px;
  padding: 12px;
}

.tutorial-hero__media img,
.flow-card img,
.tutorial-screenshot-pair img,
.wallet-card img {
  width: 100%;
  display: block;
  border-radius: 18px;
  object-fit: cover;
  background: #fff;
}

.tutorial-hero__media img {
  aspect-ratio: 16 / 10;
}

.tutorial-anchor-nav {
  position: sticky;
  top: calc(var(--app-header-height) + 10px);
  z-index: 3;
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 10px;
  border: 1px solid rgba(242, 247, 250, 0.8);
  border-radius: 999px;
  background: rgba(235, 243, 249, 0.9);
  box-shadow: 0 12px 28px rgba(45, 45, 45, 0.06);
  -webkit-backdrop-filter: blur(14px);
  backdrop-filter: blur(14px);
  scrollbar-width: none;
}

.tutorial-anchor-nav::-webkit-scrollbar {
  display: none;
}

.tutorial-anchor-nav a {
  flex: 0 0 auto;
  min-height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
  border-radius: 999px;
  color: var(--pd-fg-1);
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  padding: 0 13px;
  transition:
    transform 180ms var(--pd-ease-out),
    background 180ms var(--pd-ease-out),
    border-color 180ms var(--pd-ease-out);
}

.tutorial-anchor-nav a:hover {
  border-color: rgba(134, 162, 184, 0.34);
  background: rgba(235, 243, 249, 0.86);
  transform: translateY(-1px);
}

.tutorial-section,
.tutorial-cta {
  display: grid;
  gap: clamp(16px, 3vw, 24px);
  padding: clamp(22px, 4vw, 36px);
  scroll-margin-top: 120px;
}

.tutorial-section__heading {
  display: grid;
  gap: 10px;
}

.tutorial-section h2,
.tutorial-cta h2 {
  font-size: clamp(28px, 4.5vw, 46px);
}

.flow-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.flow-card {
  position: relative;
  display: grid;
  gap: 14px;
  border-radius: 22px;
  padding: 14px;
  transition:
    transform 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out);
}

.flow-card:hover,
.mode-guide-card:hover,
.wallet-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 20px 46px rgba(134, 162, 184, 0.14);
}

.flow-card__index {
  position: absolute;
  top: 22px;
  left: 22px;
  min-width: 34px;
  height: 34px;
  display: inline-grid;
  place-items: center;
  border-radius: 999px;
  background: var(--pd-gradient);
  color: var(--pd-fg-1);
  font-weight: 600;
  box-shadow: 0 10px 22px rgba(134, 162, 184, 0.22);
}

.flow-card img {
  aspect-ratio: 16 / 10;
}

.flow-card h3,
.mode-guide-card h3,
.wallet-card h3,
.faq-list h3 {
  margin: 0;
  color: var(--pd-fg-1);
  font-size: 20px;
  font-weight: 600;
  line-height: 1.25;
}

.flow-card p,
.mode-guide-card p,
.wallet-card p,
.faq-list p {
  margin: 8px 0 0;
  color: var(--pd-fg-2);
  font-size: 14px;
  font-weight: 500;
  line-height: 1.75;
}

.mode-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.mode-guide-card {
  display: grid;
  gap: 16px;
  border-radius: 24px;
  padding: 22px;
}

.mode-guide-card__title {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
}

.mode-guide-card__title span {
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: var(--pd-r-tag);
  background: rgba(242, 247, 250, 0.38);
  color: var(--pd-orange);
  font-size: 12px;
  font-weight: 600;
  padding: 5px 8px;
}

.mode-guide-card ul {
  display: grid;
  gap: 9px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.mode-guide-card li {
  position: relative;
  color: var(--pd-fg-1);
  font-size: 14px;
  font-weight: 850;
  line-height: 1.6;
  padding-left: 18px;
}

.mode-guide-card li::before {
  content: "";
  position: absolute;
  top: 0.68em;
  left: 0;
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: var(--pd-orange);
}

.tutorial-screenshot-pair,
.wallet-grid,
.faq-list {
  display: grid;
  gap: 14px;
}

.tutorial-screenshot-pair {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.tutorial-screenshot-pair img {
  aspect-ratio: 16 / 10;
  border: 1px solid rgba(242, 247, 250, 0.78);
  box-shadow: 0 16px 38px rgba(45, 45, 45, 0.08);
}

.wallet-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.wallet-card {
  display: grid;
  gap: 12px;
  border-radius: 22px;
  padding: 14px;
  transition:
    transform 180ms var(--pd-ease-out),
    box-shadow 180ms var(--pd-ease-out);
}

.wallet-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.wallet-card {
  grid-template-columns: minmax(130px, 0.92fr) minmax(0, 1fr);
  align-items: center;
}

.wallet-card img {
  aspect-ratio: 4 / 3;
}

.faq-list {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.faq-list article {
  border-radius: 20px;
  padding: 20px;
}

.tutorial-cta {
  grid-template-columns: minmax(0, 1fr);
  justify-items: start;
}

.tutorial-cta > * {
  min-width: 0;
  max-width: 100%;
}

.tutorial-cta .pd-btn {
  min-height: 50px;
  padding: 0 26px;
}

@media (max-width: 900px) {
  .tutorial-hero {
    grid-template-columns: minmax(0, 1fr);
  }

  .wallet-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .wallet-card {
    grid-template-columns: minmax(120px, 0.72fr) minmax(0, 1fr);
  }
}

@media (max-width: 680px) {
  .tutorial-page {
    gap: 16px;
  }

  .tutorial-hero,
  .tutorial-section,
  .tutorial-cta {
    border-radius: 24px;
  }

  .tutorial-hero {
    padding: 22px;
  }

  .flow-grid,
  .mode-grid,
  .tutorial-screenshot-pair,
  .faq-list {
    grid-template-columns: minmax(0, 1fr);
  }

  .wallet-card {
    grid-template-columns: minmax(0, 1fr);
  }

  .tutorial-anchor-nav {
    border-radius: 22px;
  }
}

@media (max-width: 420px) {
  .tutorial-hero__actions {
    align-items: stretch;
    flex-direction: column;
  }

  .tutorial-hero__actions .pd-btn,
  .tutorial-secondary {
    width: 100%;
  }
}
</style>
