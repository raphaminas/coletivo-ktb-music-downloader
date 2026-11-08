#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

echo "======================================================="
echo "   DJ Downloader - Gerador de Aplicativo para macOS"
echo "======================================================="
echo

# 1. Garante Frontend compilado
echo "[1/5] Compilando Frontend React..."
cd "$DIR/frontend"
if [ ! -d "node_modules" ]; then
    npm install --no-audit --no-fund
fi
npm run build
cd "$DIR"

# 2. Garante dependências Python
echo "[2/5] Verificando dependências Python..."
cd "$DIR/backend"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
.venv/bin/pip install -q pyinstaller pywebview pillow
cd "$DIR"

# 3. Garante binários estáticos do ffmpeg/ffprobe em macos/bin
echo "[3/5] Verificando binários estáticos do FFmpeg para macOS..."
mkdir -p "$DIR/macos/bin"
ARCH=$(uname -m)

if [ ! -f "$DIR/macos/bin/ffmpeg" ] || [ ! -f "$DIR/macos/bin/ffprobe" ]; then
    echo "    Baixando FFmpeg estático nativo para macOS ($ARCH)..."
    if [ "$ARCH" == "arm64" ]; then
        FFMPEG_URL="https://ffmpeg.martin-riedl.de/redirect/latest/macos/arm64/release/ffmpeg.zip"
        FFPROBE_URL="https://ffmpeg.martin-riedl.de/redirect/latest/macos/arm64/release/ffprobe.zip"
    else
        FFMPEG_URL="https://ffmpeg.martin-riedl.de/redirect/latest/macos/intel/release/ffmpeg.zip"
        FFPROBE_URL="https://ffmpeg.martin-riedl.de/redirect/latest/macos/intel/release/ffprobe.zip"
    fi

    curl -sL "$FFMPEG_URL" -o /tmp/ffmpeg_macos.zip
    unzip -q -o /tmp/ffmpeg_macos.zip -d "$DIR/macos/bin/"
    rm -f /tmp/ffmpeg_macos.zip

    curl -sL "$FFPROBE_URL" -o /tmp/ffprobe_macos.zip
    unzip -q -o /tmp/ffprobe_macos.zip -d "$DIR/macos/bin/"
    rm -f /tmp/ffprobe_macos.zip

    chmod +x "$DIR/macos/bin/ffmpeg" "$DIR/macos/bin/ffprobe"
    xattr -dr com.apple.quarantine "$DIR/macos/bin" 2>/dev/null || true
    echo "    FFmpeg estático configurado com sucesso!"
else
    echo "    FFmpeg já presente em macos/bin."
fi

# 4. Empacota com PyInstaller
echo "[4/5] Gerando DJ Downloader.app com PyInstaller..."
rm -rf "$DIR/dist/DJ Downloader.app" "$DIR/dist/DJ Downloader"
"$DIR/backend/.venv/bin/pyinstaller" --clean -y "$DIR/macos/dj-downloader.spec"

# Assinatura ad-hoc local para macOS Gatekeeper
echo "    Aplicando assinatura local ad-hoc..."
codesign --force --deep --sign - "$DIR/dist/DJ Downloader.app" 2>/dev/null || true

# 5. Cria Imagem de Disco DMG
echo "[5/5] Gerando instalador DMG..."
mkdir -p "$DIR/dist-installer"
DMG_PATH="$DIR/dist-installer/DJ-Downloader-macOS.dmg"
rm -f "$DMG_PATH"

STAGING_DIR="/tmp/dj_dmg_staging"
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR"

cp -R "$DIR/dist/DJ Downloader.app" "$STAGING_DIR/"
ln -s /Applications "$STAGING_DIR/Applications"

hdiutil create -volname "DJ Downloader" -srcfolder "$STAGING_DIR" -ov -format UDZO "$DMG_PATH"
rm -rf "$STAGING_DIR"

echo
echo "======================================================="
echo "   🎉 SUCESSO! Aplicativo e Instalador macOS criados:"
echo "   1. App:        dist/DJ Downloader.app"
echo "   2. Instalador: dist-installer/DJ-Downloader-macOS.dmg"
echo "======================================================="
echo
