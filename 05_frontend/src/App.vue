<script setup lang="ts">
import { onLaunch, onShow, onHide } from "@dcloudio/uni-app";
import { useUserStore } from "./store/user";

onLaunch(() => {
  console.log("PinDou App Launching...");

  // Keep launch synchronous for WeChat runtime. A slow profile request must not
  // block the first page render or WAService can report a launch timeout.
  const userStore = useUserStore();
  if (userStore.token) {
    void refreshProfileInBackground(userStore);
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
</style>
