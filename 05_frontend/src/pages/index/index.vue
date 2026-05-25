<template>
  <MiniProgramLayout variant="home" title="PinDou 拼豆" :scroll="true">
    <div class="home__container">
      <div class="home__hero-wash" aria-hidden="true"></div>

      <!-- ===== Banner carousel ===== -->
      <section class="home__carousel-section" aria-label="拼豆样张">
        <swiper 
          class="home__swiper" 
          :autoplay="autoplay" 
          :interval="4000" 
          :current="activeIndex"
          @change="onSwiperChange"
          @pointerdown="stopAutoplay"
          @pointerup="startAutoplay"
        >
          <swiper-item v-for="(banner, index) in banners" :key="index">
            <div class="home__banner">
              <image class="home__banner-image" :src="banner.image" mode="aspectFit" />
              <span class="tag tag--ai home__banner-badge">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="margin-right: 2px;">
                  <path d="M9.94 14.06 2 12l7.94-2.06L12 2l2.06 7.94L22 12l-7.94 2.06L12 22z"/>
                </svg>
                AI 生成
              </span>
              <div class="home__banner-caption">
                <span class="home__banner-title">{{ banner.title }}</span>
                <span class="home__banner-meta">{{ banner.meta }}</span>
              </div>
            </div>
          </swiper-item>
        </swiper>

        <!-- 自定义胶囊 Indicators -->
        <nav class="home__dots" aria-label="样张选择">
          <button 
            v-for="(banner, index) in banners" 
            :key="index"
            type="button" 
            class="home__dot" 
            :class="{ 'home__dot--active': activeIndex === index }" 
            @click="goToSlide(index)" 
            :aria-label="'第 ' + (index + 1) + ' 张'"
          ></button>
        </nav>
      </section>

      <!-- ===== Hero copy ===== -->
      <section class="home__hero">
        <view class="home__headline">
          30 秒生成你的<span class="text-grad">拼豆图纸</span>
        </view>
        <p class="home__subtitle">上传一张照片，AI 自动转 Q 版输出图纸</p>
      </section>

      <!-- ===== Theme chips ===== -->
      <nav class="home__chips" aria-label="热门玩法">
        <navigator class="chip" url="/pages/upload/upload?style=q_pet">
          <span class="chip__icon" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="display: block;">
              <path d="M12 5c.67 0 1.35.09 2 .26 1.78-2 5.03-2.84 6.42-2.26 1.4.58-.42 7-.42 7 .57 1.07 1 2.24 1 3.44C21 17.9 16.97 21 12 21s-9-3-9-7.56c0-1.25.5-2.4 1-3.44 0 0-1.89-6.42-.5-7 1.39-.58 4.72.23 6.5 2.23A9.04 9.04 0 0 1 12 5Z"/>
              <path d="M8 14v.5"/><path d="M16 14v.5"/>
              <path d="M11.25 16.25h1.5L12 17l-.75-.75Z"/>
            </svg>
          </span>萌宠
        </navigator>
        <navigator class="chip" url="/pages/upload/upload?style=q_couple">
          <span class="chip__icon" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="display: block;">
              <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.29 1.51 4.04 3 5.5l7 7Z"/>
            </svg>
          </span>情侣
        </navigator>
        <navigator class="chip" url="/pages/upload/upload?style=q_portrait">
          <span class="chip__icon" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="display: block;">
              <path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3Z"/>
              <circle cx="12" cy="13" r="3"/>
            </svg>
          </span>自拍
        </navigator>
      </nav>

      <!-- ===== CTA ===== -->
      <div class="home__cta-wrap">
        <navigator class="btn btn--primary btn--block btn--lg home__cta" url="/pages/upload/upload">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="margin-right: 4px; display: block;">
            <path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3Z"/>
            <circle cx="12" cy="13" r="3"/>
          </svg>
          立即上传照片
        </navigator>
        <p class="home__cta-hint">支持 JPG / PNG · 单张图片 ≤ 10MB</p>
      </div>
    </div>
  </MiniProgramLayout>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import MiniProgramLayout from '../../components/MiniProgramLayout.vue';

// 样张轮播数据
const banners = [
  { image: '/static/assets/bead-cat.svg', title: '萌宠拼豆', meta: '24×24 · 7 色' },
  { image: '/static/assets/bead-heart.svg', title: '情侣拼豆', meta: '28×28 · 5 色' },
  { image: '/static/assets/bead-bunny.svg', title: '自拍 Q 版', meta: '32×32 · 8 色' }
];

const activeIndex = ref(0);
const autoplay = ref(true);

const onSwiperChange = (e: any) => {
  activeIndex.value = e.detail.current;
};

const goToSlide = (index: number) => {
  activeIndex.value = index;
};

const stopAutoplay = () => {
  autoplay.value = false;
};

const startAutoplay = () => {
  autoplay.value = true;
};
</script>

<style scoped lang="scss">
.home__container {
  position: relative;
  height: 100%;
}

/* soft pink wash behind the hero, fades out before the chips */
.home__hero-wash {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 240px;
  background: radial-gradient(120% 100% at 50% 0%,
              #FFE4EE 0%, rgba(255, 228, 238, 0) 70%);
  pointer-events: none;
  z-index: 0;
}

/* ===== Swiper / Carousel ===== */
.home__carousel-section {
  padding-top: 16px;
  position: relative;
  z-index: 1;
}

.home__swiper {
  height: 188px;
  width: 100%;
}

.home__banner {
  width: 327px;
  height: 188px;
  margin: 0 auto;
  border-radius: var(--pd-r-card);
  background: linear-gradient(135deg, #FFF1E8 0%, #FFE4EE 100%);
  overflow: hidden;
  box-shadow: var(--pd-shadow-card);
  position: relative;
}

.home__banner-image {
  width: 100%;
  height: 100%;
}

.home__banner-badge {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 2;
}

.home__banner-caption {
  position: absolute;
  left: 0; right: 0; bottom: 0;
  padding: 24px 14px 12px;
  background: linear-gradient(180deg,
              rgba(45, 45, 45, 0) 0%,
              rgba(45, 45, 45, 0.55) 100%);
  color: #fff;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  z-index: 1;
}

.home__banner-title {
  font-weight: 700;
  font-size: 14px;
  letter-spacing: 0.2px;
}

.home__banner-meta {
  font-size: 11px;
  opacity: 0.88;
}

/* ===== Page dots ===== */
.home__dots {
  display: flex;
  gap: 6px;
  justify-content: center;
  margin-top: 12px;
}

.home__dot {
  appearance: none;
  border: 0;
  padding: 0;
  cursor: pointer;
  height: 6px;
  width: 6px;
  border-radius: 999px;
  background: var(--pd-pink-100);
  transition: all 280ms var(--pd-ease-out);
}

.home__dot--active {
  width: 18px;
  background: var(--pd-pink);
}

/* ===== Hero copy ===== */
.home__hero {
  padding: 28px 24px 0;
  text-align: center;
  position: relative;
  z-index: 1;
}

.home__headline {
  font-size: 26px;
  font-weight: 800;
  line-height: 1.3;
  letter-spacing: -0.01em;
  color: var(--pd-fg-1);
  margin: 0;
}

.home__subtitle {
  margin: 10px 0 0;
  font-size: 13px;
  line-height: 1.55;
  color: var(--pd-fg-2);
}

/* ===== Theme chips ===== */
.home__chips {
  margin: 16px 0 0;
  padding: 0 16px;
  display: flex;
  gap: 8px;
  justify-content: center;
}

.home__chips .chip {
  text-decoration: none;
  transition: transform 180ms var(--pd-ease-out);
}

.home__chips .chip:active { 
  transform: scale(0.96); 
}

/* ===== CTA block ===== */
.home__cta-wrap {
  padding: 24px 24px 0;
  position: relative;
  z-index: 1;
}

.home__cta { 
  height: 54px; 
  font-size: 17px; 
  letter-spacing: 0.5px; 
}

.home__cta-hint {
  margin: 10px 0 0;
  text-align: center;
  font-size: 11px;
  color: var(--pd-fg-3);
}
</style>
