# 手机预约时间表与微信联系方式修复

来源：店主 2026-09-12 的三张标注截图（59bb7306、8dee349a、22d5d26c）。

## 行为变化

- 预约的微信联系方式最少 1 个非空字符；姓名、联系方式仍必须按原预约规则提供，邮箱及手机号仍按原格式校验。共享的预约资料编辑、资料完整性、自动保存和老客历史回填同步接受短微信联系方式。独立的可加好友微信号字段 `wechat_id` 不在此次变更中。
- 时间表图例和选中区间共用浅紫色及边框色，开始格保留稍深的紫色。
- 700px 以下的手机网页选时步骤允许整页纵向滚动；时间表至少 520px，并随可见高度增加。日期表头在表格内部固定，底部上一步/下一步随页面滚动保持可点击。其他预约步骤继续使用原有键盘和视口布局。
- 时间表下新增“预约时长至少 2 小时” / “Minimum booking: 2 hours.”。服务端原有最低 120 分钟、营业时间、加班费及预约确认规则不变。
- 本轮修改网站及其预约服务；未改动、上传或提交微信小程序包。

## 验证

后端命令：

```powershell
python -X utf8 -m pytest 06_studio/test_booking_contact.py 06_studio/test_booking_profile.py 06_studio/test_returning_reservations.py 06_studio/test_reservations.py 06_studio/test_capacity_buffer.py -q
```

52 项通过。新增回归覆盖一个汉字、两个汉字及单个表情，预约提交、幂等重试、资料编辑、下次预约复用和同账号历史回填；空白、无效邮箱和手机号继续拒绝。

浏览器命令：

```powershell
node 05_studio/scripts/verify-booking-mobile.mjs
```

使用隔离临时 SQLite、假登录与支付网关，监听回环端口 8011；构建后的前端由 4184 端口提供。Chromium 和 WebKit 的六组窗口各自验证选时、2.5 小时延长、图例颜色、两小时提示、返回及重载保留、联系方法切换。每种浏览器另用独立假用户成功提交“猫”并重试，确认资料保存和同一预约返回。测试不产生生产预约、不发送真实通知。

| WebKit 窗口 | 上线前时间表高度 | 修改后时间表高度 |
|---|---:|---:|
| 390 × 700 | 224.42px | 520px |
| 390 × 844 | 368.42px | 788px |
| 320 × 568 | 150px | 520px |
| 430 × 932 | 456.42px | 964px |

同时检查 1440 × 900 桌面及 844 × 390 横屏，均无横向溢出。桌面/横屏保留原来一屏内操作的布局。这些是浏览器模拟测试，不替代真实 iPhone 设备测试。

`npm run build` 通过（含文案契约、TypeScript 和 Vite）。文案仅批准新增最低时长提示；默认文案导出时发现其他历史模块有差异，最终发布只纳入本次新增提示，避免覆盖其他经营内容。

## 发布与证据

- 发布：`20260913024413-studio-v7`
- 前端 build：`2026-09-13T02:37:52.300Z`
- 发布包 SHA256：`f743e48755c6adf2f263affc8d885bb2ebc88b64dd10445bd22f3728b1ce7627`
- 增量包：714852 bytes；399 个文件完整校验。
- 服务文件变化仅 `reservations.py`、`booking_profile.py`、`content-defaults.json`。
- 回滚基线：`20260913012550-studio-v7`。
- 发布前备份：`/opt/pindou/studio/backups/20260913024413-studio-v7/`。
- 当前原生成器：`/opt/pindou/releases/20260910015453-studio-v7`，未替换；两个服务均 active。
- 相对即时发布备份，243 商品、21 分类、16 预约、8 预约资料、16 会员、23 钱包明细、12 日记、4 收支记录、1 商城配置、69 内容模块逐行不变。

证据目录：`artifacts/booking-mobile-20260912/`。`baseline.json` 为修改前公网尺寸；`browser-verification.json` 为本地双浏览器端到端结果；`origin-verification.json` 为源站文件、服务、模式校验及业务数据比较；`live-verification.json` 为公网相同浏览器检查，所有状态必须匹配本轮 build，且禁止提交生产预约。

公网 WebKit 首次检查的全部功能断言通过，但 Cloudflare `cdn-cgi/rum` 统计请求产生访问控制诊断。原始结果保存在 `live-with-telemetry-errors.json`；最终测试单独记录这一确切第三方诊断，预约应用错误仍会使测试失败。未修改网站统计配置。

公网验证命令：

```powershell
$env:PINDOU_QA_ORIGIN = 'https://pindoupuppy.com'
node 05_studio/scripts/verify-booking-mobile.mjs
```
