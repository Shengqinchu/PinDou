# N1–N6 定点复验 closure

对象：`12a27b711daf280022ded60f49623a5e6b6239fa`。日期：2026-09-08 UTC。对照 [第二轮复审](C:/Users/123/Desktop/PinDou/03_design/STUDIO_0830_REREVIEW.md)，仅复验六个原失败状态，没有扩展为全站重审。

## 结论

**N1–N6 在本轮独立本地浏览器复验范围内均可关闭，没有仍未解决的原项。** 原先对应的控制、照片和样式清理保留项已完成闭环，无需为这六项继续冻结应用或重复全站设计评审。

判断依据是独立操作冻结版本、查看实际截图和中间帧，并核对 `e34120e → 12a27b7` 的源码变化；没有用实施方的 19 条测试通过数代替验收。

| 项目 | 判定 | 本轮实测 |
|---|---|---|
| N1 触摸颜色残留 | 关闭 | 复制成功与失败都用实际 touch 操作；松开 500ms 后均回到 `rgb(165,88,66)`，无按压位移。即使浏览器仍保留 `:hover`，也不再出现旧深色。 |
| N2 内容抢先移动 | 关闭 | 后台切页采样全程无内容位移，只有 opacity 0.9→1 的轻变化；选中条正常抵达。原来的整块 14px 位移消失。 |
| N3 反向丢失图层 | 关闭 | 约 25%、55%、76% 时反向，24–27ms 后仍保留两层并继续淡出：`0.2558→0.2395`、`0.5497→0.5337`、`0.7556→0.7414`，结束后才清理。五连点最多两层，最终图片/索引一致，没有卡在加载中。 |
| N4 当前栏目不收起 | 关闭 | 在商品页再次选择当前栏目，菜单关闭、背景 inert 解除、body 恢复 static，焦点返回菜单按钮。按既有 680ms 动画结束后补验，侧栏右边界为 0，完全退出画面。 |
| N5 中文孤行 | 关闭 | 首页与预约页两段文字在 320、390、1080、1440px 均为自然完整单行，没有“乐。”孤行；字号保持手机 14px、桌面 15px。 |
| N6 错误/辅助文案 | 关闭 | Visit/Shop 的中英文网络无响应均显示本地化提示，不再出现 `Failed to fetch`；订单类型辅助名称随语言切换为“订单类型”/“Order type”。 |

## 证据

- E1：[独立结果](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-closure/independent.json)，包含六项的输入、状态与结果；主取证时间为 `01:09:26–01:09:56 UTC`。
- E2：[照片逐帧](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-closure/photo-frames.json)、[反向中间画面](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-closure/N3-reversal-midpoint.png)。中间画面保留两张图是正常淡出过程，不是旧版多层排队残影。
- E3：[切页逐帧](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-closure/navigation-frames.json)。
- E4：[菜单完成状态](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-closure/menu-settled.json)、[收起完成截图](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-closure/N4-settled.png)。500ms 的早期截图仍在既有收起动画中，不作为最终位置判断。
- E5：[首页断行](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-closure/N5-home-1440.png)、[预约页断行](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-closure/N5-visit-1080.png)、[中文失败提示](C:/Users/123/Desktop/PinDou/artifacts/studio-0830-closure/N6-network-zh.png)。

结果与源码相互验证，闭环路径为：原失败状态 → 独立重现操作 → 观察修正后的中间/完成状态 → 关闭对应项。

主证据 SHA-256：

```text
independent.json       66e900aa77dd60f459057be58cc44fbb70560dbd6c35aadc9f7581d0fac55e7f
photo-frames.json      9dad5720d8be239d0280f7119d3d08ed082fd83718818c523433fa77a97708aa
navigation-frames.json 2fcc3e60578b2c8b3a97cae9be0db853e774b12675df3abec88a1c9856f05242
```

## 范围边界

本轮使用独立 Chromium 浏览器及触摸模拟；关闭营业/断网/剪贴板结果在浏览器内模拟。没有修改应用源码、seed QA、保存业务数据、创单、收费或部署；浏览器均已关闭。既有报告与证据目录未覆盖。

本报告不判断生产版本或批准部署，原任务另行发布及线上验证以其同期记录为准。真实 iOS/Android 微信、真实收款和履约仍不属于本轮证明范围，也未借 closure 重新审查其他已通过项目。
