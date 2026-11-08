"""Desktop App Entrypoint para DJ Downloader.

Executa o backend FastAPI em segundo plano e abre uma janela nativa moderna
do Windows 11 (via Edge WebView2 / pywebview) ou o navegador padrão.
"""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

# Garante que binários embutidos (ffmpeg, ffprobe) estejam no PATH
def ensure_binaries_in_path() -> None:
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            meipass = Path(sys._MEIPASS)
            candidates.extend([meipass, meipass / "bin"])
        exe_dir = Path(sys.executable).parent
        candidates.extend([exe_dir, exe_dir / "bin"])
    else:
        root = Path(__file__).resolve().parent.parent
        candidates.extend([root / "bin", root / "windows" / "bin"])

    for c in candidates:
        if c.is_dir() and str(c) not in os.environ.get("PATH", ""):
            os.environ["PATH"] = f"{str(c)}{os.pathsep}{os.environ.get('PATH', '')}"

ensure_binaries_in_path()

import uvicorn
from app.main import app


def find_free_port(preferred: int = 8000) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            pass

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_server(url: str, timeout: float = 12.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(f"{url}/api/health", timeout=0.8) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.15)
    return False


def get_icon_path() -> str | None:
    candidates = []
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidates.extend([
            meipass / "assets" / "icon.ico",
            meipass / "assets" / "icon.png",
            meipass / "icon.ico",
        ])
    else:
        root = Path(__file__).resolve().parent.parent
        candidates.extend([
            root / "assets" / "icon.ico",
            root / "assets" / "icon.png",
        ])

    for c in candidates:
        if c.is_file():
            return str(c)
    return None


def main() -> None:
    use_browser = "--browser" in sys.argv
    port = find_free_port(8000)
    server_url = f"http://127.0.0.1:{port}"

    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)

    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    ready = wait_for_server(server_url)
    if not ready:
        print("Erro: O servidor backend não respondeu a tempo.")

    has_webview = False
    if not use_browser:
        try:
            import webview  # type: ignore
            has_webview = True
        except Exception:
            has_webview = False

    if has_webview:
        try:
            import webview  # type: ignore

            icon = get_icon_path()
            window = webview.create_window(
                title="DJ Downloader",
                url=server_url,
                width=1280,
                height=840,
                min_size=(960, 600),
                background_color="#07080b",
                text_select=True,
            )

            # Inicia loop de janela nativo do WebView2
            webview.start(icon=icon)
            server.should_exit = True
            return
        except Exception as e:
            print(f"Aviso: Não foi possível abrir janela nativa ({e}). Abrindo no navegador...")

    # Fallback: navegador padrão
    webbrowser.open(server_url)
    print(f"DJ Downloader em execução em {server_url}")
    print("Pressione Ctrl+C para encerrar.")
    try:
        while server_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        server.should_exit = True


if __name__ == "__main__":
    main()
