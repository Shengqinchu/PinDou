# 小狗拼豆铺小程序 / PinDou Puppy mini program

本目录仅构建小狗拼豆铺的店铺信息、预约、顾客账号与店主工作台。运行 `npm run build:mp-weixin` 构建微信包，`npm run build:h5` 构建浏览器验证版本。

This directory builds studio information, bookings, customer accounts and the host workspace. Use `npm run build:mp-weixin` for WeChat and `npm run build:h5` for browser verification.

入口为 `pages/studio/home`，账号状态使用 `store/studio-user.ts`。旧生成器源码保留供历史查阅，但不注册进当前页面清单，也不允许从 Studio 代码重新引用旧账号 store、生成接口或旧底部导航。网站图纸工具在独立的 `../05_web` 项目中。

The entry is `pages/studio/home`, with account state in `store/studio-user.ts`. Legacy generator source is retained for reference and is excluded from this product's routes and dependencies. The website pattern tool remains in the separate `../05_web` project.

微信构建后自动执行包检查：确认 Studio 页面范围，移除构建目录中自动复制的旧素材，拒绝旧路由、AI 生成文案及生成接口标记。冻结上传包也可以复查：

The post-build check validates Studio routes, excludes copied legacy assets, and rejects generator routes, labels and API markers. Verify a frozen upload package with:

```powershell
node scripts/check-studio-package.cjs --path=C:/absolute/path/to/frozen-package
```
