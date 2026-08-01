# Bilibili Drops Miner macOS

这是 [mi0e/BiliBiliDropsMiner](https://github.com/mi0e/BiliBiliDropsMiner) 的 macOS 增强 fork。它保留多房间、多会话、任务进度和通知能力，并补充了 Cookie 持久化、当前 Chrome 账号同步，以及从直播间自动解析任务 ID 的完整流程。

- [下载最新 Release](https://github.com/MarchPhantasia/BiliBiliDropsMiner/releases/latest)
- [上游项目](https://github.com/mi0e/BiliBiliDropsMiner)

## 本 fork 的改动

- GUI 自动保存最后一次输入或同步成功的 Cookie，重启后自动恢复。
- 提供 Chrome 配套扩展，从当前 Chrome Profile 读取已登录的 Bilibili Cookie，无需在临时浏览器中重复登录。
- 输入直播间号后按 Enter，或点击任务 ID 右侧的自动获取，即可打开直播间并解析任务 ID。
- 自动点击页面中可见的 DAY 任务标签，并监听真实的 `/x/task/totalv2` 请求。
- 检测到多个日期任务组时弹出选择框；同一日期存在多个任务时自动用逗号合并。
- 保留临时 Chrome / Edge 自动登录流程作为 Cookie 获取的后备方案。

## macOS 快速开始

1. 从 [Releases](https://github.com/MarchPhantasia/BiliBiliDropsMiner/releases/latest) 下载 DMG。
2. 打开 DMG，将 `Bilibili Drops Miner.app` 拖入 `Applications`。
3. 首次启动如被 Gatekeeper 拦截，在 Finder 中右键应用并选择“打开”。
4. 填写 Cookie 和直播间号，按 Enter 自动获取任务 ID，然后点击“启动”。

发布包目前使用 ad-hoc 签名，未做 Apple notarization。只应从本仓库 Release 下载，并先核对 Release 中提供的 SHA-256。

## 使用当前 Chrome 账号

macOS 应用内置一个 Manifest V3 配套扩展。首次点击 Cookie 右侧的“自动获取”时：

1. 在自动打开的 `chrome://extensions/` 页面开启“开发者模式”。
2. 点击“加载已解压的扩展程序”。
3. 选择应用内的扩展目录：

   ```text
   /Applications/Bilibili Drops Miner.app/Contents/Resources/chrome_extension
   ```

4. 回到应用，再次点击 Cookie 的“自动获取”。

扩展安装后的固定 ID 为 `illpcmbmojgliojnfhleklbdonlhmhfc`。也可以点击 Chrome 工具栏中的扩展图标手动同步。

扩展只申请：

- `cookies`：读取 `.bilibili.com` 下白名单中的登录 Cookie。
- `nativeMessaging`：把 Cookie 发送给本机的 Bilibili Drops Miner。
- `https://*.bilibili.com/*`：限制站点访问范围。

本机接收端只接受这个固定扩展 ID，并只保存 `SESSDATA`、`bili_jct`、`DedeUserID` 等必要字段。Cookie 通过 Qt `QSettings` 保存在当前 macOS 用户配置中，属于本机明文持久化，不是 Keychain 加密存储。不要共享配置文件、Cookie 或包含 Cookie 的截图。

## 自动获取任务 ID

在“房间号”中输入直播间 URL 末尾的数字，例如 `23612045`，然后按 Enter。程序会用一个独立的 Chrome / Edge 会话打开：

```text
https://live.bilibili.com/23612045
```

程序会依次点击直播页的 DAY 标签，从网络日志中的 `totalv2` 请求读取当前标签对应的 `task_ids`。若页面没有生成请求，则回退解析 `window.__initialState.EraTasklistPc`。

- 多个 DAY：弹出任务组选择框。
- 同一 DAY 多个任务：写入逗号分隔的多个 ID。
- 未检测到任务：确认该直播间当前存在掉宝活动后重试。

`totalv2` 是已知任务 ID 的进度查询接口；任务 ID 本身来自直播活动页面的数据和标签交互，而不是通过房间号直接查询 `totalv2` 得到。

## 其他功能

- 多房间并发挂机，每个房间可配置多个会话。
- 任务进度自动轮询和手动刷新。
- Gotify、Server 酱通知。
- GUI 配置导入/导出、运行日志和任务完成提醒。
- CLI 模式，适合服务器或纯命令行环境。

## 源码运行

需要 Python 3.10 或更高版本：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python bilibili_gui.py
```

CLI 示例：

```bash
python bilibili.py \
  --cookie "SESSDATA=xxx; bili_jct=xxx" \
  --rooms "23612045" \
  --task-ids "taskId1,taskId2"
```

查看全部参数：

```bash
python bilibili.py --help
```

## 构建 macOS 应用

在目标架构的 Mac 上安装依赖后执行：

```bash
python build.py --target gui --clean --dmg
```

产物位于：

```text
dist/Bilibili Drops Miner.app
dist/Bilibili Drops Miner-macOS.dmg
```

PyInstaller 会将 Selenium、Chrome 配套扩展和 Native Messaging 接收端一起打入 `.app`。在 Apple Silicon Mac 上构建的是 arm64 产物；Intel 版本需要在 x86_64 Python 环境构建。

## 测试

```bash
python -m unittest discover -s tests -v
```

测试覆盖 Cookie 持久化、Chrome 配套扩展、Native Messaging、直播页任务分组解析、GUI 状态和既有任务逻辑。

## 常见问题

### 为什么 Cookie 自动获取仍然打开了新浏览器？

当前 Chrome Profile 同步仅用于已安装的 macOS `.app` 和 Google Chrome。源码运行、未安装配套扩展、使用 Edge，或 Native Messaging 注册失败时，会自动回退到临时浏览器流程。

### 为什么任务时长一直为 0？

平台任务进度不是实时结算的，启动后通常要等待至少 30 秒。若预估观看时长增长但接口进度长期不变，可能是账号风控或活动状态变化，应先停止工具并在官方直播页验证。

### 线程数是否越高越好？

不是。过高的并发或频繁启停会增加请求失败和账号风控风险。请从较小值开始，根据网络与任务进度逐步调整。

## 免责声明

本项目仅供个人学习和研究，不保证稳定性或任务结果。请遵守 Bilibili 服务条款、活动规则和所在地法律法规；使用本项目产生的后果由使用者承担，禁止商业用途。

## License 与致谢

本 fork 基于 [mi0e/BiliBiliDropsMiner](https://github.com/mi0e/BiliBiliDropsMiner)，保留上游项目的作者归属。上游 README 将项目标注为 MIT，请同时查阅上游仓库的许可说明。
