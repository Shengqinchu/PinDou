# PinDou 新服务器筛选与实测（2026-09-12）

用户条件：客户主要在加拿大；保留微信小程序；参考现有移动云，全年预算约人民币 500 元以内。未购买新服务器，未改 DNS 或迁移生产数据。

## 建议

优先试 OVHcloud 加拿大东部 Beauharnois 的 VPS-1 2027：2 vCPU、4GB RAM、40GB NVMe、500Mbps、无限流量，含前一天自动备份。当前配置页可选加拿大机房并显示 Available now。无合约月付 CAD 7.30；12 个月合约 CAD 74.40，均未含税，自动续订相同合约周期。建议先月付验证实际分配的机器，再决定是否改年付。

备选 RackNerd New York 或 Chicago 的 4GB KVM Special：3 vCPU、4GB、60GB SSD RAID-10、每月 7TB 流量、1Gbps 端口，USD 59.99/年。购物车已核对套餐、年付价及这两个可选机房；尚未付款。额外 CPU/RAM 会加价，不属于表内基础价格。

### 价格与预算

| 方案 | 核实的基础价格（税前） | 约合人民币 | 取舍 |
|---|---|---|---|
| OVH 加拿大 VPS-1，12个月 | CAD 74.40/年 | 360元/年 | 本地机房、NVMe、含前一天备份；40GB须按应用迁移，控制历史包和备份留存 |
| OVH 加拿大 VPS-1，无合约 | CAD 7.30/月 | 35元/月 | 适合先开一台做真实应用验收 |
| RackNerd 4GB Special | USD 59.99/年 | 402元/年 | 多一核、60GB空间；需另做异机备份，年付前没有这台VM的CPU/磁盘结果 |
| 现有上海移动云 | 用户提供：不到500元/年 | 不到500元/年 | 8核16GB硬件便宜；当前加拿大动态请求需要跨洋回源 |

换算使用加拿大央行 2026-09-11 指示汇率：1 CNY = CAD 0.2067、1 USD = CAD 1.3866。实际税费、支付汇率和续期价格以订单为准。数字不是锁定的人民币结算价。

DigitalOcean 官方基础 2核4GB80GB报价 USD24/月、4核8GB160GB USD48/月，超出本次预算。CloudCone 当前4GB产品 USD92/年，也高于本轮目标。Hetzner 美国区域已调整价格，不能套用旧的欧洲低价文章；本轮不优先。

## 当前服务器观察

SSH 实测：8 vCPU、15,796MiB 内存、Ubuntu22.04.5、根盘79GiB/已用32GiB。`pindou`、`pindou-studio`、Nginx 和 cloudflared 均 active，公网 `/health` 200。

本次20秒观察：CPU使用率0.25%–2.12%，可用内存14,889MiB，swap未使用；两个业务服务内存约282.5MiB和64.2MiB。负载均值约0.05。只能证明当前低负载，不能推断峰值并发容量。

共享目录抽样：生成器 shared154MiB、Studio shared15MiB；历史生成器 releases16GiB、Studio releases2.1GiB。新机40GB应迁移有效应用与数据、保留有限回滚版本，不能把整盘及所有旧发布目录原样复制过去。未清理现有机器任何数据。需要进一步核对全部存储路径并做恢复测试后才能切换。

## 网络实测

用 Globalping 公共探针从多伦多3个网络、蒙特利尔2个网络测量，单轮每探针3次ICMP。测试是短时线路快照，不能保证长期可用性，也不是新购VM的CPU、磁盘或应用性能测试。

| 目标 | 多伦多各探针平均RTT | 蒙特利尔各探针平均RTT | 本轮丢包 |
|---|---|---|---|
| OVH BHS 官方测试点 `bhs.proof.ovh.ca` | 7.94 / 7.37 / 7.94 ms | 0.48 / 1.55 ms | 0/15 |
| RackNerd New York 官方测试IP | 40.17 / 12.55 / 31.76 ms | 13.95 / 11.32 ms | 0/15 |
| RackNerd Chicago 官方测试IP | 12.17 / 14.90 / 13.63 ms | 18.83 / 24.07 ms | 0/15 |

另测当前 `https://pindoupuppy.com/health`：5探针均HTTP200，HTTPS总耗时416/440/444/441/1080ms。Cloudflare标记DYNAMIC，报告的回源耗时357–946ms。该HTTP指标含连接、TLS及回源，与上表ICMP不同，不能直接相除当作迁移提速倍数。

## 小程序与迁移

核对现有 `05_frontend/src/utils/request.ts`：正式小程序使用 HTTPS 请求 `https://pindoupuppy.com/api/v1`；正式包禁用历史 `wx.cloud.callContainer` 路由。Studio请求也走同一网站域名。因此客户在加拿大运行小程序时，可直接访问加拿大后端，不需要仅因微信平台位于中国而把业务源站放上海。

迁移应保持正式域名、HTTPS、合法域名配置，以及网站/小程序共用的用户ID与数据库。新机必须实际验证微信登录和订阅消息接口、邮件发送、Mac短信桥、头像上传、小红书导入和文件下载；核对任何来源IP白名单。用户在手机微信完成一次只读/测试预约流程后再切流量。不要使用开发者工具“忽略域名校验”代替正式验收。

开机后的验收：先做 CPU、内存、磁盘和网络基线；在隔离数据库、屏蔽所有通知外发的测试环境，验证预约、图纸生成、导入和1/5/10并发的耗时及错误；测试备份恢复。新机未购买，以上VM测试当前未执行。

## 官方来源与证据

- OVH产品：https://www.ovhcloud.com/en-ca/vps/
- 已核对配置页：https://www.ovhcloud.com/en-ca/vps/configurator/?planCode=vps-2027-model1&brick=VPS%2BModel%2B1&pricing=upfront12&vcore=2__vCore&storage=40__SSD__NVMe
- OVH官方网络测试：https://proof.ovh.net/ → BHS https://bhs.proof.ovh.ca/
- RackNerd当前套餐：https://www.racknerd.com/specials/ ，4GB产品购物车 https://my.racknerd.com/cart.php?a=add&pid=954
- DigitalOcean：https://www.digitalocean.com/pricing/droplets
- CloudCone：https://cloudcone.com/vps/
- Hetzner价格变更：https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/
- 加拿大央行：https://www.bankofcanada.ca/rates/exchange/ 、https://www.bankofcanada.ca/valet/observations/FXCNYCAD,FXUSDCAD/json?recent=1
- Globalping：https://globalping.io/ 、https://github.com/jsdelivr/globalping/blob/master/public/v1/spec.yaml

原始资料：`artifacts/server-information-20260912/` 中的 current.json、load.json、fx.json、globalping-result.json、ovh-bhs-result.json、racknerd-ny-result.json、racknerd-chicago-result.json及两家实际配置页报价。未把供应商宣传、共享vCPU数量或“端口1Gbps”当作这台未购买VM的专属性能保证。
