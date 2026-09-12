# 2核4GB是否足够与免费云复核

2026-09-12，用户质疑小配置是否真能优于国内8核16GB，并询问免费方案。

## 修正结论

**2核4GB只能作为待验收候选，尚没有证据证明它足够承接图纸生成高峰，也没有证明其计算性能超过目前8核16GB。** 原先“优先试OVH”是按加拿大客户访问距离、年预算和空闲观测筛选，不是已完成新VM性能验收。保留现有生产服务器；领到试用或开月付机器后，在隔离副本跑完真实工作负载再决定迁移。

访问体验包含网络往返、排队、计算/数据库处理。加拿大机房可能显著降低加拿大用户等待API响应的网络部分，但图像量化和导出的CPU密集部分仍可能因降配变慢。不同供应商的共享vCPU、CPU型号、超售和磁盘也不能只按“2核对8核”推算倍数。前轮Globalping测的是网络测试点，不是新购虚拟机。

## 本轮实际源站证据

- 仍是x86_64、8个逻辑CPU、Intel Xeon Processor；内存15796MiB。
- 新一轮20秒只读观察：CPU平均0.8315%、最高2.38%，可用内存14866MiB，swap未使用；按总量减可用计算约930MiB。
- 当时生成器服务MemoryCurrent=296091648字节，Studio=51286016字节。没有取得可用的历史memory.peak/max_usage记录，因此不能把这些数当作最高并发占用。
- 核对**已部署**生成器目录 `/opt/pindou/releases/20260910015453-studio-v7/06_backend`：AI图片供应商使用外部OpenAI兼容SDK；本地仍调用PatternBuilder与quantize_to_codes，且存在后台生成线程。因此“模型在外部”不等于服务器没有重计算。
- 本轮没有在生产环境制造压测流量，没有调用付费AI来做合成测试，没有购买/更换服务器。

证据：`artifacts/shop-bulk-20260912/server-load.json`、`live-compute.json`。之前的线路测量见 [服务器筛选记录](PINDOU_SERVER_SELECTION_20260912.md)。

## 免费方案（官方现行说明）

| 方案 | 当前官方额度 | 与小店的关系 |
|---|---|---|
| Oracle Always Free A1 | 当前技术文档：每月1500 OCPU小时、9000GB内存小时，折合持续2 OCPU/12GB ARM。仅home region；可能缺容量；低使用率实例可被回收。 | 免费资源规模确实可大于2核4GB。值得作为实验候选，需先验证开户资格、加拿大机房容量、ARM依赖及备份恢复；不能保证能领到或长期不回收。 |
| Google Cloud永久免费Compute | 美国指定区域1台e2-micro、30GB标准盘、1GB/月出站流量。e2-micro为1GB内存，虽暴露2vCPU，持续CPU份额合计只有0.25vCPU。 | 适合轻量实验，不能等同于一台完整2核4GB网站/图纸服务器；还要核对公网IP等其他费用。另有新客户90天300美元试用额度。 |
| AWS新客户Free Plan | 注册100美元，再完成指定探索活动最多再得100美元；免费计划到6个月或额度耗尽时结束，以较早者为准。 | 是限时/限额试用，可用于候选验证；不是终身免费2核4GB，实际实例可选范围需看账户。 |
| Azure for Students | 符合资格大学生100美元额度、12个月有效，可按学生资格年度续订；无需信用卡，部分新客户免费服务另计。 | 用户有学生背景，但不能推定本次可再领或额度尚存。官方说明用途侧重教学、非商业研究与相关开发测试，不直接把学生优惠当商店长期生产资源。 |
| DigitalOcean旧GitHub学生200美元 | 搜索引擎仍有旧摘要；本轮打开当前GitHub Pack未找到DigitalOcean，旧github-students入口跳转普通首页。 | **未验证仍可领取，不列入已可用免费方案**。不要为了旧文章盲目绑卡或开付费机。 |

Oracle部分地区旧营销页仍写4核24GB，与现行技术文档2核12GB不一致；本轮按技术文档保守计算，最终看账户控制台的Always Free标记与配额。没有申请新账号、提交身份/银行卡或创建收费资源。

## 下一台机器应怎样验收

1. 保持生产网站与数据不动，在新机使用隔离副本并禁用真实通知/支付。
2. 测同一组普通图纸、AI后处理、图片上传导出以及预约查询，记录1/3/5并发的延时、CPU、内存峰值与错误；AI外部耗时单列。
3. 同时从加拿大和需要覆盖的国内网络测登录、预约、图片，比较网络与计算分别耗时。
4. 验证微信服务接口、Mac短信桥、邮件、日记导入、备份与恢复；最后才决定2核4GB、4核8GB或继续国内8核16GB。

## 官方来源

- [Oracle Always Free技术文档](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
- [Google免费额度](https://docs.cloud.google.com/free/docs/free-cloud-features)、[E2共享CPU定义](https://docs.cloud.google.com/compute/docs/general-purpose-machines)
- [AWS Free Tier FAQ](https://aws.amazon.com/free/free-tier-faqs/)
- [Azure for Students](https://azure.microsoft.com/en-us/free/students)、[具体优惠条件](https://azure.microsoft.com/en-us/pricing/offers/ms-azr-0170p)
- [GitHub当前学生包](https://education.github.com/pack/)、[DigitalOcean旧学生入口](https://www.digitalocean.com/github-students)
