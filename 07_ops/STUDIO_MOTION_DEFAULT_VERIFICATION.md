# 首次访问默认动画 / 2026-09-09

来源：店主反馈无痕窗口没有标题动画，并明确“必须让大家第一次进来就有动画”。沿用当前动画设计，仅修正默认偏好；不增加界面文案、菜单层级或新的登录条件。

## 原因与修正

- 线上旧版 `2026-09-10T02:38:48.162Z`，空存储＋原生 Chromium：系统 reduced，本站 source=system、motion=reduced，字形悬停 transform=none。应用内当前标签 DOM 公开诊断同样为 system/reduced。
- 同一系统显式访问 full 时，字形在指针停留后维持约 -7.38px。系统 no-preference 的全新上下文也正常。该问题来自默认策略，没有证据指向无痕禁用 JS、登录状态或随机丢失动画。
- `motion-preference.ts` 无本站选择、无效选择或存储异常时统一默认 full。显式 reduced/full/system 均保留；system 现在保存字面值，清除键则返回本站 full 默认。首组件挂载前解析完毕，不改操作系统设置。
- CSS、GSAP、标题、小狗/星星、按压、弹层、预约和生成器继续用同一个开关。离屏、后台标签、触屏无悬停的正常行为保留。
- 旧版默认跟随系统的考虑是减少动画引起的不适；本轮按店主明确要求变更默认，同时保留访客主动选择的减少动效和跟随系统。

## 验证

- `npm run build` 通过：64 个文案模块无变化，Vue/TypeScript 与正式构建通过。构建时间 `2026-09-10T02:57:02.099Z`。
- `node scripts/verify-motion-default.mjs` 通过 19 组场景，Chromium、Firefox、WebKit 三引擎。
- 三种空存储首次访问（原生媒体偏好、模拟 reduce、模拟 no-preference）均有完整入场中间帧，首帧即 full；逐字独立抬升、指针不移开持续保持、移开回落、小狗点击挤压与缓慢漂浮均有实际测量。
- 原生设置下重新加载、预约卡片和生成器模式按钮继续有位移；手机触屏在模拟 reduce 下仍有入场与点击反馈。
- 显式 reduced/system、刷新、系统信号变动、跨标签同步、清除选择、存储被拒绝与无效存储均通过。
- 没有页面错误，没有登录、邮件、生成或预约提交请求。浏览器脚本使用临时 QA 数据，不连接或写入真实客户数据。
- 脚本开发中修正一处测试前提：保留 `?motion=system` 的 URL 在刷新后仍是显式选择；测试清除本站选择后回到普通 URL 再验证默认。该行为符合 URL 优先规则。

证据目录：`artifacts/studio-motion-default/`，包括线上 before.json、browser-test.log、verification.json；发布核对将追加在下方。

## 线上结果

- 实现提交 `bc81349` 已推送。发布 `20260910030309-studio-v7`，构建 `2026-09-10T02:57:02.099Z`，357 文件哈希通过。归档 343618 字节，SHA-256 `ca58cb7cac976f6be70bee0e694d31ff2368b4cdfd1eda9f3d5b818f7448a191`。
- 线上原生 Windows、模拟 reduce 的 Chromium、手机 WebKit 全新会话均 source=full/motion=full、saved=null；标题抬升 -7.38px，狗图捏捏 scaleY 约0.80–0.81，刷新仍 full。应用内真实窗口也读取到新构建和 full，而系统仍 reduced，预约人数2人及当前第二步保留。
- 原始线上检查记录了 Cloudflare `/cdn-cgi/rum` 性能统计请求；其中手机 WebKit 报一条访问控制错误。该统计请求不影响已通过的动效断言，记录保留在 live-browser.json，不把它描述为零浏览器错误。未发生本站登录、邮件、生成或预约写入请求。
- 发布前后业务数据指纹完全一致；生成器原服务/HTML保持不变，两个服务均 active。证据为 before-deploy.json、after-deploy.json、preservation.json 与 deploy-result.json。
