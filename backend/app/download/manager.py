"""Fila de downloads: yt-dlp + ffmpeg, tags e verificação do bitrate real."""
from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Awaitable, Callable

import yt_dlp

from .. import db
from ..tagging import write_tags

CHROME_DIR = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
# itag 141 = AAC 256kbps (Premium); 140 = AAC 128; depois o melhor áudio disponível.
FORMAT_SELECTOR = "141/bestaudio[acodec^=mp4a]/bestaudio/best"
EXT = {"mp3": "mp3", "wav": "wav", "m4a": "m4a"}


# ---------- Chrome / cookies ----------

def chrome_profiles() -> list[dict]:
    """Perfis do Chrome: [{dir, name, email}]. Vazio se não der para ler."""
    try:
        state = json.loads((CHROME_DIR / "Local State").read_text())
        cache = state["profile"]["info_cache"]
    except Exception:
        return []
    return [
        {"dir": d, "name": v.get("name") or d, "email": v.get("user_name") or ""}
        for d, v in cache.items()
    ]


def resolve_profile(wanted: str) -> str | None:
    """Aceita nome exibido ('raphael'), e-mail ou pasta ('Profile 1')."""
    if not wanted:
        return None
    w = wanted.strip().lower()
    for p in chrome_profiles():
        if w in (p["dir"].lower(), p["name"].lower(), p["email"].lower()):
            return p["dir"]
    for p in chrome_profiles():
        if w in p["name"].lower() or (p["email"] and w in p["email"].lower()):
            return p["dir"]
    return wanted  # deixa o yt-dlp tentar como pasta


def cookies_option(settings: dict) -> tuple | None:
    browser = (settings.get("cookies_browser") or "").strip()
    if not browser:
        return None
    profile = resolve_profile(settings.get("cookies_profile") or "") if browser == "chrome" else (
        settings.get("cookies_profile") or None)
    return (browser, profile, None, None)


# ---------- utilidades ----------

def sanitize(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", name or "").strip().strip(".")
    return re.sub(r"\s+", " ", name)[:150] or "sem nome"


def ffprobe_bitrate(path: Path) -> float | None:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
             "stream=bit_rate:format=bit_rate", "-of", "json", str(path)],
            capture_output=True, text=True, timeout=30,
        ).stdout
        d = json.loads(out)
        br = (d.get("streams") or [{}])[0].get("bit_rate") or d.get("format", {}).get("bit_rate")
        return round(int(br) / 1000) if br else None
    except Exception:
        return None


def track_meta(track: dict) -> dict:
    """Metadados finais: origem (Spotify) tem prioridade, depois o vídeo escolhido."""
    src = track.get("source") or {}
    sel = track.get("selected") or {}
    artists = src.get("artists") or sel.get("artists") or ["Desconhecido"]
    title = src.get("title") or sel.get("title") or "Sem título"
    alt_label = sel.get("alt_label") if sel.get("alt_kind") == "extended" else None
    version = alt_label or (sel.get("version") if sel.get("alt_kind") else None)
    if version and version.lower() not in title.lower():
        title = f"{title} ({version})"
    return {
        "title": title,
        "artist": ", ".join(artists),
        "album_artist": artists[0],
        "album": src.get("album") or sel.get("album"),
        "year": src.get("year"),
        "cover_url": src.get("cover") or sel.get("thumbnail"),
        "comment": f"https://music.youtube.com/watch?v={sel.get('video_id')}",
    }


def output_path(track: dict, project: dict, settings: dict) -> Path:
    meta = track_meta(track)
    pattern = settings.get("filename_pattern") or "{artist} - {title}"
    try:
        stem = pattern.format(artist=meta["artist"], title=meta["title"],
                              album=meta.get("album") or "", n=track.get("position", ""))
    except Exception:
        stem = f"{meta['artist']} - {meta['title']}"
    folder = Path(settings["output_dir"]).expanduser() / sanitize(project["name"])
    return folder / f"{sanitize(stem)}.{EXT[settings['format']]}"


# ---------- download ----------

class Cancelled(Exception):
    pass


def _ydl_opts(fmt: str, tmp_dir: Path, cookies: tuple | None, hook, pp_hook) -> dict:
    opts: dict[str, Any] = {
        "format": FORMAT_SELECTOR,
        "outtmpl": str(tmp_dir / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": True,
        "progress_hooks": [hook],
        "postprocessor_hooks": [pp_hook],
        "overwrites": True,
        "retries": 5,
        "fragment_retries": 5,
    }
    if cookies:
        opts["cookiesfrombrowser"] = cookies
    if fmt == "mp3":
        opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3",
                                   "preferredquality": "320"}]
        opts["postprocessor_args"] = {"extractaudio": ["-ar", "44100"]}
    elif fmt == "wav":
        opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}]
        opts["postprocessor_args"] = {"extractaudio": ["-ar", "44100", "-sample_fmt", "s16"]}
    else:  # m4a: copia o AAC original sem recompressão quando possível
        opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}]
    return opts


def download_sync(video_id: str, fmt: str, settings: dict,
                  on_progress: Callable[[dict], None]) -> dict:
    """Baixa um vídeo e devolve {path, source_abr, source_format, used_cookies, warning}."""
    tmp_dir = db.DATA_DIR / "tmp" / video_id
    tmp_dir.mkdir(parents=True, exist_ok=True)
    url = f"https://music.youtube.com/watch?v={video_id}"
    last = {"t": 0.0}

    def hook(d: dict) -> None:
        if d.get("status") == "downloading":
            now = time.time()
            if now - last["t"] < 0.25:
                return
            last["t"] = now
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            pct = (d.get("downloaded_bytes", 0) / total * 100) if total else 0
            on_progress({"status": "downloading", "progress": round(pct, 1),
                         "speed": d.get("speed"), "eta": d.get("eta")})
        elif d.get("status") == "finished":
            on_progress({"status": "processing", "progress": 100})

    def pp_hook(d: dict) -> None:
        if d.get("status") == "started":
            on_progress({"status": "processing", "progress": 100})

    cookies = cookies_option(settings)
    warning = None
    attempts = [cookies, None] if cookies else [None]
    info = None
    err: Exception | None = None
    used_cookies = False
    for c in attempts:
        try:
            with yt_dlp.YoutubeDL(_ydl_opts(fmt, tmp_dir, c, hook, pp_hook)) as ydl:
                info = ydl.extract_info(url, download=True)
            used_cookies = c is not None
            break
        except Exception as e:  # noqa: BLE001
            err = e
            if c is not None:
                warning = f"Falha com cookies do navegador ({str(e)[:160]}). Baixado sem Premium."
    if info is None:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RuntimeError(_friendly_error(err))

    rd = (info.get("requested_downloads") or [{}])[0]
    produced = Path(rd.get("filepath") or "")
    if not produced.exists():
        files = [p for p in tmp_dir.iterdir() if p.suffix.lstrip(".") == EXT[fmt]]
        if not files:
            raise RuntimeError("Arquivo final não encontrado após a conversão.")
        produced = files[0]
    abr = info.get("abr") or rd.get("abr")
    return {
        "tmp_path": produced,
        "tmp_dir": tmp_dir,
        "source_abr": round(abr) if abr else None,
        "source_format": f"{info.get('format_id')} · {info.get('acodec') or ''}".strip(" ·"),
        "used_cookies": used_cookies,
        "warning": warning,
    }


def _friendly_error(e: Exception | None) -> str:
    msg = str(e or "erro desconhecido")
    msg = re.sub(r"\x1b\[[0-9;]*m", "", msg).replace("ERROR: ", "")
    if "Sign in to confirm" in msg:
        return "O YouTube pediu login (anti-bot). Confira se o Chrome está logado e tente de novo."
    if "Video unavailable" in msg:
        return "Vídeo indisponível. Escolha outro candidato."
    return msg[:300]


# ---------- fila ----------

Broadcast = Callable[[dict], Awaitable[None]]


class DownloadManager:
    def __init__(self, broadcast: Broadcast):
        self.broadcast = broadcast
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.workers: list[asyncio.Task] = []
        self.loop: asyncio.AbstractEventLoop | None = None
        self.queued: set[str] = set()

    def start(self) -> None:
        self.loop = asyncio.get_running_loop()
        n = max(1, int(db.get_settings().get("concurrency") or 2))
        self.workers = [asyncio.create_task(self._worker()) for _ in range(n)]

    async def stop(self) -> None:
        for w in self.workers:
            w.cancel()

    async def enqueue(self, track_ids: list[str]) -> int:
        n = 0
        for tid in track_ids:
            t = db.get_track(tid)
            if not t or not t.get("selected") or tid in self.queued:
                continue
            t["download"] = {"status": "queued", "progress": 0}
            db.save_track(t)
            self.queued.add(tid)
            await self.queue.put(tid)
            await self._emit(t)
            n += 1
        return n

    async def _emit(self, track: dict) -> None:
        await self.broadcast({"type": "track", "track": track})

    def _emit_threadsafe(self, track: dict) -> None:
        if self.loop:
            asyncio.run_coroutine_threadsafe(self._emit(track), self.loop)

    async def _worker(self) -> None:
        while True:
            tid = await self.queue.get()
            try:
                await self._process(tid)
            except Exception as e:  # noqa: BLE001
                t = db.get_track(tid)
                if t:
                    t["download"] = {"status": "error", "progress": 0, "error": str(e)[:300]}
                    db.save_track(t)
                    await self._emit(t)
            finally:
                self.queued.discard(tid)
                self.queue.task_done()

    async def _process(self, tid: str) -> None:
        track = db.get_track(tid)
        if not track:
            return
        project = db.get_project_meta(track["project_id"])
        settings = db.get_settings()
        fmt = settings["format"]
        sel = track["selected"]
        vid = sel["video_id"]
        dest = output_path(track, project, settings)
        min_br = int(settings.get("min_bitrate") or 192)

        def update(patch: dict) -> None:
            track["download"] = {**track.get("download", {}), **patch}
            db.save_track(track)
            self._emit_threadsafe(dict(track))

        cached = db.cached_download(vid, fmt)
        if cached:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if Path(cached["path"]) != dest:
                await asyncio.to_thread(shutil.copy2, cached["path"], dest)
            await asyncio.to_thread(write_tags, dest, track_meta(track))
            abr = cached["source_abr"]
            track["download"] = {
                "status": "done", "progress": 100, "path": str(dest), "format": fmt,
                "source_abr": abr, "file_bitrate": await asyncio.to_thread(ffprobe_bitrate, dest),
                "quality_ok": bool(abr and abr >= min_br), "from_cache": True,
            }
            db.save_track(track)
            await self._emit(track)
            return

        update({"status": "downloading", "progress": 0, "error": None})
        res = await asyncio.to_thread(download_sync, vid, fmt, settings, update)
        update({"status": "processing", "progress": 100})
        dest.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(shutil.move, str(res["tmp_path"]), dest)
        shutil.rmtree(res["tmp_dir"], ignore_errors=True)
        await asyncio.to_thread(write_tags, dest, track_meta(track))
        file_br = await asyncio.to_thread(ffprobe_bitrate, dest)
        abr = res["source_abr"]
        db.remember_download(vid, fmt, str(dest), abr)
        track["download"] = {
            "status": "done", "progress": 100, "path": str(dest), "format": fmt,
            "source_abr": abr, "source_format": res["source_format"], "file_bitrate": file_br,
            "quality_ok": bool(abr and abr >= min_br), "used_cookies": res["used_cookies"],
            "warning": res["warning"],
        }
        db.save_track(track)
        await self._emit(track)
