<script setup lang="ts">
import { onLaunch, onShow, onHide } from "@dcloudio/uni-app";
import { useUserStore } from "./store/user";

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
    // 首次启动：自动微信登录拿 JWT，保证 consent / upload 等鉴权接口可用
    void userStore.login().catch((e) => {
      console.warn("自动登录失败（可继续浏览，鉴权动作时会再触发）:", e);
    });
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
    await userStore.fetchProfile();
  } catch (e) {
    console.warn("自动登录拉取 Profile 失败，可能登录态已失效:", e);
    userStore.logout();
  }
}

function initWxCloud() {
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
      radial-gradient(circle at 12% 16%, rgba(255, 176, 136, 0.26), transparent 28%),
      radial-gradient(circle at 86% 10%, rgba(255, 107, 157, 0.22), transparent 26%),
      linear-gradient(135deg, #FFF9F5 0%, #FFF1E8 45%, #FFF1F6 100%) !important;
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
    padding: 32px 32px 64px;
    overflow: visible !important;
  }

  .frame__body--scroll {
    overflow: visible !important;
  }

  .desktop-nav {
    position: sticky;
    top: 0;
    z-index: 200;
    display: flex;
    align-items: center;
    gap: 28px;
    width: 100%;
    min-height: 72px;
    padding: 0 max(32px, calc((100vw - 1200px) / 2 + 32px));
    background: rgba(255, 249, 245, 0.86);
    border-bottom: 1px solid rgba(241, 236, 230, 0.9);
    backdrop-filter: blur(18px) saturate(160%);
    -webkit-backdrop-filter: blur(18px) saturate(160%);
  }

  .desktop-nav button,
  .desktop-footer button {
    appearance: none;
    border: 0;
    background: transparent;
    font-family: inherit;
    color: inherit;
    cursor: pointer;
  }

  .desktop-nav__brand {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    min-width: 184px;
    padding: 0;
    font-family: var(--pd-font-display);
    font-size: 20px;
    font-weight: 900;
    color: var(--pd-fg-1);
  }

  .desktop-nav__logo-dot {
    width: 28px;
    height: 28px;
    border-radius: 999px;
    background: var(--pd-gradient);
    box-shadow: 0 8px 18px rgba(255, 107, 157, 0.28);
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
    gap: 6px;
    flex: 1;
  }

  .desktop-nav__link {
    min-width: 76px;
    height: 40px;
    border-radius: 999px;
    padding: 0 18px;
    font-size: 14px;
    font-weight: 800;
    color: var(--pd-fg-2);
  }

  .desktop-nav__link:hover,
  .desktop-nav__link--active {
    color: var(--pd-pink-deep);
    background: var(--pd-pink-50);
  }

  .desktop-nav__user {
    min-width: 142px;
    height: 44px;
    padding: 0 14px 0 6px;
    border-radius: 999px !important;
    background: rgba(255, 255, 255, 0.72) !important;
    box-shadow: var(--pd-shadow-card);
    display: inline-flex;
    align-items: center;
    justify-content: flex-start;
    gap: 10px;
    color: var(--pd-fg-1);
  }

  .desktop-nav__avatar {
    width: 32px;
    height: 32px;
    border-radius: 999px;
    background: var(--pd-gradient-pink);
    color: #fff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 900;
    font-size: 15px;
  }

  .desktop-nav__user-text {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 13px;
    font-weight: 800;
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
    color: var(--pd-fg-2);
    font-size: 13px;
  }

  .desktop-footer__link {
    color: var(--pd-fg-2) !important;
    font-size: 13px;
  }

  .desktop-footer__link:hover {
    color: var(--pd-pink-deep) !important;
  }

  .desktop-footer__dot {
    width: 4px;
    height: 4px;
    border-radius: 999px;
    background: var(--pd-pink-200);
  }

  .home__container {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(430px, 520px);
    grid-template-rows: auto auto auto auto;
    column-gap: 72px;
    align-items: center;
    min-height: calc(100vh - 240px);
    min-height: calc(100dvh - 240px);
    padding: 28px 8px 80px;
  }

  .home__hero-wash {
    inset: -80px -160px auto;
    height: 560px;
    background:
      radial-gradient(80% 80% at 18% 22%, rgba(255, 228, 238, 0.95), transparent 70%),
      radial-gradient(70% 80% at 82% 26%, rgba(255, 241, 232, 0.9), transparent 68%);
  }

  .home__carousel-section {
    grid-column: 2;
    grid-row: 1 / span 4;
    width: 100%;
    padding: 0;
  }

  .home__swiper {
    width: 100%;
    height: 520px !important;
  }

  .home__banner {
    width: 100% !important;
    height: 520px !important;
    border-radius: 28px !important;
    box-shadow: 0 24px 64px rgba(255, 107, 157, 0.20), var(--pd-shadow-card);
  }

  .home__banner-caption {
    padding: 96px 28px 26px !important;
  }

  .home__banner-title {
    font-size: 22px !important;
  }

  .home__banner-meta {
    font-size: 14px !important;
  }

  .home__dots {
    justify-content: center;
    margin-top: 18px !important;
  }

  .home__hero {
    grid-column: 1;
    grid-row: 1;
    padding: 0 !important;
    text-align: left !important;
  }

  .home__headline {
    max-width: 560px;
    font-size: clamp(44px, 5vw, 64px) !important;
    line-height: 1.08 !important;
    letter-spacing: 0 !important;
  }

  .home__subtitle {
    max-width: 520px;
    margin-top: 20px !important;
    font-size: 20px !important;
    line-height: 1.7 !important;
  }

  .home__chips {
    grid-column: 1;
    grid-row: 2;
    justify-content: flex-start !important;
    gap: 12px !important;
    margin-top: 30px !important;
    padding: 0 !important;
  }

  .home__chips .chip {
    min-height: 44px;
    padding: 0 18px !important;
    font-size: 15px !important;
    box-shadow: var(--pd-shadow-card);
  }

  .home__cta-wrap {
    grid-column: 1;
    grid-row: 3;
    width: 360px;
    padding: 34px 0 0 !important;
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
