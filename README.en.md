<div align="center">

# Route Studio

**Keep your routes close at hand.**

A Windows desktop workspace for route editing and location testing

[简体中文](README.md) · **English**

[Quick start](#quick-start) · [Development and packaging](#development-and-packaging) · [USB and recovery](#usb-and-recovery) · [Upstream project](https://github.com/yinsuecci/mockrunning)

</div>

---

Route Studio adds a standalone Windows desktop window to [mockrunning](https://github.com/yinsuecci/mockrunning). It embeds the route map and controls, with a route library, local persistence, and iPhone USB status detection. The interface uses warm neutral colors, terracotta accents, and restrained typography.

The desktop version uses the upstream location adapters. This repository is a fork: the core remains in `src/`, and desktop additions live in `route-studio-desktop/`.

## Features

| Feature | Description |
| --- | --- |
| Route editing | Add, drag, and remove map nodes; import and export GPX; nodes connect with straight segments |
| Route library | Save, name, search, and reopen multiple routes |
| Playback controls | Start, pause, stop, and clear simulation; save reusable pace and parameter presets |
| Local memory | Restore drafts, map position, the last page, window size, and playback history |
| USB detection | Show iPhone connection, trust, and Developer Mode status; distinguish USB presence from a location-service connection |
| Interruption handling | Stop playback on unplug, retain routes, record interruptions, and prompt for leftover-location cleanup |

History describes this software's simulated playback, rather than real exercise or third-party platform records. The software does not automatically connect, start playback, or submit third-party records.

## Quick start

### Windows package

If a Windows package is available in [Releases](https://github.com/kelsilib/mockrunning-GUI/releases), download and extract it, then run `RouteStudio/RouteStudio.exe`. Keep the adjacent `_internal/` directory; copying only the EXE is insufficient.

The packaged version does not require a separate Python installation. It still requires:

- Windows 11; other Windows versions have not been verified.
- A working Microsoft Edge WebView2 Runtime.
- Device communication support from Apple Devices / Apple Mobile Device Support.
- An unlocked iPhone that trusts the computer, with Developer Mode enabled and its reboot confirmation completed.
- Working developer services and an appropriate DDI for the iOS version. USB discovery alone does not establish location-service readiness.

This documentation does not indicate that a downloadable Release already exists. Source installation is described below.

### First playback

1. Connect and unlock the iPhone over USB. Check the connection card at the lower left.
2. Edit or import a GPX route in “布设路线” (route editor), then save it to the library.
3. Load the route in “手机回放” (device playback), then click “连接手机” (connect). **Connecting with a loaded route sends its starting point; loading a route while connected also sends the starting point.**
4. Set and save the parameters, then start playback. Pause before changing parameters.
5. Click “停止并清除模拟” (stop and clear), wait a few seconds, and verify the real location in an ordinary map app before disconnecting.

Map tiles and place search require internet access. Coordinates and existing routes remain usable without map tiles. Routes are not automatically snapped to roads.

The desktop UI currently uses Chinese labels; this language switch applies to documentation.

## USB and recovery

USB status is polled approximately once per second. Reading pairing and Developer Mode can take a few additional seconds.

| Status | Meaning and action |
| --- | --- |
| USB connected | Apple usbmux found the device; the location service may still be disconnected |
| Waiting for trust / unlock | Unlock the iPhone and confirm “Trust This Computer” |
| Developer Mode disabled | Enable it on the iPhone, reboot, and confirm again |
| Detection error | Check the cable and Apple device communication; a failed probe is not treated as an unplug |
| USB disconnected | Stop playback, including paused sessions; cleanup on the disconnected phone cannot be confirmed |
| Leftover-location warning | Reconnect and unlock the phone, click “清除遗留定位” (clear leftover location), and check its map |

Reinserting USB does not automatically resume playback. Closing the software attempts to stop and clear simulation, but unplugging, force termination, or device errors can prevent cleanup. A successful clear request does not mean the map immediately returns to the real location; check the phone itself.

**Manual iPhone steps:** unlocking, trusting the computer, enabling Developer Mode and confirming after reboot, and checking location recovery. The desktop software does not automatically install drivers or change system settings.

## Local data

Desktop data lives in `%LOCALAPPDATA%\RouteStudio`, separate from the source and executable directories.

| File | Contents |
| --- | --- |
| `memory.json` | Routes, presets, preferences, and playback history |
| `session.json` | The last loaded route and parameters |
| `window.json` | Window settings |
| `desktop.log` | Local diagnostic logs |
| `WebView2/` | Embedded browser data |

Close the software before copying this directory for backup. Do not commit personal routes, device information, or logs to a public repository. Map tiles and place search contact their respective online services.

## Development and packaging

The desktop version was developed with Python 3.12.14. Python 3.12 is recommended; create a virtual environment at the repository root.

```powershell
git clone https://github.com/kelsilib/mockrunning-GUI.git
cd mockrunning-GUI
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]" -r route-studio-desktop/requirements-desktop.txt
.\.venv\Scripts\python.exe route-studio-desktop/desktop_app.py
```

If the desktop addition has not reached the default branch, switch to the appropriate branch before installation, for example `git switch route-studio-desktop`. These commands require Git and Python to be available in the terminal.

Run upstream and desktop tests:

```powershell
$env:PYTHONPATH = "$PWD\route-studio-desktop"
.\.venv\Scripts\python.exe -m pytest tests route-studio-desktop/tests -q
```

Build the Windows directory-based package:

```powershell
cd route-studio-desktop
..\.venv\Scripts\python.exe -m PyInstaller --noconfirm --distpath ..\dist --workpath ..\build RouteStudio.spec
..\.venv\Scripts\python.exe package_release.py
```

The application is written to `dist/RouteStudio/`; release ZIPs and the checksum manifest go to `outputs/`. See [BUILD.md](route-studio-desktop/BUILD.md) for build details and browser tests. Upstream web, CLI, and Android usage is preserved in the [original documentation](README.upstream.md), in Chinese.

## Verification and limitations

These results describe earlier development checks. They do not imply that every source revision has repeated the full test suite.

- Previously, 101 upstream automated tests and 5 desktop tests passed. Desktop tests cover persistence, corrupt-data backup, USB interruption, and restart recovery.
- The desktop route library, preset persistence, compact layout, and packaged WebView2 startup and exit were verified.
- A user-assisted test verified physical iPhone USB insertion, removal, and reinsertion. Desktop tests did not send simulated locations to the phone.
- Earlier testing with the upstream location program verified simulated placement and real-location recovery in an ordinary map app.
- **Location injection from the desktop build, WeChat Mini Program compatibility, and physical-device Android / wireless compatibility have not been verified.**

“Sent location” is the most recently transmitted coordinate, rather than GPS readback from the phone. The current iOS adapter sends latitude and longitude only; it does not simulate steps, motion sensors, GNSS raw measurements, or configurable location accuracy. Applications may reject simulated locations or use other location sources.

This project is for location and application testing on authorized devices. It provides no campus-running anti-cheat bypass or third-party score submission features.

## Repository layout

```text
mockrunning-GUI/
├── src/                     # Upstream location core and web UI
├── tests/                   # Upstream tests
├── routes/                  # Sample routes
├── route-studio-desktop/     # Desktop host, USB supervision, persistence, UI
├── README.md                # Simplified Chinese
├── README.en.md             # English
└── README.upstream.md       # Preserved upstream documentation
```

## Acknowledgments

Built on [yinsuecci/mockrunning](https://github.com/yinsuecci/mockrunning), with [pymobiledevice3](https://github.com/doronz88/pymobiledevice3), [pywebview](https://pywebview.flowrl.com/), [Leaflet](https://leafletjs.com/), and OpenStreetMap. Thanks to the upstream authors and dependency maintainers.
