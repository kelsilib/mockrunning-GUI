"""Portable Windows host using Edge WebView2 and the upstream device adapter."""
import argparse
import asyncio
import ctypes
import json
import importlib
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import runpy
import sys
import threading
import time
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.parse import urlparse

from desktop_backend import DesktopController
from ios_location_controller import web

ROOT = Path(__file__).resolve().parent
web.STATIC = ROOT / "assets"
WINDOW = None

class DesktopBridge:
    def __init__(self):
        self.latest = None
        self.lock = threading.Lock()

    def cache_preferences(self, values):
        # Called asynchronously by WebView JavaScript before the native close event.
        # Evaluating JavaScript from synchronous FormClosing would deadlock WebView2.
        if isinstance(values, dict):
            with self.lock:
                self.latest = values
        return True

class DesktopHandler(web.Handler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path in {"/api/memory", "/api/desktop-health"}:
            if not self.host_allowed():
                self.json({"error": "Host denied"}, 403)
                return
            self.json(self.server.controller.memory.snapshot() if path.endswith("memory") else {"app": "route-studio-desktop", "version": "1.0.0"})
            return
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in {"/api/memory", "/api/refresh-usb", "/api/clear-leftover", "/api/focus"}:
            return super().do_POST()
        try:
            if not self.host_allowed() or (self.headers.get("Origin") and self.headers["Origin"] != "http://" + self.headers.get("Host", "")):
                self.json({"error": "Origin denied"}, 403)
                return
            if self.headers.get_content_type() != "application/json":
                raise ValueError("Content-Type must be application/json")
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= 2_500_000:
                raise ValueError("Invalid request size")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Request must be a JSON object")
            controller = self.server.controller
            if path == "/api/memory":
                self.json(controller.memory.change(data))
            elif path == "/api/focus":
                if WINDOW:
                    WINDOW.restore()
                    WINDOW.show()
                self.json({"ok": True})
            else:
                coroutine = controller._usb_scan() if path.endswith("refresh-usb") else controller.clear_leftover()
                future = asyncio.run_coroutine_threadsafe(coroutine, controller.loop)
                try:
                    future.result(timeout=45)
                except Exception:
                    future.cancel()
                    raise
                self.json(controller.status())
        except Exception as exc:
            self.json({"error": str(exc) or type(exc).__name__}, 400)

def main():
    global WINDOW
    # The original adapter invokes `sys.executable -m pymobiledevice3` for optional WDA forwarding.
    # A frozen host must route that worker command back to the dependency CLI.
    if sys.argv[1:3] == ["-m", "pymobiledevice3"]:
        sys.argv = sys.argv[2:]
        runpy.run_module("pymobiledevice3", run_name="__main__")
        return
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-only", action="store_true")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--port", type=int, default=18765)
    parser.add_argument("--smoke", action="store_true", help="Exercise native WebView without device writes, then close")
    args = parser.parse_args()
    folder = args.data_dir or Path(os.environ.get("LOCALAPPDATA", Path.cwd())) / "RouteStudio"
    folder.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(folder / "desktop.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler], format="%(asctime)s %(levelname)s %(name)s %(message)s")
    url = f"http://127.0.0.1:{args.port}"
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), DesktopHandler)
    except OSError:
        try:
            with urlopen(url + "/api/desktop-health", timeout=2) as response:
                if json.load(response).get("app") != "route-studio-desktop":
                    raise RuntimeError("Port is occupied by another application")
            req = Request(url + "/api/focus", data=b"{}", headers={"Content-Type": "application/json"})
            urlopen(req, timeout=3).close()
            return
        except Exception:
            raise RuntimeError(f"端口 {args.port} 已被占用，请关闭其他程序后重试。")
    server.controller = DesktopController(folder)
    server.daemon_threads = True
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print("Route Studio ready: " + url, flush=True)
    if args.server_only:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            server.controller.close()
            server.shutdown()
            server.server_close()
        return
    import webview
    webview.settings["ALLOW_DOWNLOADS"] = True
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("RouteStudio.Desktop")
    os.environ["WEBVIEW2_USER_DATA_FOLDER"] = str(folder / "WebView2")
    preferences_path = folder / "window.json"
    size = {"width": 1440, "height": 960}
    try:
        saved_size = json.loads(preferences_path.read_text(encoding="utf-8"))
        size = {"width": max(1100, min(2500, int(saved_size["width"]))), "height": max(740, min(1800, int(saved_size["height"])))}
    except Exception:
        pass
    bridge = DesktopBridge()
    WINDOW = webview.create_window("Route Studio", url, min_size=(1100, 740), background_color="#faf9f5", js_api=bridge, **size)

    def on_closing():
        # Keep the window open when cleanup fails, so the user can reconnect and retry.
        try:
            with bridge.lock:
                preferences = bridge.latest
            if isinstance(preferences, dict):
                server.controller.memory.change({"action": "preferences", "values": preferences})
        except Exception:
            logging.exception("Could not capture final window preferences")
        try:
            if server.controller.status()["connected"]:
                server.controller.call("stop")
                time.sleep(5)
                server.controller.call("disconnect")
        except Exception as exc:
            logging.exception("Close cleanup failed")
            ctypes.windll.user32.MessageBoxW(None, "定位清理未完成，请保持手机连接，在软件中停止并清除模拟后再关闭。\n\n" + str(exc)[:250], "Route Studio", 0x30)
            return False
        preferences_path.write_text(json.dumps({"width": WINDOW.width, "height": WINDOW.height}), encoding="utf-8")
        return True

    WINDOW.events.closing += on_closing
    smoke_result = {}
    def native_smoke():
        time.sleep(3)
        try:
            modules = ["pymobiledevice3.remote.userspace_tunnel", "pymobiledevice3.services.dvt.instruments.location_simulation", "pymobiledevice3.services.dvt.instruments.dvt_provider"]
            for module in modules:
                importlib.import_module(module)
            result = WINDOW.evaluate_js("({title:document.title, webview:!!window.pywebview, width:innerWidth, service:document.querySelector('#service').textContent, routes:document.querySelector('#route-total').textContent})")
            status = server.controller.status()
            result.update(device_modules_imported=modules, usb_count=len(status["desktop"]["usb_devices"]), location_service_connected=status["connected"], passed=True)
            smoke_result.update(result)
        except Exception as exc:
            logging.exception("Native smoke test failed")
            smoke_result.update(passed=False, error=str(exc))
        finally:
            (folder / "native-smoke.json").write_text(json.dumps(smoke_result, ensure_ascii=False, indent=2), encoding="utf-8")
            WINDOW.destroy()
    try:
        webview.start(native_smoke if args.smoke else None, gui="edgechromium", private_mode=False, storage_path=str(folder / "WebView2"), debug=False, icon=str(ROOT / "assets/route-studio.ico"))
    finally:
        server.controller.close()
        server.shutdown()
        server.server_close()
    if args.smoke and not smoke_result.get("passed"):
        raise RuntimeError("Native smoke test failed: " + smoke_result.get("error", "unknown"))

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        logging.exception("Desktop startup failed")
        if "--server-only" not in sys.argv and "--smoke" not in sys.argv:
            ctypes.windll.user32.MessageBoxW(None, "启动失败：" + str(error) + "\n请确认已安装 Microsoft Edge WebView2 Runtime。", "Route Studio", 0x10)
        if getattr(sys, "frozen", False):
            sys.exit(1)
        raise
