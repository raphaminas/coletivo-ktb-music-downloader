# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import os
import sys

block_cipher = None

root_dir = Path(os.path.abspath(SPECPATH)).parent
backend_dir = root_dir / "backend"
frontend_dist = root_dir / "frontend" / "dist"
assets_dir = root_dir / "assets"
bin_dir = root_dir / "windows" / "bin"

datas = []

# Inclui build do frontend estático
if frontend_dist.is_dir():
    datas.append((str(frontend_dist), "frontend/dist"))

# Inclui ícones
if assets_dir.is_dir():
    datas.append((str(assets_dir), "assets"))

# Inclui binários do ffmpeg/ffprobe se presentes na pasta windows/bin
if bin_dir.is_dir():
    datas.append((str(bin_dir), "bin"))

hidden_imports = [
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "fastapi",
    "starlette",
    "yt_dlp",
    "ytmusicapi",
    "mutagen",
    "mutagen.mp3",
    "mutagen.id3",
    "mutagen.mp4",
    "mutagen.wave",
    "rapidfuzz",
    "sqlite3",
    "webview",
    "webview.platforms.winforms",
    "webview.platforms.edgechromium",
    "clr",
]

a = Analysis(
    [str(backend_dir / "desktop.py")],
    pathex=[str(backend_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "pandas"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DJ Downloader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(assets_dir / "icon.ico") if (assets_dir / "icon.ico").is_file() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DJ Downloader",
)
