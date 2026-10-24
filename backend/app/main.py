"""DJ Downloader: API FastAPI + WebSocket de progresso."""
from __future__ import annotations

import asyncio
import io
import re
import shutil
import subprocess
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
import yt_dlp
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from . import db
from .download.manager import DownloadManager, chrome_profiles, resolve_profile, sanitize
from .matching import engine
from .sources import spotify

SINGLES_ID = "singles"
YT_ID_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|embed/|live/)|youtu\.be/|music\.youtube\.com/watch\?(?:.*&)?v=)"
    r"([A-Za-z0-9_-]{11})"
)


# ---------- WebSocket hub ----------

class Hub:
    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()

    async def broadcast(self, msg: dict) -> None:
        dead = []
        for ws in list(self.clients):
            try:
                await ws.send_json(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)


hub = Hub()
manager = DownloadManager(hub.broadcast)
match_sem = asyncio.Semaphore(4)
_bg: set[asyncio.Task] = set()


def spawn(coro) -> None:
    t = asyncio.create_task(coro)
    _bg.add(t)
    t.add_done_callback(_bg.discard)


@asynccontextmanager
async def lifespan(_: FastAPI):
    manager.start()
    # Faixas que ficaram "matching"/"queued" de uma sessão anterior.
    for p in db.list_projects():
        for t in db.list_tracks(p["id"]):
            if t.get("status") == "matching":
                spawn(run_match(t["id"]))
            dl = t.get("download") or {}
            if dl.get("status") in ("queued", "downloading", "processing"):
                t["download"] = {"status": "idle"}
                db.save_track(t)
    yield
    await manager.stop()


app = FastAPI(title="DJ Downloader", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    hub.clients.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        hub.clients.discard(ws)


# ---------- helpers ----------

def new_track(source: dict, origin: str) -> dict:
    return {
        "id": db.new_id(),
        "origin": origin,
        "source": source,
        "status": "matching",
        "candidates": [],
        "alternatives": [],
        "selected": None,
        "confidence": None,
        "download": {"status": "idle"},
    }


async def emit_track(t: dict) -> None:
    await hub.broadcast({"type": "track", "track": t})


async def run_match(tid: str, query_override: str | None = None) -> None:
    async with match_sem:
        t = db.get_track(tid)
        if not t:
            return
        try:
            src = dict(t["source"])
            if query_override:
                cands = await asyncio.to_thread(engine.search, query_override, "songs", 8)
                cands += await asyncio.to_thread(engine.search, query_override, "videos", 5)
                ranked = sorted((engine._decorate(c, engine.score(src, c)) for c in cands),
                                key=lambda c: c["score"], reverse=True)
                res = {"candidates": ranked[:8], "selected": ranked[0] if ranked else None,
                       "confidence": engine.confidence(ranked[0]["score"]) if ranked else "low",
                       "alternatives": t.get("alternatives") or []}
            else:
                res = await engine.match(src)
        except Exception as e:  # noqa: BLE001
            t = db.get_track(tid) or t
            t["status"] = "error"
            t["error"] = str(e)[:200]
            db.save_track(t)
            await emit_track(t)
            return
        t = db.get_track(tid) or t
        # Link colado pelo usuário: mantém a escolha dele e só guarda os candidatos.
        if t.get("origin") == "youtube" and t.get("selected") and not query_override:
            res["selected"] = t["selected"]
            res["confidence"] = "high"
        t.update(res)
        t["status"] = "matched" if res["selected"] else "not_found"
        if not t["source"].get("cover") and res["selected"]:
            t["source"]["cover_fallback"] = res["selected"].get("thumbnail")
        db.save_track(t)
        await emit_track(t)


def ensure_singles() -> dict:
    return db.get_project_meta(SINGLES_ID) or db.create_project(
        "Avulsas", "singles", None, None, project_id=SINGLES_ID)


def parse_text_lines(text: str) -> list[dict]:
    out = []
    for line in text.splitlines():
        line = line.strip().strip("-•*").strip()
        line = re.sub(r"^\d+[\.\)]\s*", "", line)
        if not line or line.startswith("http"):
            continue
        if " - " in line:
            a, title = line.split(" - ", 1)
            artists = [x.strip() for x in re.split(r",|&| feat\.? | ft\.? ", a) if x.strip()]
            out.append({"title": title.strip(), "artists": artists, "duration": None})
        else:
            out.append({"title": line, "artists": [], "duration": None, "free_text": True})
    return out


# ---------- rotas: resolver entrada ----------

class ResolveIn(BaseModel):
    input: str
    project_id: str | None = None


@app.post("/api/resolve")
async def resolve(body: ResolveIn) -> dict:
    text = body.input.strip()
    if not text:
        raise HTTPException(400, "Cole um link ou digite uma música.")

    track_ids = spotify.find_track_ids(text)
    sp = spotify.parse_spotify(text)
    yt_ids = list(dict.fromkeys(YT_ID_RE.findall(text)))

    # Playlist / álbum do Spotify
    if sp and sp[0] in ("playlist", "album") and not body.project_id:
        try:
            col = await spotify.fetch_collection(sp[0], sp[1])
        except spotify.SpotifyError as e:
            raise HTTPException(502, str(e))
        url = f"https://open.spotify.com/{sp[0]}/{sp[1]}"
        project = db.create_project(col["name"], sp[0], url, col["cover"])
        tracks = [new_track(t, "spotify") for t in col["tracks"]]
        db.add_tracks(project["id"], tracks)
        for t in tracks:
            spawn(run_match(t["id"]))
        return {"project_id": project["id"], "kind": sp[0], "count": len(tracks),
                "truncated": col["truncated"]}

    target = body.project_id
    if target and not db.get_project_meta(target):
        raise HTTPException(404, "Projeto não encontrado.")

    # Várias faixas do Spotify coladas (Cmd+A / Cmd+C)
    if len(track_ids) > 1 or (track_ids and target):
        if target:
            existing = {t["source"].get("spotify_id") for t in db.list_tracks(target)}
            track_ids = [i for i in track_ids if i not in existing]
        sources = await spotify.fetch_tracks(track_ids)
        if not target:
            target = db.create_project(f"Lista colada ({len(sources)} faixas)", "list", None,
                                       sources[0]["cover"] if sources else None)["id"]
        tracks = [new_track(s, "spotify") for s in sources]
        db.add_tracks(target, tracks)
        for t in tracks:
            spawn(run_match(t["id"]))
        return {"project_id": target, "kind": "list", "count": len(tracks), "track_ids": [t["id"] for t in tracks]}

    # Faixa única do Spotify
    if track_ids:
        try:
            src = await spotify.fetch_track(track_ids[0])
        except spotify.SpotifyError as e:
            raise HTTPException(502, str(e))
        target = target or ensure_singles()["id"]
        t = new_track(src, "spotify")
        db.add_tracks(target, [t])
        spawn(run_match(t["id"]))
        return {"project_id": target, "kind": "track", "count": 1, "track_ids": [t["id"]]}

    # Links do YouTube / YouTube Music
    if yt_ids:
        target = target or ensure_singles()["id"]
        tracks = []
        for vid in yt_ids:
            try:
                info = await engine.video_info(vid)
            except Exception as e:  # noqa: BLE001
                raise HTTPException(502, f"Não consegui ler o vídeo {vid}: {e}")
            t = new_track(info["source"], "youtube")
            cand = engine._decorate(info["candidate"], 1.0)
            t["selected"] = cand
            t["confidence"] = "high"
            tracks.append(t)
        db.add_tracks(target, tracks)
        for t in tracks:
            spawn(run_match(t["id"]))
        return {"project_id": target, "kind": "youtube", "count": len(tracks), "track_ids": [t["id"] for t in tracks]}

    # Texto livre: uma ou várias linhas "Artista - Música"
    sources = parse_text_lines(text)
    if not sources:
        raise HTTPException(400, "Não reconheci a entrada.")
    if not target:
        target = ensure_singles()["id"] if len(sources) == 1 else db.create_project(
            f"Lista ({len(sources)} faixas)", "list", None, None)["id"]
    tracks = []
    for s in sources:
        if s.pop("free_text", False):
            # Sem separador: busca direto e usa o melhor resultado como origem.
            res = await asyncio.to_thread(engine.search, s["title"], "songs", 1)
            if res:
                s = {"title": res[0]["title"], "artists": res[0]["artists"],
                     "duration": res[0]["duration"], "album": res[0]["album"]}
        tracks.append(new_track(s, "text"))
    db.add_tracks(target, tracks)
    for t in tracks:
        spawn(run_match(t["id"]))
    return {"project_id": target, "kind": "text", "count": len(tracks), "track_ids": [t["id"] for t in tracks]}


# ---------- projetos ----------

@app.get("/api/projects")
async def projects() -> list[dict]:
    return db.list_projects()


@app.get("/api/projects/{pid}")
async def project(pid: str) -> dict:
    p = db.get_project(pid)
    if not p:
        raise HTTPException(404, "Projeto não encontrado.")
    return p


class ProjectPatch(BaseModel):
    name: str


@app.patch("/api/projects/{pid}")
async def patch_project(pid: str, body: ProjectPatch) -> dict:
    db.rename_project(pid, body.name.strip() or "Sem nome")
    return db.get_project(pid)


@app.delete("/api/projects/{pid}")
async def delete_project(pid: str) -> dict:
    db.delete_project(pid)
    return {"ok": True}


@app.post("/api/projects/{pid}/reveal")
async def reveal(pid: str) -> dict:
    p = db.get_project_meta(pid)
    if not p:
        raise HTTPException(404)
    folder = Path(db.get_settings()["output_dir"]).expanduser() / sanitize(p["name"])
    folder.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(["open", str(folder)])
    return {"ok": True, "path": str(folder)}


@app.get("/api/projects/{pid}/zip")
async def project_zip(pid: str):
    p = db.get_project(pid)
    if not p:
        raise HTTPException(404)
    files = [Path(t["download"]["path"]) for t in p["tracks"]
             if (t.get("download") or {}).get("status") == "done"
             and Path(t["download"]["path"]).exists()]
    if not files:
        raise HTTPException(400, "Nenhuma faixa baixada ainda.")

    def build() -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
            for f in files:
                z.write(f, f.name)
        return buf.getvalue()

    data = await asyncio.to_thread(build)
    name = sanitize(p["name"]) + ".zip"
    return StreamingResponse(io.BytesIO(data), media_type="application/zip",
                             headers={"Content-Disposition": f"attachment; filename*=UTF-8''{_q(name)}"})


def _q(s: str) -> str:
    from urllib.parse import quote
    return quote(s)


# ---------- faixas ----------

class TrackPatch(BaseModel):
    video_id: str | None = None
    url: str | None = None


@app.patch("/api/tracks/{tid}")
async def patch_track(tid: str, body: TrackPatch) -> dict:
    t = db.get_track(tid)
    if not t:
        raise HTTPException(404)
    chosen = None
    if body.url:
        m = YT_ID_RE.search(body.url) or re.fullmatch(r"([A-Za-z0-9_-]{11})", body.url.strip())
        if not m:
            raise HTTPException(400, "Link do YouTube inválido.")
        info = await engine.video_info(m.group(1))
        chosen = engine._decorate(info["candidate"], engine.score(t["source"], info["candidate"]))
        chosen["manual"] = True
        t["candidates"] = [chosen] + [c for c in t.get("candidates", []) if c["video_id"] != chosen["video_id"]]
    elif body.video_id:
        for c in (t.get("candidates") or []) + (t.get("alternatives") or []):
            if c["video_id"] == body.video_id:
                chosen = c
                break
        if not chosen:
            raise HTTPException(400, "Candidato não encontrado.")
    if not chosen:
        raise HTTPException(400, "Nada para alterar.")
    t["selected"] = chosen
    t["confidence"] = "high"
    t["status"] = "matched"
    t["user_confirmed"] = True
    if (t.get("download") or {}).get("status") == "done":
        t["download"] = {"status": "idle", "previous_path": t["download"].get("path")}
    db.save_track(t)
    await emit_track(t)
    return t


class RematchIn(BaseModel):
    query: str | None = None


@app.post("/api/tracks/{tid}/rematch")
async def rematch(tid: str, body: RematchIn) -> dict:
    t = db.get_track(tid)
    if not t:
        raise HTTPException(404)
    t["status"] = "matching"
    db.save_track(t)
    await emit_track(t)
    spawn(run_match(tid, body.query or None))
    return {"ok": True}


@app.delete("/api/tracks/{tid}")
async def delete_track(tid: str) -> dict:
    db.delete_track(tid)
    return {"ok": True}


@app.get("/api/tracks/{tid}/file")
async def track_file(tid: str):
    t = db.get_track(tid)
    path = Path(((t or {}).get("download") or {}).get("path") or "")
    if not t or not path.exists():
        raise HTTPException(404, "Arquivo não encontrado.")
    return FileResponse(path, filename=path.name)


@app.get("/api/search")
async def search(q: str) -> list[dict]:
    songs = await asyncio.to_thread(engine.search, q, "songs", 8)
    videos = await asyncio.to_thread(engine.search, q, "videos", 5)
    return [engine._decorate(c, 0) for c in songs + videos]


# ---------- downloads ----------

class DownloadIn(BaseModel):
    track_ids: list[str] | None = None
    project_id: str | None = None
    include_low: bool = False
    redownload: bool = False


@app.post("/api/download")
async def download(body: DownloadIn) -> dict:
    ids = body.track_ids or []
    if body.project_id:
        for t in db.list_tracks(body.project_id):
            if not t.get("selected"):
                continue
            if not body.redownload and (t.get("download") or {}).get("status") == "done":
                continue
            if t.get("confidence") == "low" and not body.include_low and not t.get("user_confirmed"):
                continue
            ids.append(t["id"])
    n = await manager.enqueue(ids)
    return {"queued": n}


# ---------- preview de áudio ----------

_preview_cache: dict[str, str] = {}


def _preview_url(video_id: str) -> str:
    if video_id in _preview_cache:
        return _preview_cache[video_id]
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "format": "140/bestaudio[ext=m4a]/bestaudio"}) as y:
        info = y.extract_info(f"https://music.youtube.com/watch?v={video_id}", download=False)
    url = info["url"]
    _preview_cache[video_id] = url
    return url


@app.get("/api/preview/{video_id}")
async def preview(video_id: str, request: Request):
    try:
        url = await asyncio.to_thread(_preview_url, video_id)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Preview indisponível: {str(e)[:120]}")
    headers = {}
    if rng := request.headers.get("range"):
        headers["Range"] = rng
    client = httpx.AsyncClient(timeout=30, follow_redirects=True)
    req = client.build_request("GET", url, headers=headers)
    r = await client.send(req, stream=True)
    if r.status_code >= 400:
        await r.aclose()
        await client.aclose()
        _preview_cache.pop(video_id, None)
        raise HTTPException(502, "Preview indisponível.")
    out_headers = {k: v for k, v in r.headers.items()
                   if k.lower() in ("content-length", "content-range", "accept-ranges", "content-type")}

    async def body():
        try:
            async for chunk in r.aiter_bytes(64 * 1024):
                yield chunk
        finally:
            await r.aclose()
            await client.aclose()

    return StreamingResponse(body(), status_code=r.status_code, headers=out_headers,
                             media_type=r.headers.get("content-type", "audio/mp4"))


# ---------- configurações / status ----------

@app.get("/api/settings")
async def get_settings() -> dict:
    return db.get_settings()


@app.put("/api/settings")
async def put_settings(body: dict[str, Any]) -> dict:
    if "format" in body and body["format"] not in ("mp3", "wav", "m4a"):
        raise HTTPException(400, "Formato inválido.")
    return db.update_settings(body)


@app.get("/api/chrome-profiles")
async def get_chrome_profiles() -> dict:
    s = db.get_settings()
    return {"profiles": chrome_profiles(), "resolved": resolve_profile(s.get("cookies_profile") or "")}


@app.get("/api/health")
async def health() -> dict:
    return {
        "ok": True,
        "yt_dlp": yt_dlp.version.__version__,
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "deno": bool(shutil.which("deno")),
        "queue": manager.queue.qsize(),
    }


@app.post("/api/check-premium")
async def check_premium() -> dict:
    """Testa os cookies: lista os formatos de uma faixa e vê se o itag 141 (256kbps) aparece."""
    from .download.manager import cookies_option
    s = db.get_settings()
    cookies = cookies_option(s)
    if not cookies:
        return {"ok": False, "premium": False, "message": "Cookies desativados nas configurações."}

    def run() -> dict:
        opts = {"quiet": True, "no_warnings": True, "cookiesfrombrowser": cookies, "skip_download": True}
        with yt_dlp.YoutubeDL(opts) as y:
            info = y.extract_info("https://music.youtube.com/watch?v=FXk4oLgkKL0", download=False)
        ids = {f.get("format_id") for f in info.get("formats") or []}
        return {"ok": True, "premium": "141" in ids, "profile": cookies[1],
                "message": "256kbps disponível (Premium ativo)." if "141" in ids
                else "Cookies lidos, mas o 256kbps não apareceu. Confira se o perfil é o da conta Premium."}

    try:
        return await asyncio.to_thread(run)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "premium": False, "profile": cookies[1], "message": str(e)[:300]}


# ---------- frontend estático (SPA fallback) ----------

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    from fastapi.staticfiles import StaticFiles

    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.api_route("/{full_path:path}", methods=["GET", "HEAD"])
    async def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path == "ws":
            raise HTTPException(404)
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")

