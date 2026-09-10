<script setup lang="ts">
import { onLaunch, onShow, onHide } from "@dcloudio/uni-app";
import { useUserStore } from "./store/user";
import { IS_H5_CLIENT, USE_WX_CLOUD } from "./utils/request";

declare const wx: any;
declare const process: { env?: { VITE_WX_CLOUD_ENV?: string } };

onLaunch(() => {
  console.log("PinDou App Launching...");
  initWxCloud();

  // Keep launch synchronous for WeChat runtime. A slow profile request must not
  // block the first page render or WAService can report a launch timeout.
  const userStore = useUserStore();
  userStore.initDeviceMetrics();
  if (userStore.token) {
    void refreshProfileInBackground(userStore);
  } else {
    // #ifdef H5
    console.log("H5 默认保持未登录态，用户需要身份动作时再走邮箱验证码登录。");
    // #endif
    // Native visitors can browse first. Sign-in is requested by an identity
    // action; opening an approval QR must not silently register a new account.
  }
});

onShow(() => {
  console.log("PinDou App Show");
});

onHide(() => {
  console.log("PinDou App Hide");
});

async function refreshProfileInBackground(userStore: ReturnType<typeof useUserStore>) {
  try {
    const profile = await userStore.fetchProfile();
    if (IS_H5_CLIENT && !profile.email) {
      console.warn("H5 检测到旧匿名登录态，已清除并切换为邮箱登录。");
      userStore.logout();
    }
  } catch (e) {
    console.warn("自动登录拉取 Profile 失败，可能登录态已失效:", e);
    userStore.logout();
  }
}

function initWxCloud() {
  if (!USE_WX_CLOUD) return;
  if (typeof wx === "undefined" || !wx.cloud) {
    return;
  }
  const viteEnv = (import.meta as any).env || {};
  const wxCloudEnv =
    viteEnv.VITE_WX_CLOUD_ENV ||
    (typeof process !== "undefined" && process.env?.VITE_WX_CLOUD_ENV ? process.env.VITE_WX_CLOUD_ENV : "") ||
    "prod-01";
  wx.cloud.init({
    env: wxCloudEnv,
    traceUser: true,
  });
}
</script>

<style lang="scss">
/* 导入小程序版 Design Tokens 与全局公共组件 */
@import "./static/styles/colors_and_type.css";
@import "./static/styles/components.css";
/* Shared across the native auth shell, its slot content and child components. */
@import "./static/styles/studio-auth.css";

/* 适配小程序 page 容器 */
page {
  background-color: var(--pd-bg);
  color: var(--pd-fg-1);
  font-family: var(--pd-font-body);
  font-size: var(--pd-fs-body);
  line-height: var(--pd-lh-body);
  -webkit-font-smoothing: antialiased;
  min-height: 100vh;
  box-sizing: border-box;
}

/* 微信小程序全局容器盒子适配 */
.uni-page-head, .uni-page-wrapper {
  background-color: var(--pd-bg);
}

/* 保证所有视图元素的盒子模型都应用 border-box */
view, scroll-view, text, image, button, input, textarea {
  box-sizing: border-box;
}

/* #ifdef H5 */
*,
*::before,
*::after {
  box-sizing: border-box;
}

/* Desktop browsers should see the mobile app as a centered phone column.
   The mobile breakpoint keeps the original full-width behavior untouched. */
@media (min-width: 768px) {
  html,
  body {
    min-height: 100%;
    background:
      radial-gradient(circle at 18% 14%, rgba(255, 176, 136, 0.32), transparent 28%),
      radial-gradient(circle at 82% 20%, rgba(255, 107, 157, 0.24), transparent 30%),
      linear-gradient(135deg, #FFF9F5 0%, #FFF1E8 48%, #FFF1F6 100%) !important;
  }

  body {
    overflow-x: hidden;
  }

  #app,
  uni-app {
    width: min(100vw, 430px) !important;
    max-width: 430px !important;
    height: 100vh;
    height: 100dvh;
    margin: 0 auto !important;
    position: relative;
    overflow: hidden;
    background: var(--pd-bg, #FFF9F5);
    box-shadow:
      0 24px 70px rgba(255, 107, 157, 0.18),
      0 2px 16px rgba(45, 45, 45, 0.06);
  }

  uni-page,
  uni-page-wrapper,
  uni-page-body,
  .frame {
    width: 100% !important;
    max-width: 430px !important;
  }

  .frame {
    height: 100vh !important;
    height: 100dvh !important;
  }

  .frame__body {
    height: calc(100vh - var(--pd-top-chrome-height) - var(--pd-safe-bottom));
    height: calc(100dvh - var(--pd-top-chrome-height) - var(--pd-safe-bottom));
  }

  uni-tabbar,
  uni-tabbar.uni-tabbar-bottom,
  .uni-tabbar-bottom,
  .uni-tabbar-bottom .uni-tabbar {
    width: min(100vw, 430px) !important;
    max-width: 430px !important;
  }

  .uni-tabbar-bottom,
  .uni-tabbar-bottom .uni-tabbar {
    left: 50% !important;
    right: auto !important;
    transform: translateX(-50%) !important;
  }

  .uni-tabbar-bottom .uni-tabbar {
    bottom: 0 !important;
  }

  .uni-tabbar ~ .uni-placeholder {
    width: 100% !important;
    max-width: 430px !important;
    margin-left: auto;
    margin-right: auto;
  }
}

.desktop-nav,
.desktop-footer {
  display: none;
}

@media (min-width: 1024px) {
  html,
  body {
    min-height: 100%;
    background:
      radial-gradient(circle at 9% 18%, rgba(255, 176, 132, 0.18), transparent 26%),
      radial-gradient(circle at 91% 14%, rgba(164, 212, 197, 0.22), transparent 24%),
      linear-gradient(135deg, #fffaf0 0%, #faf5e8 100%) !important;
  }

  body {
    overflow-x: hidden;
    overflow-y: auto;
  }

  #app,
  uni-app,
  uni-page,
  uni-page-wrapper,
  uni-page-body,
  .frame {
    width: 100% !important;
    max-width: none !important;
    min-height: 100vh;
    min-height: 100dvh;
    height: auto !important;
    margin: 0 !important;
    overflow: visible !important;
    box-shadow: none !important;
  }

  #app,
  uni-app,
  uni-page-body,
  .frame {
    background: transparent !important;
  }

  .uni-app--showtabbar uni-page-wrapper,
  .uni-app--showtabbar uni-page-head[uni-page-head-type=default] ~ uni-page-wrapper {
    height: auto !important;
    min-height: 100vh !important;
    min-height: 100dvh !important;
  }

  .uni-app--showtabbar uni-page-wrapper::after {
    display: none !important;
    height: 0 !important;
    content: none !important;
  }

  uni-tabbar,
  .uni-tabbar,
  .uni-tabbar-bottom,
  .uni-tabbar-bottom .uni-tabbar,
  .uni-tabbar ~ .uni-placeholder {
    display: none !important;
  }

  .frame {
    min-height: 100vh !important;
    min-height: 100dvh !important;
    display: flex;
    flex-direction: column;
  }

  .frame__header {
    display: none !important;
  }

  .frame__body {
    width: 100% !important;
    max-width: 1200px !important;
    height: auto !important;
    min-height: calc(100vh - 150px);
    min-height: calc(100dvh - 150px);
    margin: 0 auto !important;
    padding: 0 32px 64px;
    overflow: visible !important;
  }

  .frame__body--scroll {
    overflow: visible !important;
  }

  .desktop-nav {
    position: sticky;
    top: 0;
    z-index: 200;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    gap: 28px;
    width: 100%;
    min-height: 64px;
    padding: 0 max(32px, calc((100vw - 1200px) / 2));
    background: rgba(255, 250, 240, 0.92);
    border-bottom: 1px solid rgba(229, 229, 229, 0.78);
    backdrop-filter: blur(16px) saturate(150%);
    -webkit-backdrop-filter: blur(16px) saturate(150%);
  }

  .desktop-nav button,
  .desktop-footer button,
  .desktop-nav uni-button,
  .desktop-footer uni-button {
    appearance: none;
    border: 0;
    background: transparent;
    font-family: inherit;
    color: inherit;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin: 0;
    padding: 0;
    line-height: 1;
    overflow: visible;
    box-shadow: none;
  }

  .desktop-nav button::after,
  .desktop-footer button::after,
  .desktop-nav uni-button::after,
  .desktop-footer uni-button::after {
    display: none;
    border: 0;
    content: none;
  }

  .desktop-nav__brand {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
    flex: 0 0 auto;
    padding: 0;
    font-family: var(--pd-font-display);
    font-size: 20px;
    font-weight: 800;
    color: #0a0a0a;
  }

  .desktop-nav__logo-dot {
    width: 28px;
    height: 28px;
    border-radius: 999px;
    background: #ffb084;
    box-shadow: 0 8px 18px rgba(255, 176, 132, 0.28);
    position: relative;
  }

  .desktop-nav__logo-dot::after {
    content: "";
    position: absolute;
    inset: 9px;
    border-radius: inherit;
    background: #fff;
  }

  .desktop-nav__links {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 10px;
    flex: 0 0 auto;
    margin-left: auto;
  }

  .desktop-nav__link {
    min-width: 0;
    height: 40px;
    border-radius: 999px;
    padding: 0 16px;
    font-size: 14px;
    font-weight: 600;
    color: #3a3a3a;
  }

  .desktop-nav__link:hover,
  .desktop-nav__link--active {
    color: #0a0a0a;
    background: #f5f0e0;
  }

  .desktop-nav__account {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .desktop-nav__avatar-button {
    width: 42px;
    height: 42px;
    border: 1px solid rgba(229, 229, 229, 0.78) !important;
    border-radius: 999px;
    background: #fffaf0 !important;
    transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
  }

  .desktop-nav__avatar-button:hover,
  .desktop-nav__avatar-button--active {
    transform: translateY(-1px);
    border-color: rgba(255, 176, 132, 0.72) !important;
    box-shadow: 0 10px 26px rgba(255, 176, 132, 0.18);
  }

  .desktop-nav__avatar {
    width: 32px;
    height: 32px;
    border-radius: inherit;
    background: #1a3a3a;
    color: #fffaf0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 900;
    font-size: 15px;
  }

  .desktop-nav__menu {
    position: absolute;
    top: calc(100% + 10px);
    right: 0;
    z-index: 260;
    width: 152px;
    padding: 8px;
    border: 1px solid rgba(229, 229, 229, 0.86);
    border-radius: 16px;
    background: rgba(255, 250, 240, 0.98);
    box-shadow: 0 18px 48px rgba(10, 10, 10, 0.12);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
  }

  .desktop-nav__menu-item {
    width: 100%;
    min-height: 38px;
    justify-content: flex-start !important;
    padding: 0 12px !important;
    border-radius: 10px !important;
    color: #1a1a1a !important;
    font-size: 13px;
    font-weight: 700;
  }

  .desktop-nav__menu-item:hover {
    background: #f5f0e0 !important;
  }

  .desktop-nav__menu-item--danger {
    color: #d93d30 !important;
  }

  .desktop-footer {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    width: 100%;
    max-width: 1200px;
    margin: auto auto 0;
    padding: 22px 32px 30px;
    color: #6a6a6a;
    font-size: 13px;
  }

  .desktop-footer__link {
    color: #6a6a6a !important;
    font-size: 13px;
  }

  .desktop-footer__link:hover {
    color: #0a0a0a !important;
  }

  .desktop-footer__dot {
    width: 4px;
    height: 4px;
    border-radius: 999px;
    background: #ebe6d6;
  }

  .home__container {
    display: grid;
    grid-template-columns: minmax(0, 0.95fr) minmax(360px, 0.9fr);
    grid-template-areas:
      "hero sample"
      "chips sample"
      "cta sample";
    grid-template-rows: auto auto auto;
    align-content: center;
    align-items: center;
    justify-content: space-between;
    column-gap: clamp(36px, 7vw, 96px);
    min-height: calc(100vh - 150px);
    min-height: calc(100dvh - 150px);
    padding: clamp(56px, 8vh, 88px) 0 92px;
  }

  .home__hero-wash {
    display: none;
  }

  .home__carousel-section {
    grid-area: sample;
    width: 100%;
    margin-top: 0 !important;
    padding: 0;
  }

  .home__swiper {
    width: 100%;
    height: clamp(444px, 47vw, 520px) !important;
  }

  .home__banner {
    width: 100% !important;
    max-width: none !important;
    height: clamp(430px, 45vw, 506px) !important;
    border: 1px solid rgba(229, 229, 229, 0.78);
    border-radius: 24px !important;
    background: #faf5e8 !important;
    box-shadow: 0 22px 60px rgba(10, 10, 10, 0.08);
  }

  .home__banner-caption {
    padding: 16px 28px 0 2px !important;
    background: transparent !important;
    color: #0a0a0a !important;
  }

  .home__banner-title {
    font-size: 22px !important;
  }

  .home__banner-meta {
    font-size: 14px !important;
  }

  .home__dots {
    justify-content: center;
    margin-top: 14px !important;
  }

  .home__hero {
    grid-area: hero;
    padding: 0 !important;
    text-align: left !important;
  }

  .home__headline {
    max-width: 620px;
    font-size: clamp(50px, 5.2vw, 72px) !important;
    line-height: 1 !important;
    letter-spacing: 0 !important;
  }

  .home__subtitle {
    max-width: 520px;
    margin-top: 24px !important;
    font-size: 20px !important;
    line-height: 1.55 !important;
  }

  .home__chips {
    grid-area: chips;
    justify-content: flex-start !important;
    gap: 12px !important;
    margin-top: 36px !important;
    padding: 0 !important;
  }

  .home__chips .chip {
    min-height: 44px;
    padding: 0 18px !important;
    font-size: 15px !important;
    box-shadow: var(--pd-shadow-card);
  }

  .home__cta-wrap {
    grid-area: cta;
    width: 360px;
    padding: 28px 0 0 !important;
  }

  .home__cta-hint {
    text-align: left !important;
    font-size: 13px !important;
  }

  .upload__empty,
  .upload__selected {
    width: min(100%, 720px) !important;
    height: auto !important;
    min-height: 0 !important;
    margin: 40px auto 0;
    padding: 44px !important;
    border-radius: 28px;
    background: rgba(255, 255, 255, 0.88);
    box-shadow: 0 24px 72px rgba(255, 107, 157, 0.14), var(--pd-shadow-card);
  }

  .upload__hint {
    font-size: 22px !important;
    margin-bottom: 32px !important;
  }

  .upload__entries {
    gap: 18px !important;
  }

  .upload__entry {
    height: 220px !important;
    border-radius: 22px !important;
  }

  .upload__entry-icon {
    width: 72px !important;
    height: 72px !important;
    font-size: 26px !important;
  }

  .upload__entry-label {
    font-size: 18px !important;
  }

  .upload__tip {
    margin-top: 24px !important;
    padding: 18px 20px !important;
  }

  .upload__spacer {
    display: none !important;
  }

  .upload__footnote {
    margin-top: 24px !important;
  }

  .upload__preview {
    height: min(68vh, 640px) !important;
    min-height: 420px;
  }

  .consent-modal {
    max-width: 520px !important;
  }

  .result {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(340px, 392px);
    gap: 28px;
    align-items: start;
    max-width: 1200px;
    margin: 0 auto;
    padding: 22px 0 80px !important;
  }

  .result__pattern {
    grid-column: 1;
    grid-row: 1 / span 5;
    position: sticky;
    top: 96px;
    margin: 0 !important;
    padding: 24px !important;
    border-radius: 28px !important;
    min-height: calc(100vh - 160px);
    min-height: calc(100dvh - 160px);
    justify-content: center;
  }

  .result__pattern-img-wrap {
    max-height: calc(100vh - 250px);
    max-height: calc(100dvh - 250px);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .result__pattern-image,
  .result__grid-preview,
  .result__loading-preview,
  .result__empty-preview {
    max-height: calc(100vh - 250px) !important;
    max-height: calc(100dvh - 250px) !important;
  }

  .result__summary,
  .result__colors-card,
  .result__actions,
  .result__regen {
    grid-column: 2;
  }

  .result__summary {
    margin: 0 !important;
    padding: 18px 8px !important;
  }

  .result__colors-card {
    margin: 0 !important;
    padding: 18px 16px 10px !important;
    max-height: 420px;
    overflow-y: auto;
  }

  .result__actions {
    margin: 0 !important;
    gap: 12px !important;
  }

  .result__regen {
    width: auto !important;
    margin: 0 !important;
    justify-content: flex-start !important;
  }

  .premium {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(360px, 420px);
    gap: 28px;
    align-items: start;
    max-width: 1200px;
    margin: 0 auto;
    padding: 22px 0 80px !important;
  }

  .premium__pattern {
    grid-column: 1;
    grid-row: 1 / span 6;
    position: sticky;
    top: 96px;
    margin: 0 !important;
    padding: 24px !important;
    border-radius: 28px !important;
    min-height: calc(100vh - 160px);
    min-height: calc(100dvh - 160px);
    justify-content: center;
  }

  .premium__pattern-wrap {
    max-width: min(100%, 680px) !important;
  }

  .premium__pattern-image {
    max-width: min(100%, 620px) !important;
    max-height: calc(100vh - 250px);
    max-height: calc(100dvh - 250px);
  }

  .premium__pro-bar,
  .premium__section-title,
  .premium__formats,
  .premium__stats,
  .premium__actions {
    grid-column: 2;
  }

  .premium__formats {
    grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
  }

  .works {
    max-width: 1200px;
    margin: 0 auto;
    padding: 22px 0 80px !important;
  }

  .works__stats {
    width: max-content;
    min-width: 360px;
    margin-bottom: 24px !important;
  }

  .works__grid {
    grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
    gap: 18px !important;
  }

  .works__card {
    padding: 12px 12px 14px !important;
    border-radius: 22px !important;
    transition: transform 180ms var(--pd-ease-out), box-shadow 220ms var(--pd-ease-out);
  }

  .works__card:hover {
    transform: translateY(-3px);
    box-shadow: 0 18px 44px rgba(255, 107, 157, 0.16), var(--pd-shadow-card);
  }

  .works__thumb {
    height: 220px !important;
    border-radius: 18px !important;
  }

  .works__more-cta {
    margin-top: 24px !important;
  }

  .works__empty {
    max-width: 620px;
    min-height: 0 !important;
    margin: 40px auto;
    padding: 58px 44px !important;
    border-radius: 28px;
    background: rgba(255, 255, 255, 0.86);
    box-shadow: var(--pd-shadow-card);
  }

  .me {
    max-width: 980px;
    margin: 24px auto 80px;
    display: grid;
    grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
    gap: 22px;
    align-items: start;
    padding-bottom: 0 !important;
  }

  .me__profile {
    grid-column: 1;
    flex-direction: column !important;
    align-items: flex-start !important;
    gap: 18px !important;
    padding: 28px !important;
    border-radius: 28px;
    background: rgba(255, 255, 255, 0.86);
    box-shadow: var(--pd-shadow-card);
  }

  .me__avatar,
  .me__avatar-img {
    width: 84px !important;
    height: 84px !important;
  }

  .me__nickname {
    font-size: 26px !important;
  }

  .me__credits {
    grid-column: 2;
    margin: 0 !important;
    padding: 24px 28px 14px !important;
    border-radius: 28px !important;
  }

  .me__menu {
    grid-column: 2;
    margin: 0 !important;
    border-radius: 28px !important;
  }

  .me__footer,
  .me__error {
    grid-column: 1 / -1;
  }

  .me__cs-sheet {
    align-items: center !important;
    justify-content: center !important;
  }

  .me__cs-panel {
    width: 420px !important;
    border-radius: 24px !important;
    padding: 24px !important;
  }
}
/* #endif */
</style>
