"""Package the built application and a source-only archive for GitHub Releases."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

root = Path(__file__).resolve().parent
repo = root.parent
outputs = repo / "outputs"
package = repo / "dist/RouteStudio"
if not (package / "RouteStudio.exe").is_file():
    raise SystemExit("Build dist/RouteStudio/RouteStudio.exe with PyInstaller first.")
outputs.mkdir(parents=True, exist_ok=True)
shutil.copy2(root / "README.md", package / "使用说明.md")
with zipfile.ZipFile(outputs / "RouteStudio-Windows.zip", "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for file in sorted(package.rglob("*")):
        if file.is_file():
            archive.write(file, file.relative_to(package.parent))

excluded_names = {"memory.json", "session.json", "window.json"}
def include_source(file):
    relative = file.relative_to(repo)
    return (file.is_file()
            and not any(part in {"__pycache__", ".pytest_cache", ".venv", "WebView2"}
                        or part.endswith(".egg-info") for part in relative.parts)
            and file.suffix not in {".pyc", ".pyo", ".log"}
            and file.name not in excluded_names
            and not file.name.startswith("memory-recovery-"))

with zipfile.ZipFile(outputs / "RouteStudio-Source.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for directory in ("route-studio-desktop", "src", "tests", "routes"):
        for file in sorted((repo / directory).rglob("*")):
            if include_source(file):
                archive.write(file, file.relative_to(repo))
    for name in ("pyproject.toml", ".gitignore", "README.md", "README.en.md", "README.upstream.md",
                 "play-route.ps1", "start-map.cmd", "start-map.ps1", "start-map.sh",
                 "start-server.cmd", "stop-server.sh"):
        file = repo / name
        if file.is_file():
            archive.write(file, name)

manifest = {"version": "1.0.0", "files": []}
for file in (package / "RouteStudio.exe", outputs / "RouteStudio-Windows.zip", outputs / "RouteStudio-Source.zip"):
    with file.open("rb") as source:
        manifest["files"].append({"file": file.relative_to(repo).as_posix(), "bytes": file.stat().st_size,
                                  "sha256": hashlib.file_digest(source, "sha256").hexdigest()})
(outputs / "desktop-release-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(json.dumps(manifest, indent=2))
