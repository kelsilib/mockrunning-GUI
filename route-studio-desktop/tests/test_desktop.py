import asyncio
import json
from types import SimpleNamespace
import pytest
from desktop_backend import DesktopController, Memory

POINTS = [{"lat": 31.2304, "lng": 121.4737}, {"lat": 31.2308, "lng": 121.4742}]

def test_memory_survives_restart_and_overwrites_by_id(tmp_path):
    path = tmp_path / "memory.json"
    memory = Memory(path)
    saved = memory.change({"action": "save-route", "name": "常用路线", "points": POINTS})
    ident = saved["routes"][0]["id"]
    memory.change({"action": "save-route", "id": ident, "name": "重命名", "points": POINTS})
    memory.change({"action": "save-preset", "name": "7 分钟", "settings": {"speed_kmh": 60 / 7, "speed_variation_pct": 0}})
    memory.change({"action": "preferences", "values": {"mode": "player", "draft": {"name": "草稿", "points": POINTS}}})
    recovered = Memory(path).snapshot()
    assert len(recovered["routes"]) == 1
    assert recovered["routes"][0]["name"] == "重命名"
    assert recovered["presets"][0]["settings"]["speed_kmh"] == 60 / 7
    assert recovered["preferences"]["draft"]["points"] == POINTS
    with pytest.raises(ValueError):
        memory.change({"action": "save-route", "points": [{"lat": 100, "lng": 0}] * 2})

def test_corrupt_memory_is_preserved(tmp_path):
    path = tmp_path / "memory.json"
    path.write_text("broken", encoding="utf-8")
    assert Memory(path).snapshot()["routes"] == []
    assert list(tmp_path.glob("memory-recovery-*.json"))[0].read_text() == "broken"

class QuietController(DesktopController):
    async def _discover(self):
        while True:
            await asyncio.sleep(60)

class FakeDevice:
    def __init__(self, **kwargs):
        self.udid = kwargs.get("udid")
        self.closed = False
    async def connect(self): pass
    async def set_point(self, point): pass
    async def clear(self): pass
    async def close(self): self.closed = True

def test_usb_insert_unplug_paused_and_reinsert(tmp_path):
    present = [SimpleNamespace(serial="phone-1", connection_type="USB")]
    inspected = []
    async def probe(): return list(present)
    async def readiness(serial):
        inspected.append(serial)
        return {"name": "测试手机", "paired": True, "developer_mode": True}
    c = QuietController(tmp_path, device_factory=FakeDevice, usb_probe=probe, readiness_probe=readiness)
    def scan():
        return asyncio.run_coroutine_threadsafe(c._usb_scan(), c.loop).result(timeout=8)
    try:
        scan()
        assert c.status()["desktop"]["usb_devices"][0]["name"] == "测试手机"
        c.call("route", {"name": "USB test", "points": POINTS})
        c.call("connect", {"platform": "ios", "udid": "phone-1"})
        c.call("start")
        c.call("pause")
        connected = c.device
        present.clear()
        scan()
        state = c.status()
        assert not state["connected"] and state["state"] == "error"
        assert state["desktop"]["cleanup_pending"] and state["current"] is None
        assert state["route"]["points"] == POINTS and connected.closed
        assert c.memory.snapshot()["history"][0]["outcome"] == "usb-disconnected"
        present.append(SimpleNamespace(serial="phone-1", connection_type="USB"))
        scan()
        assert len(inspected) == 2
        assert not c.status()["connected"]
        with pytest.raises(ValueError, match="遗留定位"):
            c.call("connect", {"platform": "ios", "udid": "phone-1"})
    finally:
        c.close()

def test_probe_failure_does_not_fake_unplug(tmp_path):
    fail = False
    async def probe():
        if fail: raise OSError("usbmux temporary failure")
        return [SimpleNamespace(serial="phone-1", connection_type="USB")]
    async def ready(serial): return {"name": "Phone", "paired": True, "developer_mode": True}
    c = QuietController(tmp_path, device_factory=FakeDevice, usb_probe=probe, readiness_probe=ready)
    try:
        asyncio.run_coroutine_threadsafe(c._usb_scan(), c.loop).result()
        c.call("connect", {"udid": "phone-1"})
        fail = True
        asyncio.run_coroutine_threadsafe(c._usb_scan(), c.loop).result()
        assert c.status()["connected"]
        assert c.status()["desktop"]["usb_error"]
    finally:
        c.close()

def test_interrupted_session_survives_restart_without_playback(tmp_path):
    memory = Memory(tmp_path / "memory.json")
    memory.checkpoint({"id": "interrupted-run", "started_at": "2026-10-12T00:00:00+00:00", "route_name": "Last route", "settings": {"speed_kmh": 5}})
    async def no_usb(): return []
    c = QuietController(tmp_path, usb_probe=no_usb)
    try:
        assert c.status()["desktop"]["cleanup_pending"]
        assert c.status()["state"] == "idle" and not c.status()["connected"]
        assert c.memory.snapshot()["history"][0]["outcome"] == "interrupted"
    finally:
        c.close()
