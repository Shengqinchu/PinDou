# 中文字体、按钮反馈与排版修订

## 变更范围

只修改独立工作室前端 `05_studio`。保留英文 DM Serif Display / Outfit 字体、原图纸工具、业务服务和现有请求数据。

中文字体从浏览器实际使用的 Microsoft YaHei，改为站点发布的 Noto Serif SC / Noto Sans SC 项目子集；通过 Chrome DevTools Protocol 核实标题和正文确实使用 custom font，而非只改了 CSS 名称。

按钮依据 T-Check 已验收规范适配：300ms ease-in-out，父按钮和子图标同步；悬停 -2px，按下 y=1px / scale=.988，松开恢复。减少动态效果时双方均无位移。

排版调整了中文字号、行高、标题 / 正文角色、图集对齐、商品价格对齐与表单分组；预约表消除已过去时段及开始 / 结束矛盾，并保持套餐人数一致。

## 已验证

- Vue / TypeScript 生产构建通过。
- 1440×900、390×844 的首页、预约、小店、相册均无水平溢出，axe 自动检查无报告问题。
- 1080×665、320×740、2048×1017 的首页和预约页面无水平溢出。
- 实际字体：标题 PinDou Serif SC，正文 PinDou Sans SC，均为随站点加载的字体；英文展示字体仍是 DM Serif Display。
- 按钮 idle / hover / pressed / released 逐状态验证通过；父子时长均为 0.3s。减少动态效果时父子 transform 均为 none。
- 用 Asia/Tokyo 浏览器时区及受控时钟验证 Hamilton 日期：过去的开始时间移除、晚间结束时间修正、套餐人数 1 / 2、无可选时段时禁用提交但仍能更改日期。
- 测试不提交公网顾客请求，不发送通知。

验证脚本：`05_studio/scripts/verify-refinement.mjs`。
截图和 JSON：本地 `artifacts/studio-refinement/`。

本轮实际浏览器为 Windows Edge / Chromium；手机项目是视口模拟，未声称完成真机 Safari 或微信浏览器验证。

## 发布记录

- 版本：`20260907210223-studio-v1`。
- 发布包 SHA-256：`ef5397f83da24d57181e94802f312e7b6a5b19c5086326baae234580ea0a71b7`。
- 公网 JS / CSS 和本地构建一致；两份中文字体均可下载；新旧服务健康检查正常。
