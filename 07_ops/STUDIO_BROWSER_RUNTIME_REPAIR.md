# Codex内置浏览器运行组件修复

2026-09-09 UTC。店主要求直接操作右侧已登录的Authing页面，明确不切到独立Chrome。

## 根因与恢复

当前用户配置的`in_app_browser`、`browser_use`、`browser_use_external`及`browser_use_full_cdp_access`本来均为true。页面可见，但普通工具列表没有暴露原生CUA入口。

官方安装包的`unified-computer-use/resources/banner-browser.js`给出了`@oai/cua/tinyskyAlt`的`setupCUA({browser:true,computer:false})`入口。实际初始化报错：找不到`C:\Users\123\.codex\plugins\cache\openai-bundled\browser\26.901.51231\scripts\browser-service.mjs`。

同版本原始组件实际位于：

`C:\Program Files\WindowsApps\OpenAI.Codex_26.901.6511.0_x64__2p2nqsd0c76g0\app\resources\cua_node\bin\node_modules\@oai\browser-desktop`

已恢复其scripts、docs和package.json，共33个文件到缺失缓存目录，逐个比较SHA-256。Windows普通Copy-Item会试图复制安装包文件的加密属性并失败，实际采用读取／写入文件字节，未修改内容。node_modules目录通过junction引用同一官方安装包的依赖。未修改安装包、运行库源码、权限开关或浏览器用户数据。

browser-service.mjs的SHA-256：`3032666de451e423db76b5f9b0456e370d4f57416bbf53d0c746be636359ba02`。

由于失败的ESM导入被当前Node REPL缓存，恢复文件后还需重置一次尚未初始化成功的内核，再执行官方bootstrap。初始化成功后保留同一个会话和浏览器句柄，不能反复重置。

## 验证

- `cua.getState()`返回一个Codex In-app Browser，类型iab；其中唯一标签的标题与URL匹配店主的“PC小程序扫码”配置页。
- 使用`cua.getTab()`获取原标签，基于实际AX/DOM状态完成显示名、创建身份源、关联应用和默认扫码方式设置。
- 新建同一内置浏览器的托管登录体验标签，实际读到“使用微信扫码登录”和二维码。
- 费用管理实际读到B2C免费版、0/8,000 MAU、有效期无限期。
- 临时桌面尺寸覆盖已reset；控制台和体验标签已标记保留以供后续验收。

详细哈希清单在忽略目录`artifacts/authing-setup/browser-runtime-repair.json`。以上路径和版本仅对应这次已核验的Codex安装；应用更新后必须重新核对实际版本，不能把旧路径当永久配置。

此前独立Chrome自动连接失败只是选错了通道，与内置浏览器是否打开无关。今后本任务优先复用当前CUA/iab会话，避免让店主重新登录或设置无关的Chrome远程调试。
