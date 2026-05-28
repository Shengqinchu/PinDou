<template>
  <MiniProgramLayout title="上传你的照片" backUrl="/pages/index/index" :scroll="true">
    <!-- ===== Empty state ===== -->
    <section v-if="!hasImage" class="upload__empty">
      <p class="upload__hint">选一张照片，30 秒生成专属拼豆图纸</p>

      <div class="upload__entries">
        <button type="button" class="upload__entry" @click="handlePick('camera')">
          <span class="upload__entry-icon" aria-hidden="true">
            拍
          </span>
          <span class="upload__entry-label">拍一张</span>
          <span class="upload__entry-sub">启用相机</span>
        </button>

        <button type="button" class="upload__entry" @click="handlePick('album')">
          <span class="upload__entry-icon" aria-hidden="true">
            图
          </span>
          <span class="upload__entry-label">从相册选</span>
          <span class="upload__entry-sub">本地图库</span>
        </button>
      </div>

      <aside class="upload__tip">
        <span class="upload__tip-icon" aria-hidden="true">
          i
        </span>
        <div class="upload__tip-body">
          <strong class="upload__tip-title">怎样的图效果最好？</strong>
          <span class="upload__tip-text">主体清晰、光线均匀、背景简单的近距离正脸/宠物照</span>
        </div>
      </aside>

      <div class="upload__spacer"></div>

      <p class="footnote upload__footnote">
        上传即同意 <span class="footnote-link" @click="openContract('agreement')">《用户服务协议》</span>
        与 <span class="footnote-link" @click="openContract('privacy')">《隐私政策说明》</span>，请勿上传他人肖像
      </p>
    </section>

    <!-- ===== Selected state ===== -->
    <section v-else class="upload__selected">
      <div class="upload__preview">
        <image class="upload__preview-img-element" :src="previewImage" mode="aspectFit" />
      </div>
      <div class="upload__actions">
        <button type="button" class="btn btn--secondary btn--md upload__retry" @click="handleRetry">
          重新选择
        </button>
        <button type="button" class="btn btn--primary btn--md upload__next" @click="handleNext">
          下一步
          <span class="upload__next-mark" aria-hidden="true">›</span>
        </button>
      </div>
    </section>

    <!-- ===== 敏感肖像授权合规 Modal (ADR-009) ===== -->
    <div v-if="showConsentModal" class="consent-modal-overlay">
      <div class="consent-modal pd-card">
        <h3 class="consent-modal__title">肖像隐私授权说明</h3>
        <scroll-view scroll-y class="consent-modal__scroll">
          <p class="consent-modal__text">
            PinDou 极其重视您的照片安全与肖像隐私。根据 <strong>ADR-009 隐私安全规范</strong>，我们向您郑重承诺：
          </p>
          <p class="consent-modal__text">
            1. <strong>隐私合规使用</strong>：您上传的照片仅流向专用的安全 AI 反代服务用于 Q 版化设计和拼豆量化，绝对不用于训练模型或泄露给任何第三方广告商。<br />
            2. <strong>30天自动销毁</strong>：上传的原图在 30 天后自动启动定时物理清理任务进行完全抹除，无法恢复。<br />
            3. <strong>数字资产归属</strong>：由照片生成出的拼豆图纸、色卡等交付物作为无敏感信息的数字资产，将永久留存并归属于您的个人账户。
          </p>
          <p class="consent-modal__text">
            您是否同意授权上传并调用 AI 拼豆设计系统？
          </p>
        </scroll-view>
        <div class="consent-modal__buttons">
          <button class="btn btn--secondary btn--sm" @click="handleConsentCancel">拒绝</button>
          <button class="btn btn--primary btn--sm" @click="handleConsentAgree">同意并继续</button>
        </div>
      </div>
    </div>
  </MiniProgramLayout>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
import MiniProgramLayout from '../../components/MiniProgramLayout.vue';
import { useUserStore } from '../../store/user';

const userStore = useUserStore();

// 路由传入的预设风格
const stylePreset = ref('cartoon_fallback');

onLoad((options: any) => {
  if (options.style) {
    stylePreset.value = options.style;
  }
});

const hasImage = ref(false);
const previewImage = ref('');
const showConsentModal = ref(false);
const pendingSourceType = ref<'camera' | 'album'>('album');

const handlePick = (type: 'camera' | 'album') => {
  pendingSourceType.value = type;
  
  // 拦截合规机制：用户必须进行单独的敏感人像同意
  if (!userStore.hasSensitiveConsent) {
    showConsentModal.value = true;
  } else {
    triggerChooseImage();
  }
};

const triggerChooseImage = () => {
  uni.chooseImage({
    count: 1,
    sizeType: ['compressed'], // 使用压缩版加速上传
    sourceType: pendingSourceType.value === 'camera' ? ['camera'] : ['album'],
    success: (res) => {
      previewImage.value = res.tempFilePaths[0];
      hasImage.value = true;
    },
    fail: (err) => {
      console.warn('选择图片被取消或失败:', err);
    }
  });
};

const handleRetry = () => {
  hasImage.value = false;
  previewImage.value = '';
};

const handleNext = () => {
  if (!previewImage.value) return;
  
  // 路由跳转至生成方式选择页，带上风格和原图临时路径
  uni.navigateTo({
    url: `/pages/generate/choice?style=${stylePreset.value}&image=${encodeURIComponent(previewImage.value)}`
  });
};

// 合规留痕
const handleConsentAgree = async () => {
  try {
    showConsentModal.value = false;
    uni.showLoading({ title: '授权留痕中...' });
    await userStore.giveConsent('sensitive');
    uni.hideLoading();
    // 授权留痕成功，调用相机或相册
    triggerChooseImage();
  } catch (e) {
    uni.hideLoading();
    uni.showToast({ title: '授权服务连接失败，请稍后重试', icon: 'none' });
  }
};

const handleConsentCancel = () => {
  showConsentModal.value = false;
  uni.showToast({ title: '需要同意肖像授权才能体验拼豆哦~', icon: 'none' });
};

const openContract = (type: 'agreement' | 'privacy') => {
  uni.navigateTo({
    url: `/pages/consent/consent?type=${type}`
  });
};
</script>

<style scoped lang="scss">
.upload__empty {
  width: 100%;
  height: 100%;
  padding: 28px 20px 24px;
  display: flex;
  flex-direction: column;
}

.upload__hint {
  text-align: center;
  font-size: 16px;
  font-weight: 500;
  color: var(--pd-fg-2);
  line-height: 1.4;
  margin: 0 0 24px;
}

/* ===== Two parallel entry cards ===== */
.upload__entries {
  display: flex;
  gap: 12px;
}

.upload__entry {
  flex: 1;
  height: 168px;
  appearance: none;
  cursor: pointer;
  font-family: inherit;
  color: var(--pd-fg-1);
  border-radius: var(--pd-r-card);
  background: rgba(255, 241, 246, 0.5);
  border: 1.5px dashed var(--pd-pink-200);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  transition: transform 180ms var(--pd-ease-out),
              background 220ms var(--pd-ease-out);
  padding: 0;
  line-height: normal;
  
  &:active {
    transform: scale(0.97);
    background: rgba(255, 241, 246, 0.8);
  }
}

.upload__entry-icon {
  width: 56px;
  height: 56px;
  border-radius: 999px;
  background: var(--pd-gradient-warm);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 6px 16px rgba(255, 142, 83, 0.28);
  font-size: 20px;
  font-weight: 800;
  line-height: 1;
}

.upload__entry-label {
  font-size: 15px;
  font-weight: 600;
}

.upload__entry-sub {
  font-size: 11px;
  color: var(--pd-fg-2);
}

/* ===== "What works best" tip card ===== */
.upload__tip {
  margin-top: 20px;
  padding: 14px 16px;
  border-radius: var(--pd-r-card);
  background: #FFF1E8;
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.upload__tip-icon {
  width: 22px;
  height: 22px;
  border-radius: 999px;
  background: var(--pd-gradient-warm);
  color: #fff;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 1px;
  font-size: 12px;
  font-weight: 800;
  line-height: 1;
}

.upload__tip-body {
  font-size: 12px;
  line-height: 1.6;
  color: var(--pd-fg-1);
}

.upload__tip-title {
  display: block;
  font-weight: 600;
}

.upload__tip-text { 
  color: var(--pd-fg-2); 
}

.upload__spacer { 
  flex: 1; 
}

.upload__footnote { 
  margin: 0; 
  text-align: center;
}

.footnote-link {
  color: var(--pd-pink-deep);
  display: inline;
  text-decoration: underline;
}

/* ===== Selected state ===== */
.upload__selected {
  width: 100%;
  height: 100%;
  padding: 20px 24px 24px;
  display: flex;
  flex-direction: column;
}

.upload__preview {
  flex: 1;
  border-radius: var(--pd-r-card);
  overflow: hidden;
  background: #fff;
  box-shadow: var(--pd-shadow-card);
  display: flex;
  align-items: center;
  justify-content: center;
  height: calc(100vh - 160px); /* 让预览图片撑高 */
}

.upload__preview-img-element {
  width: 100%;
  height: 100%;
}

.upload__actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

.upload__retry { 
  flex: 1; 
}

.upload__next  { 
  flex: 2; 
}

.upload__next-mark {
  margin-left: 4px;
  font-size: 20px;
  font-weight: 800;
  line-height: 1;
}

/* ===== Consent Modal ===== */
.consent-modal-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(45, 45, 45, 0.4);
  backdrop-filter: blur(4px);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.consent-modal {
  width: 100%;
  max-width: 327px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  background: #fff;
  z-index: 101;
}

.consent-modal__title {
  font-family: var(--pd-font-display);
  font-size: 18px;
  font-weight: 700;
  text-align: center;
  color: var(--pd-fg-1);
  margin-bottom: 12px;
}

.consent-modal__scroll {
  max-height: 220px;
  margin-bottom: 20px;
}

.consent-modal__text {
  font-size: 13px;
  line-height: 1.6;
  color: var(--pd-fg-2);
  margin-bottom: 10px;
  
  strong {
    color: var(--pd-fg-1);
  }
}

.consent-modal__buttons {
  display: flex;
  gap: 10px;
  
  button {
    flex: 1;
    padding: 10px 0;
  }
}
</style>
