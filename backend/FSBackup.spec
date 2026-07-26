from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("uvicorn")

a = Analysis(
    ["app/launcher.py"],
    pathex=["."],
    binaries=[],
    datas=[("app/web_ui", "app/web_ui")],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "ruff", "black"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FSBackup",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="FSBackup",
)
