"""Leitura de faixas do Spotify sem login, pela página embed pública.

Camadas:
1. Embed público (open.spotify.com/embed/...): título, artistas, duração. Limite de 100 faixas.
2. Colar a lista: links de faixas (Cmd+A / Cmd+C no Spotify desktop), resolvidos um a um.
"""
from __future__ import annotations

import asyncio
import json
import re

import httpx

UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
EMBED_LIMIT = 100

SPOTIFY_RE = re.compile(
    r"(?:open\.spotify\.com/(?:intl-[a-z]{2}/)?(?:embed/)?|spotify:)"
    r"(playlist|track|album)[/:]([A-Za-z0-9]{22})"
)
NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S
)


class SpotifyError(Exception):
    pass


def parse_spotify(text: str) -> tuple[str, str] | None:
    m = SPOTIFY_RE.search(text)
    return (m.group(1), m.group(2)) if m else None


def find_track_ids(text: str) -> list[str]:
    """Todos os IDs de faixa num texto colado, na ordem e sem repetição."""
    seen: dict[str, None] = {}
    for kind, sid in SPOTIFY_RE.findall(text):
        if kind == "track":
            seen.setdefault(sid, None)
    return list(seen)


def _best_image(images: list[dict] | None) -> str | None:
    if not images:
        return None
    best = max(images, key=lambda i: (i.get("maxWidth") or i.get("width") or 0))
    return best.get("url")


async def _entity(client: httpx.AsyncClient, kind: str, sid: str) -> dict:
    r = await client.get(f"https://open.spotify.com/embed/{kind}/{sid}")
    if r.status_code != 200:
        raise SpotifyError(f"Spotify respondeu {r.status_code} para {kind} {sid}")
    m = NEXT_DATA_RE.search(r.text)
    if not m:
        raise SpotifyError("Não encontrei os dados na página do Spotify (o layout pode ter mudado).")
    try:
        return json.loads(m.group(1))["props"]["pageProps"]["state"]["data"]["entity"]
    except (KeyError, TypeError) as e:
        raise SpotifyError("Formato inesperado na página do Spotify.") from e


def _split_artists(subtitle: str) -> list[str]:
    return [a.strip() for a in re.split(r",\s*|\s*&\s*", subtitle or "") if a.strip()]


def _track_from_list_item(item: dict) -> dict:
    sid = (item.get("uri") or "").split(":")[-1]
    return {
        "spotify_id": sid,
        "title": item.get("title") or "",
        "artists": _split_artists(item.get("subtitle", "")),
        "duration": round((item.get("duration") or 0) / 1000),
        "explicit": bool(item.get("isExplicit")),
        "album": None,
        "cover": None,
    }


async def fetch_collection(kind: str, sid: str) -> dict:
    """Playlist ou álbum: {name, cover, tracks, truncated}."""
    async with httpx.AsyncClient(headers=UA, follow_redirects=True, timeout=20) as client:
        e = await _entity(client, kind, sid)
    images = (e.get("visualIdentity") or {}).get("image") or (e.get("coverArt") or {}).get("sources")
    cover = _best_image(images)
    tracks = [_track_from_list_item(i) for i in e.get("trackList") or []]
    if kind == "album":
        for t in tracks:
            t["album"] = e.get("name")
            t["cover"] = cover
    return {
        "name": e.get("name") or e.get("title") or "Playlist",
        "subtitle": e.get("subtitle"),
        "cover": cover,
        "tracks": tracks,
        "truncated": len(tracks) >= EMBED_LIMIT,
    }


async def fetch_track(sid: str, client: httpx.AsyncClient | None = None) -> dict:
    own = client is None
    client = client or httpx.AsyncClient(headers=UA, follow_redirects=True, timeout=20)
    try:
        e = await _entity(client, "track", sid)
    finally:
        if own:
            await client.aclose()
    images = (e.get("visualIdentity") or {}).get("image") or (e.get("coverArt") or {}).get("sources")
    release = (e.get("releaseDate") or {}).get("isoString") or ""
    return {
        "spotify_id": sid,
        "title": e.get("title") or e.get("name") or "",
        "artists": [a["name"] for a in e.get("artists") or []] or _split_artists(e.get("subtitle", "")),
        "duration": round((e.get("duration") or 0) / 1000),
        "explicit": bool(e.get("isExplicit")),
        "album": None,
        "year": release[:4] or None,
        "cover": _best_image(images),
    }


async def fetch_tracks(ids: list[str], concurrency: int = 6) -> list[dict]:
    sem = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(headers=UA, follow_redirects=True, timeout=20) as client:
        async def one(sid: str) -> dict | None:
            async with sem:
                try:
                    return await fetch_track(sid, client)
                except Exception:
                    return None
        results = await asyncio.gather(*(one(i) for i in ids))
    return [r for r in results if r]
