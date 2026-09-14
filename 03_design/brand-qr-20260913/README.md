# 小狗拼豆铺固定二维码

店主要求：分别提供网站与小程序两张码，不制作宣传海报；中心采用原品牌重新排列的方形 logo。网站保留 Hamilton；小程序将“小程序”放在“拼豆铺”下方并使用微信绿。

## 文件

- `website-qr-large-logo.png`：新版大 logo 网站码，2624 × 2624；完整 Hamilton logo 相对二维码画布的宽度增大 41.8%，面积约为原来的 2.01 倍，保留全部文字。配套 `website-qr-large-logo.svg`。
- `website-qr.png`：2368 × 2368；直接编码 `https://pindoupuppy.com`。中心为 Hamilton 方形 logo。
- `miniapp-qr.png`：1280 × 1280；微信官方 `getUnlimitedQRCode` 返回的正式版首页码，AppID `wx9f2b4d171e92a5ef`，scene `puppy-studio`。中心为底部“小程序”绿字的方形 logo。
- 同名 SVG：保留编码与嵌入图案的可缩放版本。
- `logo-website-square.png`、`logo-miniapp-square.png`：使用内置 imagegen 根据店主原品牌制作的独立方形图。实际提示词保存在 `prompts.json`。

## 有效性与核验

- 大 logo 版保持同一 HTTPS 首页地址，采用 Version 4、H 纠错、mask 0、四模块外留白，中心 logo 由原来的画布 7/37 调整为 11/41。原 SVG 上直接增加遮盖面积出现部分解码失败，因此重新生成相同地址的编码后筛选。最终在 2624、740、370、296、222、185 px、90° 旋转及轻微模糊/透视条件下，OpenCV 和 ZXing 共 40 项检查通过。证据 `artifacts/brand-qr-20260913/large-logo-candidates/final-checks.json`；仅交付全部通过的版本。
- 网站码是静态码，无服务商中转、无订阅、无二维码到期时间；网址本身仍需保持续费与正常服务。高纠错 H、Version 3，四模块留白。OpenCV 和 ZXing 在 2368、740、370、296、222、185 px 及 90° 旋转共 24 次解码均为正确的 HTTPS 首页地址。
- 微信官方说明：通过此接口生成的小程序码永久有效；不指定 page 时进入主页面，env_version 为 release。官方文档：[获取不限制的小程序码](https://developers.weixin.qq.com/miniprogram/dev/server/API/qrcode-link/qr-code/api_getunlimitedqrcode.html)。
- 小程序中心修改完全位于官方预留头像区。最终 PNG 与官方图片比较，中心半径 300 px 外每个 RGB 像素相同，编码线条、定位标记和微信小程序标记未变。微信专用码不使用通用 QR 解码器冒充真机验证。
- **正式版已发布**：店主完成管理员扫码并回复“已发布”。2026-09-14T00:37:04Z 重新加载公众平台版本管理，线上版本显示 0.1.16，页面发布时间为 2026-09-13 20:34:29。正式版首页 pages/studio/home 的严格校验已由 41030 转为成功返回官方码。交付码仍使用永久的默认首页入口，版本更新不会把它变成体验码。已验证后台及接口，未把通用扫码器测试称为微信真机扫码测试。
- 未修改小程序头像、官方名称或网站部署；打印码采用本次设计。名称仍以平台审核结果为准。测试与平台证据保存在本地忽略目录 `artifacts/brand-qr-20260913/`，临时登录／发布验证二维码不属于本交付物。
