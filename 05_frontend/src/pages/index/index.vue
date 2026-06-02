<template>
  <MiniProgramLayout variant="home" title="PinDou 拼豆" :scroll="true">
    <div class="home__container">
      <div class="home__hero-wash" aria-hidden="true"></div>

      <!-- ===== Hero copy ===== -->
      <section class="home__hero">
        <view class="home__headline">
          <span class="home__headline-line">30 秒生成你的</span>
          <span class="text-grad home__headline-keyword">拼豆图纸</span>
        </view>
        <p class="home__subtitle">上传一张照片，AI 自动转 Q 版输出图纸</p>
      </section>

      <!-- ===== Theme chips ===== -->
      <nav class="home__chips" aria-label="热门玩法">
        <navigator class="chip" url="/pages/upload/upload?style=q_pet">
          <span class="chip__icon" aria-hidden="true">
            宠
          </span>萌宠
        </navigator>
        <navigator class="chip" url="/pages/upload/upload?style=q_couple">
          <span class="chip__icon" aria-hidden="true">
            心
          </span>情侣
        </navigator>
        <navigator class="chip" url="/pages/upload/upload?style=q_portrait">
          <span class="chip__icon" aria-hidden="true">
            拍
          </span>自拍
        </navigator>
      </nav>

      <!-- ===== CTA ===== -->
      <div class="home__cta-wrap">
        <navigator
          class="btn btn--primary btn--block btn--lg home__cta"
          url="/pages/upload/upload"
          hover-class="none"
        >
          <span class="home__cta-icon" aria-hidden="true">+</span>
          立即上传照片
        </navigator>
        <p class="home__cta-hint">支持 JPG / PNG · 单张图片 ≤ 10MB</p>
      </div>

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
              <span class="tag tag--ai home__banner-badge">
                <span class="home__badge-mark" aria-hidden="true">AI</span>
                AI 生成
              </span>
              <image class="home__banner-image" :src="banner.image" mode="aspectFit" />
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
  min-height: 100%;
  padding: 18px 20px 28px;
  background: #fffaf0;
  overflow: hidden;
}

.home__hero-wash {
  position: absolute;
  top: -80px;
  right: -120px;
  width: 260px;
  height: 260px;
  border-radius: 44% 56% 52% 48%;
  background: rgba(255, 176, 132, 0.28);
  pointer-events: none;
  z-index: 0;
}

/* ===== Swiper / Carousel ===== */
.home__carousel-section {
  margin-top: 24px;
  margin-left: -20px;
  margin-right: -20px;
  position: relative;
  z-index: 1;
}

.home__swiper {
  height: 300px;
  width: 100%;
}

.home__banner {
  width: calc(100vw - 40px);
  max-width: 350px;
  height: 288px;
  margin: 0 0 0 20px;
  border: 1px solid rgba(229, 229, 229, 0.78);
  border-radius: 24px;
  background: #faf5e8;
  box-shadow: 0 12px 34px rgba(10, 10, 10, 0.06);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
  padding: 14px 14px 12px;
}

.home__banner-image {
  width: 100%;
  flex: 1;
  min-height: 0;
}

.home__banner-badge {
  position: absolute;
  top: 14px;
  left: 14px;
  z-index: 2;
  background: #ffb084;
  color: #0a0a0a;
  box-shadow: 0 8px 18px rgba(255, 176, 132, 0.26);
}

.home__badge-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  margin-right: 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.44);
  font-size: 8px;
  font-weight: 800;
  line-height: 1;
}

.home__banner-caption {
  padding: 12px 18px 0 2px;
  color: #0a0a0a;
  display: flex;
  align-items: center;
  justify-content: space-between;
  z-index: 1;
  border-top: 1px solid rgba(229, 229, 229, 0.72);
}

.home__banner-title {
  font-weight: 800;
  font-size: 14px;
  letter-spacing: 0;
}

.home__banner-meta {
  flex: 0 0 auto;
  white-space: nowrap;
  font-size: 11px;
  color: #6a6a6a;
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
  background: #ebe6d6;
  transition: all 280ms var(--pd-ease-out);
}

.home__dot--active {
  width: 18px;
  background: #0a0a0a;
}

/* ===== Hero copy ===== */
.home__hero {
  padding: 12px 0 0;
  text-align: left;
  position: relative;
  z-index: 1;
}

.home__headline {
  max-width: 360px;
  font-size: 34px;
  font-weight: 800;
  line-height: 1.08;
  letter-spacing: 0;
  color: #0a0a0a;
  margin: 0;
}

.home__headline-line,
.home__headline-keyword {
  display: block;
}

.home__headline-keyword {
  width: max-content;
  white-space: nowrap;
  color: #ff6b5a;
  background: none;
  -webkit-text-fill-color: currentColor;
}

.home__subtitle {
  max-width: 320px;
  margin: 14px 0 0;
  font-size: 15px;
  line-height: 1.65;
  color: #3a3a3a;
}

/* ===== Theme chips ===== */
.home__chips {
  margin: 18px 0 0;
  padding: 0;
  display: flex;
  gap: 8px;
  justify-content: flex-start;
  flex-wrap: wrap;
}

.home__chips .chip {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 999px;
  background: #f5f0e0;
  border: 1px solid rgba(229, 229, 229, 0.75);
  color: #0a0a0a;
  text-decoration: none;
  transition: transform 180ms var(--pd-ease-out);
}

.home__chips .chip:active { 
  transform: scale(0.96); 
}

.chip__icon {
  font-size: 12px;
  font-weight: 800;
  line-height: 1;
}

/* ===== CTA block ===== */
.home__cta-wrap {
  width: 100%;
  max-width: 360px;
  padding: 20px 0 0;
  position: relative;
  z-index: 1;
}

.home__cta { 
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  overflow: hidden;
  height: 54px; 
  font-size: 17px; 
  letter-spacing: 0; 
  opacity: 1;
  background: #0a0a0a;
  color: #fff;
  box-shadow: 0 12px 28px rgba(10, 10, 10, 0.18);
}

.home__cta-icon {
  width: 20px;
  height: 20px;
  margin-right: 4px;
  border-radius: 999px;
  border: 2px solid currentColor;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  line-height: 1;
  font-weight: 800;
}

.home__cta-hint {
  margin: 10px 0 0;
  text-align: left;
  font-size: 11px;
  color: #6a6a6a;
}

/* #ifdef H5 */
@media (min-width: 1024px) {
  .home__container {
    display: grid;
    grid-template-columns: minmax(0, 520px) minmax(460px, 520px);
    grid-template-areas:
      "hero sample"
      "chips sample"
      "cta sample";
    grid-template-rows: auto auto auto;
    align-content: start;
    align-items: start;
    justify-content: space-between;
    column-gap: 96px;
    min-height: auto;
    padding: 88px 0 92px;
    background: transparent;
    overflow: visible;
  }

  .home__hero-wash {
    display: none;
  }

  .home__hero {
    grid-area: hero;
    padding: 0;
  }

  .home__headline {
    max-width: 620px;
    font-size: clamp(56px, 5.2vw, 72px);
    line-height: 1;
    font-weight: 800;
  }

  .home__subtitle {
    max-width: 520px;
    margin-top: 24px;
    font-size: 20px;
    line-height: 1.55;
  }

  .home__chips {
    grid-area: chips;
    margin-top: 36px;
    gap: 12px;
  }

  .home__chips .chip {
    min-height: 44px;
    padding: 0 18px;
    font-size: 15px;
  }

  .home__cta-wrap {
    grid-area: cta;
    width: 360px;
    padding-top: 28px;
  }

  .home__cta-hint {
    font-size: 13px;
  }

  .home__carousel-section {
    grid-area: sample;
    width: 100%;
    margin-top: 0;
    margin-left: 0;
    margin-right: 0;
  }

  .home__swiper {
    height: 520px;
  }

  .home__banner {
    height: 506px;
    max-width: none;
    margin: 0 auto;
    padding: 22px 22px 18px;
    border-radius: 24px;
    background: #faf5e8;
    box-shadow: 0 22px 60px rgba(10, 10, 10, 0.08);
  }

  .home__banner-image {
    padding: 8px 0 0;
  }

  .home__banner-badge {
    top: 22px;
    left: 22px;
  }

  .home__banner-caption {
    padding: 16px 28px 0 2px;
  }

  .home__banner-title {
    font-size: 22px;
  }

  .home__banner-meta {
    font-size: 14px;
  }

  .home__dots {
    margin-top: 14px;
  }
}
/* #endif */
</style>
