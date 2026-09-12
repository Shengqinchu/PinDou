# 小店工具复用与 VPS 复核（2026-09-12）

用户提供了《小店.pdf》及拼团呀路径，并指出已置顶的“调研 VPS 搭建与跨境访问方案”任务。已只读检索该任务的近期两页记录（14轮），将原本用于中国跨境/回国线路的筛选条件，改为本项目的加拿大用户、现有 Python/Vue 应用、约500元人民币年预算。旧对话不是实时库存依据。

## 结论

目前仍优先 OVH 加拿大东部 VPS-1 2027，2核4GB40GB NVMe。先月付测试，满意后年付。同期配置页已核对年付 CAD74.40税前，约人民币360；无合约月付CAD7.30。RackNerd纽约/芝加哥3核4GB60GB USD59.99/年税前（约402元）为备选。今日重新打开官方产品页，两家的对应4GB规格与基础价格仍一致。网络探针结果、旧源站观测和微信请求路由详见 [此前实测](PINDOU_SERVER_SELECTION_20260912.md)。没有购买新虚拟机，不能把官方测试点结果当成新VM性能验收。

## 置顶任务带来的候选

| 候选 | 本轮证据 | 对 PinDou 的判断 |
|---|---|---|
| HostDare 洛杉矶 NVMe | 官网4GB/100GB为USD130.99/年；当前promo页25%循环折扣。2GB/50GB优惠价USD53.24/年。 | 4GB按当前公开优惠约USD98.24/年，超预算。官网写双倍内存/流量需工单；未确认能拿到4GB前，不把2GB价格当4GB价格。 |
| HostDare旧50%码DEAL50 | 官方2026-01-04公告确有此码；实际购物配置页本轮遇安全验证，没有拿到接受优惠码的订单汇总。 | 不能声称USD65.50/年已经验证可买。若后来结账接受，可作为大磁盘备选，再测加拿大延迟。 |
| Akile LAX Lite | 实际页面：2核4GB20GB为69.99元/月、有库存；1核2GB10GB15.99元/月售罄；2核2GB10GB34.99元/月有库存。 | 4GB月付折年839.88元，且20GB偏小。不能只看“5Gbps”端口。年付可能另有折扣，本轮未登录领取优惠，不认作预算内候选。 |
| Akile华盛顿轻量 | 实际配置页：2核4GB80GB、峰值30Mbps、3072GB流量，99.88元/月。页面说明流量用完停机、无法原地升级。 | 美国东部地理位置合适，价格明显超出本轮预算。 |
| YT.NET US.LAX.SMR | 置顶任务旧记录1核1GB10GB、178.2元/年且曾售罄；本轮官网未直接取得该SKU可买库存。 | RAM和磁盘都不适合直接承接现有完整应用；不作为当前可下单推荐。 |
| HHost Tokyo、YT东京、Akile JPPro、HostDare日本 | 旧任务中有低价或大陆线路方案；本轮未逐个重跑购买页。 | 面向加拿大网站，没有必要先为日本/中国优化线路付费；旧价格与库存保持未核实标签。 |
| xTom/V.PS、DMIT、GoMami、NovixLink、edgeNAT | 旧任务主要用于质量更高的中国跨境链路，部分月费已明显高于预算。 | 可以做网络专项方案，未找到比上述4GB加拿大/美国东部方案更合适的已核实报价。 |
| JTTI、HNCloud、ZoroCloud、QQG | 原任务强调国内连通、IP或低价；RAM/磁盘、IPv4附加费、机房与续费条件需要逐SKU核对。 | 不凭品牌名或宣传核数替换已测候选，保留为未验证备选。 |

以上人民币折算沿用同日加拿大央行9月11日数据：1CNY=CAD0.2067、1USD=CAD1.3866。月价×12为简单折年比较，不是承诺的年付套餐价。税费和支付汇率另计。

## GitHub 工具选择

GitHub公开API于本轮核对；星数会变化，仅作项目采用度参考。

| 项目 | 星数 | 用法 / 实际结果 |
|---|---:|---|
| [WMPFDebugger](https://github.com/evi0s/WMPFDebugger) | 2648 | 实际采用。匹配本机微信WMPF25510，读取当前已登录拼团呀页面的商品字段和分页。工具端口限制127.0.0.1，提取后关闭。GPL-2.0；调试工具未合入业务发布包。 |
| [pywinauto](https://github.com/pywinauto/pywinauto) | 6162 | UIA试读只能看到容器，无法拿到分类商品树；因此没有继续做脆弱的全屏坐标抓取。BSD-3-Clause。 |
| [Microsoft UFO](https://github.com/microsoft/UFO) | 9711 | 更完整的Windows代理框架；本轮已有轻量连接方式，无需引入整套运行时。MIT。 |
| [TencentCloudBase skills](https://github.com/TencentCloudBase/skills) | 75 | 官方自有小程序开发/开发者工具流程参考；不把自有源码调试技能误当成第三方小程序数据访问。API未返回许可证标识，未复制代码。 |
| [Medusa](https://github.com/medusajs/medusa) | 36269 | 参考分类与商品图库组织，业务仍复用PinDou现有购物车、媒体上传、权限、版本冲突与价格模型。未复制或部署Medusa源码；API许可证字段NOASSERTION，不能据此宣称整个仓库均为MIT。 |

商品提取仅保存所选店铺公开的标题、色号/重量类别、图片、来源价格与来源ID。没有导出买家列表、个人聊天、购物车或登录凭证。没有下单、加购、关注或发送消息。

本轮WMPFDebugger固定版本为`e65e3ec98ea38de8ea78fc0ad02d01d9b2fd0345`，本地仅将两个WebSocket监听限制为127.0.0.1。结束后核对9421/62000均无监听。当前页面的分类事件参数实际是`toggleCategory({detail:{category:选中的categoryList对象}})`，不是分类ID字符串；分页使用既有`onReachBottom()`并等待loading=false/next=false。读取`items.flat(Infinity)`后只保留商品字段，逐系列归档。A/B/C/D/E/F/G/H/M分别27/33/30/27/25/26/22/24/16项，合计221个单色色号+9个整系列组合。后续来源版本更改时须重新核对页面事件，不能盲用本次上下文ID。

## 原始证据与官方链接

- 本地证据：`artifacts/shop-round-20260912/` 的source-categories.json、source-products.json、image-manifest.json、github-research.json、akile-us.txt、akile-light-washington.txt。
- [OVH加拿大](https://www.ovhcloud.com/en-ca/vps/)；[RackNerd specials](https://www.racknerd.com/specials/)。
- [HostDare规格](https://hostdare.com/vps.html)、[当前促销](https://www.hostdare.com/promo.html)、[旧50%公告](https://bill.hostdare.com/announcements/85/Hostdare-New-Year-VPS-offer----Limited-Time-.html)。
- [Akile美国](https://akile.ai/shop/server?areaId=2)、[轻量云](https://akile.ai/shop/light-server)。
- [Medusa分类文档](https://docs.medusajs.com/user-guide/products/categories)、[商品模块](https://medusajs.com/product-module)。

新机测试必须在实际购买或取得试用后进行：只迁移应用与有效数据，限制历史发布包留存；隔离通知发送、压测预约和图纸生成、备份恢复，再验证微信登录/服务通知、邮件、Mac短信桥和小红书导入。迁移前不改变生产DNS。
