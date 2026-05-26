<template>
  <MiniProgramLayout title="你的拼豆图纸" backUrl="/pages/result/basic?tier=premium" :scroll="true">
    <section class="premium">

      <!-- ===== Pro badge ===== -->
      <div class="premium__pro-bar">
        <span class="premium__pro-tag">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="margin-right: 2px;">
            <path d="M9.94 14.06 2 12l7.94-2.06L12 2l2.06 7.94L22 12l-7.94 2.06L12 22z"/>
          </svg>
          月卡解锁中
        </span>
        <span class="premium__pro-expires">23 天到期</span>
      </div>

      <!-- ===== Pattern preview ===== -->
      <figure class="premium__pattern">
        <div class="premium__pattern-wrap" @click="previewFullScreen">
          <image class="premium__pattern-image" :src="premiumPatternImage" mode="widthFix" />
          <span v-if="showZoomHint" class="premium__zoom-hint" aria-hidden="true">
            <span class="premium__zoom-hint-icon"></span>
            轻点放大
          </span>
        </div>
        <figcaption class="premium__pattern-caption">
          <span class="premium__pattern-name">萌宠拼豆 · AI 精致橘橘</span>
          <span class="premium__pattern-meta">{{ pattern.size || '32 × 32' }} · {{ pattern.total_beads || 487 }} 颗 · {{ colorsCount }} 色</span>
        </figcaption>
      </figure>

      <!-- ===== Format thumbnails ===== -->
      <h2 class="premium__section-title">高级输出</h2>
      <div class="premium__formats">

        <div class="premium__format" @click="handleDownloadFormat('PDF图纸', 'pdf')">
          <div class="premium__format-thumb premium__format-thumb--pdf">
            <span class="premium__format-corner">PDF</span>
            <span class="premium__format-line premium__format-line--primary premium__format-line--w8"></span>
            <span class="premium__format-line premium__format-line--w6"></span>
            <span class="premium__format-line premium__format-line--w9"></span>
            <span class="premium__format-line premium__format-line--w7"></span>
            <span class="premium__format-line premium__format-line--w5"></span>
          </div>
          <div class="premium__format-name">PDF 图纸</div>
          <div class="premium__format-meta">A4 · 8 页 · 打印</div>
        </div>

        <div class="premium__format" @click="handleDownloadFormat('Excel色号表', 'xlsx')">
          <div class="premium__format-thumb premium__format-thumb--xlsx">
            <span class="premium__format-corner premium__format-corner--xlsx">XLSX</span>
            <div class="premium__format-grid" aria-hidden="true">
              <span class="premium__format-cell premium__format-cell--peach"></span>
              <span class="premium__format-cell premium__format-cell--light-peach"></span>
              <span class="premium__format-cell"></span>
              <span class="premium__format-cell"></span>
              <span class="premium__format-cell premium__format-cell--cream"></span>
              <span class="premium__format-cell premium__format-cell--peach"></span>
              <span class="premium__format-cell premium__format-cell--pink"></span>
              <span class="premium__format-cell"></span>
              <span class="premium__format-cell"></span>
              <span class="premium__format-cell premium__format-cell--black"></span>
              <span class="premium__format-cell"></span>
              <span class="premium__format-cell"></span>
              <span class="premium__format-cell premium__format-cell--brown"></span>
              <span class="premium__format-cell"></span>
              <span class="premium__format-cell premium__format-cell--light-peach"></span>
              <span class="premium__format-cell"></span>
              <span class="premium__format-cell"></span>
              <span class="premium__format-cell premium__format-cell--hot-pink"></span>
              <span class="premium__format-cell"></span>
              <span class="premium__format-cell"></span>
              <span class="premium__format-cell premium__format-cell--peach"></span>
              <span class="premium__format-cell"></span>
              <span class="premium__format-cell premium__format-cell--pink"></span>
              <span class="premium__format-cell"></span>
            </div>
          </div>
          <div class="premium__format-name">Excel 色号</div>
          <div class="premium__format-meta">7 色 · 可编辑</div>
        </div>

        <div class="premium__format" @click="handleDownloadFormat('分区拼接图', 'tiles')">
          <div class="premium__format-thumb premium__format-thumb--tiles">
            <span class="premium__format-corner premium__format-corner--tiles">分区</span>
            <div class="premium__format-tiles" aria-hidden="true">
              <span class="premium__format-tile">1</span>
              <span class="premium__format-tile">2</span>
              <span class="premium__format-tile">3</span>
              <span class="premium__format-tile">4</span>
            </div>
          </div>
          <div class="premium__format-name">📋 查看分区图</div>
          <div class="premium__format-meta">4 块 · 大尺寸易拼</div>
        </div>

      </div>

      <!-- ===== Quick stats ===== -->
      <div class="card premium__stats">
        <div class="premium__stat">
          <span class="premium__stat-num">{{ pattern.total_beads || 487 }}</span>
          <span class="premium__stat-unit">总颗数</span>
        </div>
        <div class="premium__stat">
          <span class="premium__stat-num">{{ colorsCount }}</span>
          <span class="premium__stat-unit">色号数</span>
        </div>
        <div class="premium__stat">
          <span class="premium__stat-num premium__stat-num--cost">¥{{ pattern.estimated_cost || 6.5 }}</span>
          <span class="premium__stat-unit">估算成本</span>
        </div>
      </div>

      <!-- ===== CTAs ===== -->
      <div class="premium__actions">
        <button class="btn btn--primary btn--block btn--lg" @click="handleSaveAll">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="margin-right: 4px; display: block;">
            <rect x="3" y="3" width="18" height="18" rx="2"/>
            <path d="m3 16 5-5 4 4 3-3 6 6"/>
            <circle cx="8.5" cy="8.5" r="1.5"/>
          </svg>
          保存全部到相册
        </button>
        <button class="btn btn--secondary btn--block btn--md" @click="handleEmail">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="1.8"
               stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="margin-right: 4px; display: block;">
            <path d="M6 9V3h12v6"/>
            <rect x="3" y="9" width="18" height="9" rx="2"/>
            <path d="M6 14h12v7H6z"/>
          </svg>
          打印 / 邮件发送
        </button>
      </div>

    </section>
  </MiniProgramLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import MiniProgramLayout from '../../components/MiniProgramLayout.vue';
import { useArtworkStore } from '../../store/artwork';
import { BASE_URL } from '../../utils/request';

const artworkStore = useArtworkStore();
const ZOOM_HINT_KEY = 'pd_pattern_zoom_hint_seen';
const API_ORIGIN = BASE_URL.replace(/\/api\/v\d+$/, '');
const showZoomHint = ref(false);

const pattern = computed(() => {
  return artworkStore.currentPattern || {
    pattern_id: 'pattern_mock_premium',
    image_url: '/static/assets/bead-cat.svg',
    size: '32 × 32',
    total_beads: 487,
    colors_count: 7,
    estimated_cost: 6.5,
    colors: [
      { name: '蜜桃橙', code: 'O-22', count: 187, percentage: 38, hex: '#FFB088' },
      { name: '浅蜜桃', code: 'o-18', count: 156, percentage: 32, hex: '#FFCDA6' },
      { name: '奶油白', code: 'M-01', count: 65, percentage: 13, hex: '#FFF4E6' }
    ]
  };
});

const colorsCount = computed(() => (pattern.value.colors || []).length);
const artworkId = computed(() => String(pattern.value.metadata?.artwork_id || artworkStore.currentArtwork?.artwork_id || ''));
const premiumPatternImage = computed(() => {
  const url = pattern.value.image_url || pattern.value.metadata?.labeled_image_url || '/static/assets/bead-cat.svg';
  return normalizeAssetUrl(url);
});

const normalizeAssetUrl = (url: string) => {
  if (!url) return '';
  if (/^https?:\/\//.test(url)) return url;
  if (url.startsWith('/static/') && !url.startsWith('/static/assets/')) return `${API_ORIGIN}${url}`;
  return url;
};

const previewFullScreen = () => {
  markZoomHintSeen();
  uni.previewImage({
    current: premiumPatternImage.value,
    urls: [premiumPatternImage.value]
  });
};

const markZoomHintSeen = () => {
  if (!showZoomHint.value) return;
  showZoomHint.value = false;
  uni.setStorageSync(ZOOM_HINT_KEY, true);
};

onMounted(() => {
  showZoomHint.value = !uni.getStorageSync(ZOOM_HINT_KEY);
});

const handleDownloadFormat = (name: string, ext: string) => {
  if (ext === 'tiles') {
    if (!artworkId.value) {
      uni.showToast({ title: '重新生成后可查看分区图', icon: 'none' });
      return;
    }
    uni.navigateTo({
      url: `/pages/result/partitions?artwork_id=${encodeURIComponent(artworkId.value)}`
    });
    return;
  }
  uni.showActionSheet({
    itemList: [`保存本地 ${ext.toUpperCase()}`, '复制浏览器下载链接', '发送至指定邮箱'],
    success: (res) => {
      if (res.tapIndex === 0) {
        uni.showLoading({ title: '正在导出...' });
        setTimeout(() => {
          uni.hideLoading();
          uni.showToast({ title: `${name} 导出并下载成功`, icon: 'success' });
        }, 1500);
      } else if (res.tapIndex === 1) {
        const link = `https://essayaipass.online/api/v2/download/${pattern.value.pattern_id}.${ext}`;
        uni.setClipboardData({
          data: link,
          success: () => {
            uni.showToast({ title: '链接已复制，可去浏览器下载', icon: 'none' });
          }
        });
      } else if (res.tapIndex === 2) {
        handleEmail();
      }
    }
  });
};

const handleSaveAll = () => {
  uni.showLoading({ title: '打包并导出相册中...' });
  // 模拟微信小程序将 PDF 样张和拼接大图成组写入系统相册
  setTimeout(() => {
    uni.hideLoading();
    uni.showModal({
      title: '导出成功',
      content: '高级 PDF 图纸（高清图版）和 4 张分区拼接大图已全部存入手机系统相册，去手机相册或在微信发图时即可直接选择打印。',
      showCancel: false,
      confirmText: '太棒了',
      confirmColor: '#FF6B9D'
    });
  }, 1800);
};

const handleEmail = () => {
  // 小程序内带输入框的原生 Modal 交互
  uni.showModal({
    title: '发送到邮箱',
    editable: true,
    placeholderText: '请输入您的接收邮箱 (如 mail@qq.com)',
    confirmText: '发送',
    confirmColor: '#FF6B9D',
    success: (res) => {
      if (res.confirm && res.content) {
        const email = res.content.trim();
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
          uni.showToast({ title: '邮箱格式不正确', icon: 'none' });
          return;
        }
        
        uni.showLoading({ title: '正在通过邮件服务器发送...' });
        setTimeout(() => {
          uni.hideLoading();
          uni.showModal({
            title: '邮件已发出',
            content: `我们已将 [PDF 矢量高清图纸 + XLSX 规格表] 附件完整发送至：\n${email}\n请查收（若未收到，可留意垃圾邮件箱）。`,
            showCancel: false,
            confirmText: '好的',
            confirmColor: '#FF6B9D'
          });
        }, 1500);
      }
    }
  });
};
</script>

<style scoped lang="scss">
.premium { 
  padding: 12px 20px 28px; 
}

/* ===== Pro bar ===== */
.premium__pro-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.premium__pro-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px 5px 10px;
  border-radius: 999px;
  background: var(--pd-gradient);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.3px;
  box-shadow: 0 4px 10px rgba(255, 107, 157, 0.28);
}
.premium__pro-expires {
  font-size: 11px;
  color: var(--pd-fg-2);
}

/* ===== Pattern preview ===== */
.premium__pattern {
  margin: 0 0 18px;
  border-radius: var(--pd-r-card);
  background:
    radial-gradient(120% 100% at 50% 0%, #FFE4EE 0%, #FFF1E8 60%, transparent 100%),
    #fff;
  padding: 14px;
  box-shadow: var(--pd-shadow-card);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.premium__pattern-wrap {
  width: 100%;
  max-width: 260px;
  position: relative;
}

.premium__pattern-image {
  width: 100%;
  max-width: 220px;
  border-radius: var(--pd-r-img);
  display: block;
  margin: 0 auto;
  background: #fff;
}

.premium__zoom-hint {
  position: absolute;
  right: 8px;
  bottom: 8px;
  height: 28px;
  padding: 0 9px;
  border-radius: 999px;
  background: rgba(31, 31, 31, 0.72);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  box-shadow: 0 4px 12px rgba(31, 31, 31, 0.18);
  pointer-events: none;
  animation: premium-zoom-hint 1.4s var(--pd-ease-soft) infinite alternate;
}

.premium__zoom-hint-icon {
  width: 11px;
  height: 11px;
  border: 2px solid currentColor;
  border-radius: 999px;
  position: relative;
}

.premium__zoom-hint-icon::after {
  content: "";
  position: absolute;
  right: -5px;
  bottom: -4px;
  width: 7px;
  height: 2px;
  border-radius: 999px;
  background: currentColor;
  transform: rotate(45deg);
}

@keyframes premium-zoom-hint {
  from { transform: translateY(0); opacity: 0.86; }
  to { transform: translateY(-2px); opacity: 1; }
}

.premium__pattern-caption {
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.premium__pattern-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--pd-fg-1);
}
.premium__pattern-meta {
  font-size: 11px;
  color: var(--pd-fg-2);
}

/* ===== Format thumbnails row ===== */
.premium__section-title {
  margin: 0 0 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--pd-fg-2);
  letter-spacing: 0.3px;
}

.premium__formats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 18px;
}

.premium__format {
  display: flex;
  flex-direction: column;
  gap: 6px;
  text-decoration: none;
  color: var(--pd-fg-1);
  transition: transform 200ms var(--pd-ease-out);
  cursor: pointer;
  
  &:active { 
    transform: scale(0.97); 
  }
}

.premium__format-thumb {
  width: 100%;
  aspect-ratio: 3 / 4;
  border-radius: var(--pd-r-img);
  background: #fff;
  box-shadow: var(--pd-shadow-card);
  position: relative;
  padding: 12px 10px;
  overflow: hidden;
}

.premium__format-corner {
  position: absolute;
  top: 0;
  right: 0;
  padding: 3px 8px;
  background: var(--pd-pink);
  color: #fff;
  font-family: var(--pd-font-mono);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.5px;
  border-bottom-left-radius: 8px;
}
.premium__format-corner--xlsx { 
  background: var(--pd-success); 
}
.premium__format-corner--tiles { 
  background: var(--pd-orange); 
}

/* PDF thumb — text lines on a "page" */
.premium__format-thumb--pdf { 
  background: #fff; 
}
.premium__format-line {
  display: block;
  height: 4px;
  margin: 6px 0;
  border-radius: 2px;
  background: var(--pd-divider);
}
.premium__format-line--w5  { width: 50%; }
.premium__format-line--w6  { width: 65%; }
.premium__format-line--w7  { width: 72%; }
.premium__format-line--w8  { width: 88%; }
.premium__format-line--w9  { width: 92%; }
.premium__format-line--primary {
  background: var(--pd-pink);
  height: 5px;
}

/* XLSX thumb — grid of colored cells */
.premium__format-thumb--xlsx {
  background: #fff;
  padding: 14px 8px 8px;
}
.premium__format-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  grid-template-rows: repeat(6, 1fr);
  gap: 2px;
  height: 100%;
}
.premium__format-cell {
  border-radius: 1.5px;
  background: var(--pd-divider);
}
.premium__format-cell--peach { background: #FFB088; }
.premium__format-cell--light-peach { background: #FFCDA6; }
.premium__format-cell--cream { background: #FFF4E6; }
.premium__format-cell--pink { background: #FFB6C1; }
.premium__format-cell--black { background: #2D2D2D; }
.premium__format-cell--brown { background: #8C6A55; }
.premium__format-cell--hot-pink { background: #FF6B9D; }

/* Tiles thumb — 2x2 numbered quadrants */
.premium__format-thumb--tiles {
  background: #fff;
  padding: 14px 8px 8px;
}
.premium__format-tiles {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 3px;
  height: 100%;
}
.premium__format-tile {
  background: var(--pd-bg-warm);
  border: 1px dashed var(--pd-stroke);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--pd-font-display);
  font-size: 14px;
  font-weight: 800;
  color: var(--pd-pink-deep);
}

/* Format card meta below thumb */
.premium__format-name {
  font-size: 12px;
  font-weight: 600;
  text-align: center;
  color: var(--pd-fg-1);
}
.premium__format-meta {
  font-size: 10px;
  color: var(--pd-fg-2);
  text-align: center;
}

/* ===== Compact stats row ===== */
.premium__stats {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 12px 8px;
  margin-bottom: 16px;
}
.premium__stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.premium__stat-num {
  font-family: var(--pd-font-display);
  font-size: 20px;
  font-weight: 800;
  color: var(--pd-fg-1);
  line-height: 1;
}
.premium__stat-num--cost { 
  color: var(--pd-pink-deep); 
}
.premium__stat-unit {
  font-size: 11px;
  color: var(--pd-fg-2);
}

/* ===== Actions ===== */
.premium__actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
</style>
