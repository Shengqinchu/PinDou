# PinDou 部署运维文档

> **目标环境**：生产（上海 8C16G 20Mbps）
> **撰写**：Claude Code 2026-05-24（初版骨架）
> **状态**：🟡 待 Codex Phase 2 任务 0 完成后填实硬件 / 网络 / 软件版本字段
> **更新策略**：Codex / 用户 / 我 任何人改服务器配置必须同步更新本文件

---

## 1. 服务器信息

### 1.1 上海生产机
| 字段 | 值 |
|------|----|
| 区域 | 华东-上海1（国内云） |
| 操作系统 | Ubuntu 22.04 64-bit |
| 配置 | 8 核 / 16 GB RAM / 20 Mbps |
| 硬盘 | **待 Codex 任务 0 查（`df -h` + `lsblk`）** |
| 公网 IP | 见 `.env` `PINDOU_PROD_SSH_HOST` |
| SSH 用户 | 见 `.env` `PINDOU_PROD_SSH_USER` |
| SSH 凭证 | 见 `.env` `PINDOU_PROD_SSH_PASS`（**P0 待改 SSH key 认证**） |
| 到期日期 | 2026-09-25 22:41:52（**P1 提前 7 天提醒续费**） |

### 1.2 备份策略
- 当前：无（Phase 2 任务 0 后补）
- 目标：每日 PatternSheet 数据库快照 + 每周完整 backup

---

## 2. P0 安全 TODO（Phase 2 部署前必须做）

### 2.1 改 SSH key 认证 + 禁 root 密码登录
**为什么**：root + 密码 + 公网 IP = 最常见被爆破的攻击面。
**操作**（10 分钟）：
```bash
# 在本机生成 SSH key pair（如果还没有）
ssh-keygen -t ed25519 -C "pindou-prod"

# 把公钥推到服务器
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@36.137.177.135

# 测试 key 登录成功后，禁用密码登录
ssh root@36.137.177.135 "sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config && systemctl reload sshd"

# 验证密码登录已禁
ssh -o PreferredAuthentications=password root@36.137.177.135   # 应该报错
```
**完成后**：从 `.env` 删除 `PINDOU_PROD_SSH_PASS`，添加 `PINDOU_PROD_SSH_KEY_PATH`。

### 2.2 改 root 改成普通用户 + sudo
**为什么**：所有部署 / 应用都用 root 运行，被入侵就是 root 权限。
**操作**：
```bash
# 创建 pindou 用户
adduser pindou
usermod -aG sudo pindou
# 把公钥也加到 pindou 账号
mkdir -p /home/pindou/.ssh && cp /root/.ssh/authorized_keys /home/pindou/.ssh/ && chown -R pindou:pindou /home/pindou/.ssh
```

### 2.3 防火墙 + fail2ban
```bash
apt update && apt install -y ufw fail2ban
ufw default deny incoming
ufw allow 22/tcp     # SSH
ufw allow 80/tcp     # HTTP（Nginx）
ufw allow 443/tcp    # HTTPS
ufw enable
systemctl enable --now fail2ban
```

---

## 3. 部署架构（Phase 2 目标）

```
公网用户
    │
    ↓  HTTPS
[Nginx :443]  ← Let's Encrypt 证书（待域名备案后申请）
    │
    ├─→ /api/*   → [FastAPI :8000]  (后端业务)
    ├─→ /static/* → 本地磁盘 + Nginx 静态服务（用户作品图）
    └─→ /admin/* → [FastAPI :8000] (CDK 管理后台 + 客服面板)
                          │
                          ↓
                  [SQLite or PostgreSQL]
                  (Phase 2 选型，Codex 推荐)
                          │
                          ↓
                  [本地磁盘 /var/pindou/data/]
                  - 用户原图（30 天后定时删除，ADR-009）
                  - AI Preview 图（永久保存）
                  - PatternSheet JSON（永久保存）
                          │
                          ↓
                  [反代 gpt-image-2 调用]
                  https://gpt.xiaochisaascn.org/v1
                  （ADR-007 用户已接受风险）
```

---

## 4. 软件栈（Codex Phase 2 任务 1 确认 / 安装）

| 组件 | 版本目标 | 备注 |
|------|---------|------|
| Python | 3.11+ | FastAPI 性能最优 |
| FastAPI | 最新稳定 | 后端框架 |
| Uvicorn | 最新稳定 | ASGI server |
| SQLite or PostgreSQL | — | Codex 选型；MVP 期 SQLite 够，1 万用户后切 PG |
| Nginx | apt 默认 | 反代 + 静态文件 |
| systemd | 自带 | 服务管理 |
| Let's Encrypt（certbot） | apt 默认 | HTTPS 证书 |
| Pillow + numpy + scikit-learn | 最新 | PatternBuilder 算法依赖 |
| colormath | 最新 | CIEDE2000 |
| openai SDK | 最新 | 反代调用 |
| python-dotenv | 最新 | 读 .env |

---

## 5. 部署流程（Phase 2 末执行）

### 5.1 首次部署
```bash
# 1. SSH 进服务器（已改 SSH key）
ssh pindou@36.137.177.135

# 2. 拉代码
git clone <repo> /opt/pindou
cd /opt/pindou

# 3. 装依赖
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. 配置 .env（从本地 scp 上去，永远不入 git）
scp .env.production pindou@36.137.177.135:/opt/pindou/.env

# 5. 启动 systemd 服务
sudo cp deploy/pindou.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pindou

# 6. 配置 Nginx
sudo cp deploy/nginx.conf /etc/nginx/sites-available/pindou
sudo ln -s /etc/nginx/sites-available/pindou /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 7. 申请 HTTPS 证书（域名备案完成后）
sudo certbot --nginx -d pindou.cn -d www.pindou.cn
```

### 5.2 滚动更新
```bash
cd /opt/pindou
git pull
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart pindou
```

---

## 6. 备案流程（Phase 2 末同步启动）

### 6.1 ICP 个人备案
- **耗时**：申请到下证 7-15 工作日（运气好 7 天，运气差 15+）
- **要求**：身份证 + 手持照 + 域名（30 元/年）+《信息安全承诺书》
- **平台**：所选云服务商的备案系统（用上海机的云厂商）

### 6.2 小程序备案
- 个人主体（ADR-006）
- 类目：**工具 > 图像处理**（**不**选 AIGC，Task F 建议）
- 与 ICP 备案可并行启动

### 6.3 域名准备
- 候选：`pindou.cn`（用户去查可用性）
- 避开关键词：ai / gpt / chat / gen

---

## 7. 监控（Phase 2 任务 7 落地）

### 7.1 反代健康检查（ADR-007 触发条件）
- 每 5 分钟检查 `https://gpt.xiaochisaascn.org/v1/models`（轻量端点）
- 连续 3 次失败 → 触发告警（Telegram / 邮件 / 微信通知）
- 故障 > 6 小时 → FUTURE_WORK 第 8 条命中 → Claude Code 下次对话强制顶上来提醒

### 7.2 业务指标
- API 调用成功率 / 延迟（Provider 维度）
- 用户漏斗：进入 → 上传 → Preview → PatternSheet → 付费
- 错误率 / 错误类型

### 7.3 系统指标
- CPU / 内存 / 磁盘 / 带宽（Prometheus + node_exporter 或简单 `vnstat`）
- 关键阈值：磁盘 > 80% / 内存 > 90% / 带宽峰值持续 > 80% 告警

---

## 8. ADR-007 监控触发条件（Claude Code 持续盯）

发生以下任一情况，下次对话立刻顶上来：
- [ ] PinDou 月活 ≥ 1 万
- [ ] 任何 PinDou 违规投诉 / 举报
- [ ] 微信小程序审核被拒
- [ ] **反代故障 > 6 小时**（依赖本文件 §7.1 健康检查）
- [ ] 法规 / 平台规则关于境外大模型 / AIGC 口径变化
- [ ] 服务器到期前 30 天未续费

---

## 9. 跨境合规状态（FUTURE_WORK 第 2 条更新）

✅ **已解决**：上海机已就位，用户人像上传不再走跨境路径。Phase 3 提审前 FUTURE_WORK 第 2 条可关闭。

⚠️ **仍有跨境风险**：反代调用 `gpt.xiaochisaascn.org` → OpenAI 美国服务器，用户原图经过反代节点。这是 ADR-007 用户接受的剩余风险，不属于服务器选址问题。
