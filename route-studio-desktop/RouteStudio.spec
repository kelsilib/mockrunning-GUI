from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files
from pathlib import Path

root = Path(SPECPATH)
datas = [(str(root / 'assets'), 'assets')]
binaries = []
hiddenimports = []
for package in ('webview', 'pymobiledevice3', 'pmd_pytcp', 'pmd_net_proto', 'pmd_net_addr', 'developer_disk_image', 'pythonnet', 'clr_loader', 'pytun_pmd3', 'sslpsk_pmd3'):
    package_data, package_bins, package_imports = collect_all(package)
    datas += package_data
    binaries += package_bins
    hiddenimports += package_imports
hiddenimports += collect_submodules('ios_location_controller')
hiddenimports += ['pymobiledevice3.__main__', 'clr', 'webview.platforms.winforms', 'webview.platforms.edgechromium']
datas += collect_data_files('certifi')

a = Analysis([str(root / 'desktop_app.py')], pathex=[str(root), str(root.parent / 'src')],
             binaries=binaries, datas=datas, hiddenimports=hiddenimports,
             hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=['pytest', 'playwright', 'tkinter', 'PyQt5', 'PyQt6', 'PySide6', 'matplotlib'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='RouteStudio', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False, console=False,
          icon=str(root / 'assets/route-studio.ico'), version=str(root / 'version_info.txt'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='RouteStudio')
