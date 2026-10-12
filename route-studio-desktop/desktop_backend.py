"""Desktop persistence and USB supervision around the unchanged upstream controller."""
import asyncio
from dataclasses import asdict
from datetime import datetime, timezone
import json
import logging
import threading
import uuid
from pathlib import Path

from ios_location_controller.playback import PlaybackController
from ios_location_controller.motion import route_points, Settings
from pymobiledevice3.usbmux import list_devices
from pymobiledevice3.lockdown import create_using_usbmux

log = logging.getLogger(__name__)

def timestamp():
    return datetime.now(timezone.utc).isoformat()

class Memory:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.RLock()
        self.data = {"version": 1, "routes": [], "presets": [], "history": [], "preferences": {}, "active_session": None}
        if self.path.exists():
            try:
                saved = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(saved, dict) or saved.get("version") != 1:
                    raise ValueError("Invalid memory file")
                for key in ("routes", "presets", "history"):
                    if not isinstance(saved.get(key), list):
                        raise ValueError("Invalid memory list")
                if not isinstance(saved.get("preferences"), dict):
                    raise ValueError("Invalid preferences")
                self.data = saved
            except Exception:
                backup = self.path.with_name("memory-recovery-" + uuid.uuid4().hex[:8] + ".json")
                backup.write_bytes(self.path.read_bytes())
                log.exception("Memory could not be loaded; preserved recovery copy")

    def snapshot(self):
        with self.lock:
            return json.loads(json.dumps(self.data))

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.data, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        temporary.replace(self.path)

    def change(self, payload):
        with self.lock:
            action = payload.get("action")
            if action == "save-route":
                points = route_points(payload.get("points"))
                item_id = payload.get("id") or uuid.uuid4().hex
                existing = next((r for r in self.data["routes"] if r["id"] == item_id), None)
                if not existing and len(self.data["routes"]) >= 100:
                    raise ValueError("路线库最多保存 100 条路线")
                record = {"id": item_id, "name": str(payload.get("name") or "我的路线")[:100],
                          "points": [{"lat": p.latitude, "lng": p.longitude} for p in points],
                          "created_at": existing["created_at"] if existing else timestamp(), "updated_at": timestamp()}
                self.data["routes"] = [r for r in self.data["routes"] if r["id"] != item_id] + [record]
            elif action == "delete-route":
                self.data["routes"] = [r for r in self.data["routes"] if r["id"] != payload.get("id")]
            elif action == "save-preset":
                settings = asdict(Settings.parse(payload.get("settings")))
                name = str(payload.get("name") or "常用配速")[:60]
                self.data["presets"] = [p for p in self.data["presets"] if p["name"] != name]
                self.data["presets"].append({"id": uuid.uuid4().hex, "name": name, "settings": settings})
                self.data["presets"] = self.data["presets"][-20:]
            elif action == "delete-preset":
                self.data["presets"] = [p for p in self.data["presets"] if p["id"] != payload.get("id")]
            elif action == "preferences":
                values = payload.get("values", {})
                if not isinstance(values, dict) or set(values) - {"view", "mode", "platform", "transport", "follow", "draft", "map_view", "device"}:
                    raise ValueError("Invalid preferences")
                if "draft" in values:
                    draft = values["draft"]
                    if not isinstance(draft, dict) or not isinstance(draft.get("points"), list) or len(draft["points"]) > 10000:
                        raise ValueError("Invalid draft")
                    for point in draft["points"]:
                        if not -85 <= float(point["lat"]) <= 85 or not -180 <= float(point["lng"]) <= 180:
                            raise ValueError("Invalid draft coordinate")
                self.data["preferences"].update(values)
            elif action == "clear-history":
                self.data["history"] = []
            else:
                raise ValueError("Unknown memory action")
            self._save()
            return self.snapshot()

    def append_history(self, record):
        with self.lock:
            self.data["history"] = [h for h in self.data["history"] if h["id"] != record["id"]]
            self.data["history"].insert(0, record)
            self.data["history"] = self.data["history"][:500]
            self.data["active_session"] = None
            self._save()

    def checkpoint(self, record):
        with self.lock:
            self.data["active_session"] = record
            self._save()

class DesktopController(PlaybackController):
    def __init__(self, folder, **kwargs):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        self.memory = Memory(folder / "memory.json")
        self.usb_rows = []
        self.usb_error = None
        self.usb_event = None
        self.cleanup_pending = False
        self._known_usb = set()
        self._active_usb = None
        self._readiness = {}
        self._run_record = None
        self._last_checkpoint = 0
        self._usb_probe = kwargs.pop("usb_probe", list_devices)
        self._readiness_probe = kwargs.pop("readiness_probe", self._inspect_phone)
        super().__init__(folder / "session.json", **kwargs)
        interrupted = self.memory.snapshot().get("active_session")
        self.cleanup_pending = bool(self.memory.snapshot().get("cleanup_pending"))
        if interrupted:
            self.cleanup_pending = True
            with self.memory.lock:
                self.memory.data["cleanup_pending"] = True
            self.memory.append_history(interrupted | {"ended_at": timestamp(), "outcome": "interrupted"})

    async def _inspect_phone(self, serial):
        client = await asyncio.wait_for(create_using_usbmux(serial, autopair=False), 3)
        try:
            result = {"name": str(client.all_values.get("DeviceName") or "iPhone")[:70],
                      "ios_version": client.product_version, "paired": bool(client.session_id)}
            if result["paired"]:
                result["developer_mode"] = await asyncio.wait_for(client.get_developer_mode_status(), 2)
            return result
        finally:
            await client.close()

    async def _usb_scan(self):
        try:
            found = await asyncio.wait_for(self._usb_probe(), 3)
        except Exception as exc:
            self.usb_error = "无法检测 Apple USB 通信，请检查 Apple Devices。" + str(exc)[:160]
            return  # A probe failure is not evidence of an unplug.
        rows = [{"udid": str(d.serial), "platform": "ios", "type": str(d.connection_type)} for d in found]
        present = {r["udid"] for r in rows if r["type"] == "USB"}
        removed = self._known_usb - present
        added = present - self._known_usb
        self.devices = rows
        self.usb_error = None
        self.discovery_error = None
        self._known_usb = present
        if removed:
            self.usb_event = {"kind": "removed", "at": timestamp()}
        if added:
            self.usb_event = {"kind": "inserted", "at": timestamp()}
        # Stop the owned device even while paused. Wireless devices are not treated as USB.
        if self._active_usb in removed:
            async with self.lock:
                self.state = "error"
                self.speed = 0
                self._finish_record("usb-disconnected")
                device, self.device = self.device, None
                self.udid = None
                self.current = None
                self.real_current = None
                self.motion = None
                self.cleanup_pending = True
                with self.memory.lock:
                    self.memory.data["cleanup_pending"] = True
                    self.memory._save()
                self.error = "USB 已断开，回放已停止。手机上的模拟位置尚未确认清除；重新连接后点击“清除遗留定位”。"
                if device:
                    try:
                        await asyncio.wait_for(device.close(), 5)
                    except Exception:
                        log.warning("USB disconnected during device cleanup", exc_info=True)
                self._active_usb = None
        details = []
        now = self.loop.time()
        for row in rows:
            if row["type"] == "USB":
                cache = self._readiness.get(row["udid"])
                if not cache or now - cache[0] >= 8 or row["udid"] in added:
                    try:
                        metadata = await self._readiness_probe(row["udid"])
                    except Exception as exc:
                        metadata = {"name": "iPhone", "paired": None, "error": "请解锁手机并检查“信任此电脑”提示。", "detail": type(exc).__name__}
                    self._readiness[row["udid"]] = (now, metadata)
                details.append(row | self._readiness[row["udid"]][1])
        self.usb_rows = details
        self._readiness = {key: value for key, value in self._readiness.items() if key in present}

    async def _discover(self):
        while True:
            await self._usb_scan()
            if self._run_record and self.state in ("completed", "error"):
                self._finish_record(self.state)
            elif self._run_record and self.loop.time() - self._last_checkpoint >= 5:
                self.memory.checkpoint(self._run_record | {"distance_m": self.motion.distance if self.motion else 0,
                                                         "elapsed_s": self.motion.elapsed if self.motion else 0})
                self._last_checkpoint = self.loop.time()
            await asyncio.sleep(1)

    def _finish_record(self, outcome):
        if not self._run_record:
            return
        record = self._run_record | {"ended_at": timestamp(), "outcome": outcome,
                                   "distance_m": self.motion.distance if self.motion else 0,
                                   "elapsed_s": self.motion.elapsed if self.motion else 0,
                                   "laps": self.motion.laps if self.motion else 0}
        self.memory.append_history(record)
        self._run_record = None

    def _status(self):
        result = super()._status()
        result["desktop"] = {"usb_devices": self.usb_rows, "usb_error": self.usb_error,
                             "usb_event": self.usb_event, "cleanup_pending": self.cleanup_pending}
        return result

    async def _action(self, action, data):
        if action == "connect" and data.get("platform", "ios") == "ios" and not data.get("rsd_host"):
            candidate = next((r for r in self.usb_rows if not data.get("udid") or r["udid"] == data["udid"]), None)
            if candidate and candidate.get("paired") is False:
                raise ValueError("手机尚未信任电脑，请解锁并确认“信任此电脑”。")
            if candidate and candidate.get("developer_mode") is False:
                raise ValueError("请在 iPhone 设置中开启开发者模式并完成重启确认。")
            if self.cleanup_pending:
                raise ValueError("请先点击“清除遗留定位”，再连接回放；避免重新发送路线起点。")
        ending = action in {"stop", "disconnect", "clear-route"}
        before = self._status() if ending and self._run_record else None
        result = await super()._action(action, data)
        if action == "connect" and self.device and not data.get("rsd_host"):
            serial = self.udid or next(iter(self._known_usb), None)
            self._active_usb = serial if serial in self._known_usb else None
        if action == "start" and not self._run_record:
            self._run_record = {"id": uuid.uuid4().hex, "started_at": timestamp(), "route_name": self.name,
                                "settings": asdict(self.settings), "platform": self.platform,
                                "record_type": "simulated-playback"}
            self.memory.checkpoint(self._run_record)
        if ending and self._run_record:
            record = self._run_record | {"ended_at": timestamp(), "outcome": action,
                      "distance_m": before["distance_m"], "elapsed_s": before["elapsed_s"], "laps": before["laps"]}
            self.memory.append_history(record)
            self._run_record = None
        if action == "disconnect":
            self._active_usb = None
        return result

    async def clear_leftover(self):
        async with self.lock:
            if self.device:
                raise ValueError("请先停止并断开当前定位连接")
            candidates = [r for r in self.usb_rows if r.get("paired") and r.get("developer_mode")]
            if len(candidates) != 1:
                raise ValueError("请连接并解锁一台已开启开发者模式的 iPhone")
            from ios_location_controller.device import LocationDevice
            device = LocationDevice(udid=candidates[0]["udid"])
            try:
                await asyncio.wait_for(device.connect(), 25)
                await asyncio.wait_for(device.clear(), 8)
                await asyncio.sleep(5)
            finally:
                await asyncio.wait_for(device.close(), 10)
            self.cleanup_pending = False
            with self.memory.lock:
                self.memory.data["cleanup_pending"] = False
                self.memory._save()
            self.error = None
            self.state = "idle"
            return self._status()

    def close(self):
        self._finish_record("window-closed")
        return super().close()
