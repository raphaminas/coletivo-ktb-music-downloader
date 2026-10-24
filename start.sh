#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "🎧 DJ Downloader iniciando..."

# 1. Checa ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  ffmpeg não encontrado no PATH. Instalando via Homebrew..."
    if command -v brew &> /dev/null; then
        brew install ffmpeg
    else
        echo "❌ Homebrew não encontrado. Por favor instale o ffmpeg manualmente."
        exit 1
    fi
fi

# 2. Configura Backend Python
cd "$DIR/backend"
if [ ! -d ".venv" ]; then
    echo "📦 Criando ambiente virtual Python..."
    PYTHON_BIN="/opt/homebrew/bin/python3.12"
    if [ ! -f "$PYTHON_BIN" ]; then
        PYTHON_BIN="$(which python3)"
    fi
    "$PYTHON_BIN" -m venv .venv
    .venv/bin/pip install -q -U pip
    .venv/bin/pip install -q -r requirements.txt
fi

# 3. Garante build do Frontend
cd "$DIR/frontend"
if [ ! -d "node_modules" ]; then
    echo "📦 Instalando dependências do frontend..."
    npm install --no-audit --no-fund
fi

if [ ! -d "dist" ] || [ "$1" == "--build" ]; then
    echo "⚡ Compilando frontend..."
    npm run build
fi

cd "$DIR/backend"

# 4. Modo dev ou produção
if [ "$1" == "--dev" ]; then
    echo "🛠️  Iniciando em modo de desenvolvimento (FastAPI :8000 + Vite :5173)..."
    .venv/bin/uvicorn app.main:app --reload --port 8000 &
    BACKEND_PID=$!
    cd "$DIR/frontend"
    npm run dev &
    FRONT_PID=$!

    trap "kill $BACKEND_PID $FRONT_PID" EXIT
    sleep 2
    open "http://localhost:5173"
    wait
else
    echo "🚀 Servidor rodando em http://localhost:8000"
    (sleep 1.5 && open "http://localhost:8000") &
    exec .venv/bin/uvicorn app.main:app --port 8000
fi
