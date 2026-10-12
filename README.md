<div align="center">

# Route Studio

**把路线，留在手边。**

Windows 桌面路线编辑与定位测试工作台

**简体中文** · [English](README.en.md)

[快速开始](#快速开始) · [开发与打包](#开发与打包) · [USB 与恢复](#usb-与恢复) · [上游项目](https://github.com/yinsuecci/mockrunning)

</div>

---

Route Studio 为 [mockrunning](https://github.com/yinsuecci/mockrunning) 增加了独立的 Windows 桌面窗口：将路线地图和控制页面内嵌到软件中，并提供路线库、本地记忆和 iPhone USB 状态检测。界面采用暖白底色、陶土色点缀与简约排版。

桌面版沿用上游定位适配器，核心代码位于 `src/`。本仓库是原项目的 fork，新增桌面功能位于 `route-studio-desktop/`。

## 功能

| 功能 | 说明 |
| --- | --- |
| 路线编辑 | 在地图上添加、拖动和删除节点，导入与导出 GPX；节点之间直线连接 |
| 路线库 | 保存多条路线、命名并搜索，重新打开后继续使用 |
| 回放控制 | 开始、暂停、停止与清除模拟；保存常用配速及参数配置 |
| 本地记忆 | 保留草稿、地图位置、上次页面、窗口大小与回放历史 |
| USB 检测 | 展示 iPhone 连接、信任及开发者模式状态；区分物理连接与定位服务连接 |
| 中断处理 | 拔线时停止回放，保留路线并记录中断；重连后提示清除遗留定位 |

历史记录描述本软件的模拟回放，不代表真实运动或第三方平台记录。软件不会自动连接设备、开始回放或提交第三方记录。

## 快速开始

### 使用 Windows 打包版

如果仓库 [Releases](https://github.com/kelsilib/mockrunning-GUI/releases) 已提供 Windows 发布包，下载并解压，然后运行 `RouteStudio/RouteStudio.exe`。必须保留同目录的 `_internal/`；不能只复制一个 EXE。

打包版不需要另装 Python，但仍需要：

- Windows 11；其他 Windows 版本尚未验证。
- 可用的 Microsoft Edge WebView2 Runtime。
- Apple Devices / Apple Mobile Device Support 提供的设备通信支持。
- iPhone 已解锁并信任电脑，开发者模式已开启并完成重启确认。
- 与 iOS 版本匹配且可用的开发服务及 DDI；这些条件影响定位连接，USB 被发现并不代表已准备完成。

本说明不表示当前已有可下载的 Release。源码运行方法见下文。

### 第一次回放

1. USB 连接并解锁 iPhone，确认左下角连接状态。
2. 在“布设路线”编辑或导入 GPX，保存到路线库。
3. 在“手机回放”载入路线，点击“连接手机”。**已有路线时连接会发送起点；已连接时载入路线也会发送起点。**
4. 设置参数并点击“保存参数”，然后点击“开始移动”。暂停后可以修改参数。
5. 结束时点击“停止并清除模拟”，等待几秒，并在手机普通地图中确认真实位置恢复，再断开连接。

地图底图和地点搜索需要联网。底图不可用时，仍可编辑坐标和使用已有路线；软件不会自动沿道路规划。

## USB 与恢复

USB 状态约每秒轮询一次；配对和开发者模式读取可能需要额外几秒。

| 状态 | 含义与操作 |
| --- | --- |
| USB 已连接 | Apple usbmux 已发现设备；定位服务尚可能未连接 |
| 等待信任 / 请解锁 | 在 iPhone 上解锁并确认“信任此电脑” |
| 开发者模式未开启 | 在 iPhone 设置中开启，重启后再次确认 |
| 检测异常 | 检查线缆和 Apple 设备通信；检测失败不会被当作拔线 |
| USB 已断开 | 停止当前回放，包括暂停状态；手机上的模拟位置无法在断线时确认清除 |
| 遗留定位提示 | 重新连接并解锁手机，点击“清除遗留定位”，再检查普通地图 |

重新插入 USB 不会自动恢复回放。关闭软件会尝试停止并清除模拟；拔线、强制结束或设备错误仍可能妨碍清理。请求清除成功不等于地图立即恢复，应以手机实际显示为准。

**必须在 iPhone 上手动完成：**解锁、信任电脑、开启开发者模式及重启确认、检查地图定位是否恢复。系统设置和驱动不会由本桌面软件自动安装或更改。

## 本地数据

桌面版数据保存在 `%LOCALAPPDATA%\RouteStudio`，与源码和软件目录分开。

| 文件 | 内容 |
| --- | --- |
| `memory.json` | 路线库、常用配置、偏好和回放历史 |
| `session.json` | 上次载入路线与参数 |
| `window.json` | 窗口设置 |
| `desktop.log` | 本机诊断日志 |
| `WebView2/` | 嵌入式浏览器数据 |

备份前先关闭软件，再复制该数据目录。不要将个人路线、设备信息或日志提交到公开仓库。地图和地点搜索会访问对应的在线服务。

## 开发与打包

桌面版已使用 Python 3.12.14 开发。建议使用 Python 3.12，并在仓库根目录创建虚拟环境。

```powershell
git clone https://github.com/kelsilib/mockrunning-GUI.git
cd mockrunning-GUI
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]" -r route-studio-desktop/requirements-desktop.txt
.\.venv\Scripts\python.exe route-studio-desktop/desktop_app.py
```

如果桌面版尚未合入默认分支，安装前切换到对应分支，例如 `git switch route-studio-desktop`。上述命令要求 Git 和 Python 可在终端调用。

运行上游与桌面测试：

```powershell
$env:PYTHONPATH = "$PWD\route-studio-desktop"
.\.venv\Scripts\python.exe -m pytest tests route-studio-desktop/tests -q
```

生成 Windows 目录式发布包：

```powershell
cd route-studio-desktop
..\.venv\Scripts\python.exe -m PyInstaller --noconfirm --distpath ..\dist --workpath ..\build RouteStudio.spec
..\.venv\Scripts\python.exe package_release.py
```

程序输出至 `dist/RouteStudio/`，发布 ZIP 与校验清单位于 `outputs/`。构建细节与浏览器测试见 [BUILD.md](route-studio-desktop/BUILD.md)。网页、CLI 和 Android 的上游用法见 [原项目说明](README.upstream.md)。

## 验证范围与限制

以下为此前开发阶段的验证记录，不代表每次源码改动都已重新完成全部测试。

- 上游自动测试 101 项、桌面新增自动测试 5 项曾通过；桌面测试覆盖记忆、损坏数据备份、USB 中断与重启恢复。
- 桌面路线库、配置持久化、紧凑窗口布局，以及打包后的 WebView2 启动和退出曾验证。
- 用户配合验证了真机 USB 插入、拔出与重新插入检测；桌面测试没有发送真机模拟位置。
- 此前通过上游定位程序在普通地图中验证了模拟位置和真实位置恢复。
- **桌面版真机定位发送、微信小程序兼容性，以及 Android / 无线连接的真机兼容性尚未验证。**

地图中的“已发送位置”是最近成功发送的坐标，不是手机 GPS 读回。iOS 当前定位适配器只发送经纬度，不模拟步数、姿态、GNSS 原始数据或可配置定位精度。不同应用可能拒绝或以其他方式读取模拟位置。

本项目面向授权设备的定位与应用开发测试，不提供校园跑反作弊规避或第三方成绩提交功能。

## 项目结构

```text
mockrunning-GUI/
├── src/                     # 上游定位核心与网页
├── tests/                   # 上游测试
├── routes/                  # 示例路线
├── route-studio-desktop/     # 桌面窗口、USB 监督、本地记忆与 UI
├── README.md                # 简体中文
├── README.en.md             # English
└── README.upstream.md       # 保留的上游说明
```

## 致谢

基于 [yinsuecci/mockrunning](https://github.com/yinsuecci/mockrunning)，使用 [pymobiledevice3](https://github.com/doronz88/pymobiledevice3)、[pywebview](https://pywebview.flowrl.com/)、[Leaflet](https://leafletjs.com/) 和 OpenStreetMap。感谢上游作者及相关依赖的维护者。
