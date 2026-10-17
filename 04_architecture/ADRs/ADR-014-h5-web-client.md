# ADR-014 H5 / 手机 web 客户端

- 状态：已采纳（2026-06-01）
- 决策人：用户拍板（chat 端 Claude 已两次说明 web 不省备案、ICP 墙仍在；用户坚持先做出来）
- 触发：用户觉得微信小程序行政流程（备案/认证/命名）麻烦，要一个手机 web 版先做出来。

## 关键前提（钉死，别忘）
- **"做出来 / 构建"不需要备案**；但**正式上线给国内用户、用大陆域名**仍需 **ICP 备案**，且上海移动云服务器是借来的 RAM 子账号、无法用陈昕铭身份备案 —— **这堵墙是推迟不是消失**。本 ADR 只负责"做出来 + 可预览测试"，生产域名/ICP 另行解决。

## 决策：web = 现有 uni-app 编到 H5，不是新工程
- 前端已是 uni-app，自带 `build:h5` 脚本 + `@dcloudio/uni-h5` 依赖 → 同一套代码编 H5。
- **传输**：`request.ts` 已有 HTTPS fallback，H5 下无 `wx.cloud` 自动走普通 HTTPS，无需改。
- **wx.cloud.init**：App.vue 已守卫（H5 下 wx 未定义直接 return），不崩。
- **登录（唯一真缺口）**：H5 无 `uni.login({provider:weixin})`。后端 `/user/login` 实为 `openid = "wx_"+sha256(code)`（无真 code2session）→ **H5 端生成持久化设备 uuid（localStorage）当 code 调同一接口**，得到稳定匿名身份。不上 SMS、不上微信 OAuth（留作后续）。
- **支付**：虎皮椒 web QR，后端流程不变，前端展示二维码即可。
- **部署（先做出来阶段）**：`build:h5` 出静态包，挂到现有 FastAPI 静态目录 / 云托管 URL，手机浏览器直接开着测；生产中国域名 = ICP，后办。

## 双端共存约束
- mp-weixin 与 H5 两个构建都必须能过；微信专属分支用 uni-app 条件编译 `#ifdef MP-WEIXIN` / `#ifdef H5` 隔离。

## web 响应式策略（2026-06-01，pindoupuppy.com 上线后）
- 现状：H5 是移动布局，桌面浏览器下被拉满显得空/坏。受众主体在小红书=手机端 → **移动优先**。
- 决策（两批）：
  - **Batch 1（快）**：宽视口（≥768px）下把 app 收进居中手机宽度列（~420px）+ 周围柔和品牌背景，移动端不变。纯 CSS media query，mp-weixin 不受影响（手机永不触发宽断点）。
  - **Batch 2（增强）**：桌面大屏多列排版（左操作 + 右大预览 + 顶部导航），真正利用大屏编辑/查看图纸。
- 域名：pindoupuppy.com（Cloudflare），静态页 Worker 托管，/api/* 反代腾讯云托管后端（后端+DB 仍在腾讯）。

## 未决 / 后续
- 生产 web 上线的 ICP 域名方案（含服务器主体）。
- web 真实身份体系（手机号/微信 OAuth），若匿名设备 id 不够用再上。
