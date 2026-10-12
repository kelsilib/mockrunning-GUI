# 本地开发与打包 / Development and packaging

完整说明：[简体中文](../README.md) · [English](../README.en.md)。上游驱动、网页、CLI 和 Android 用法见 [README.upstream.md](../README.upstream.md)。

要求：Windows、Python 3.12、Edge WebView2 Runtime。以下准备命令在仓库根目录执行，无需激活虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]" -r route-studio-desktop/requirements-desktop.txt
.\.venv\Scripts\python.exe route-studio-desktop/desktop_app.py
```

桌面端默认只监听本机 `127.0.0.1:18765`。首次开发运行请勿与打包版同时使用同一份数据。

## 自动测试 / Automated tests

从仓库根目录执行。桌面测试使用模拟设备，不发送真机位置：

```powershell
$env:PYTHONPATH = "$PWD\route-studio-desktop"
.\.venv\Scripts\python.exe -m pytest tests route-studio-desktop/tests -q
```

## 打包 / Build

```powershell
cd route-studio-desktop
..\.venv\Scripts\python.exe -m PyInstaller --noconfirm --distpath ..\dist --workpath ..\build RouteStudio.spec
..\.venv\Scripts\python.exe package_release.py
```

程序：`dist/RouteStudio/RouteStudio.exe`。发布文件：`outputs/RouteStudio-Windows.zip`、`RouteStudio-Source.zip`、`desktop-release-manifest.json`。输出目录已忽略，不提交到 Git；Windows ZIP 可上传到 GitHub Releases。

`package_release.py` 只收集指定的源码目录及根目录文件，过滤缓存和安装元数据；不会打包 `%LOCALAPPDATA%\RouteStudio` 中的个人数据。

## 原生窗口检查 / Native smoke check

从仓库根目录执行。不发送模拟位置，使用单独的数据目录并自动退出窗口：

```powershell
.\.venv\Scripts\python.exe route-studio-desktop/desktop_app.py --smoke --data-dir smoke-data --port 18768
```

## 浏览器与 USB 检查 / Browser and USB checks

先在一个终端启动独立测试服务，保持运行：

```powershell
.\.venv\Scripts\python.exe route-studio-desktop/desktop_app.py --server-only --data-dir qa-data --port 18766
```

在另一个终端、仓库根目录运行浏览器测试。需已安装 Microsoft Edge；测试会写入 `qa-data` 的示例路线和配置，首次运行使用空目录：

```powershell
.\.venv\Scripts\python.exe route-studio-desktop/browser_qa.py
```

截图输出到 `artifacts/desktop-preview/`。USB 观察脚本只读取该服务的状态；安装 `requests` 后执行，并手动插拔手机：

```powershell
.\.venv\Scripts\python.exe -m pip install requests
.\.venv\Scripts\python.exe route-studio-desktop/usb_observe.py
```

USB 报告输出到 `artifacts/usb-physical-test.json`。这些辅助脚本不会主动连接定位服务或发送模拟位置。

`make_assets.py` 可从上游网页生成桌面 HTML；会覆盖 `assets/index.html`，仅在明确需要重新生成时运行。
