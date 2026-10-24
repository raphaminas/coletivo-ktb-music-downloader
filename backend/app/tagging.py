"""Gravação de tags (título, artista, álbum, ano, capa) com mutagen."""
from __future__ import annotations

from pathlib import Path

import httpx
from mutagen.id3 import APIC, ID3, TALB, TDRC, TIT2, TPE1, TPE2, COMM, ID3NoHeaderError
from mutagen.mp4 import MP4, MP4Cover
from mutagen.wave import WAVE


def fetch_cover(url: str | None) -> tuple[bytes, str] | None:
    if not url:
        return None
    try:
        r = httpx.get(url, timeout=20, follow_redirects=True)
        if r.status_code == 200 and r.content:
            mime = r.headers.get("content-type", "image/jpeg").split(";")[0]
            if mime not in ("image/jpeg", "image/png"):
                mime = "image/jpeg"
            return r.content, mime
    except Exception:
        pass
    return None


def _id3_frames(tags: ID3, meta: dict, cover: tuple[bytes, str] | None) -> None:
    tags.delall("APIC")
    tags.delall("TXXX")
    tags.add(TIT2(encoding=3, text=meta["title"]))
    tags.add(TPE1(encoding=3, text=meta["artist"]))
    tags.add(TPE2(encoding=3, text=meta.get("album_artist") or meta["artist"]))
    if meta.get("album"):
        tags.add(TALB(encoding=3, text=meta["album"]))
    if meta.get("year"):
        tags.add(TDRC(encoding=3, text=str(meta["year"])))
    if meta.get("comment"):
        tags.add(COMM(encoding=3, lang="por", desc="", text=meta["comment"]))
    if cover:
        tags.add(APIC(encoding=3, mime=cover[1], type=3, desc="Cover", data=cover[0]))


def write_tags(path: Path, meta: dict) -> None:
    """meta: title, artist, album, year, cover_url, comment."""
    cover = fetch_cover(meta.get("cover_url"))
    ext = path.suffix.lower()
    if ext == ".mp3":
        try:
            tags = ID3(path)
        except ID3NoHeaderError:
            tags = ID3()
        _id3_frames(tags, meta, cover)
        tags.save(path, v2_version=3)
    elif ext in (".m4a", ".mp4", ".aac"):
        f = MP4(path)
        f["\xa9nam"] = [meta["title"]]
        f["\xa9ART"] = [meta["artist"]]
        f["aART"] = [meta.get("album_artist") or meta["artist"]]
        if meta.get("album"):
            f["\xa9alb"] = [meta["album"]]
        if meta.get("year"):
            f["\xa9day"] = [str(meta["year"])]
        if meta.get("comment"):
            f["\xa9cmt"] = [meta["comment"]]
        if cover:
            fmt = MP4Cover.FORMAT_PNG if cover[1] == "image/png" else MP4Cover.FORMAT_JPEG
            f["covr"] = [MP4Cover(cover[0], imageformat=fmt)]
        f.save()
    elif ext == ".wav":
        f = WAVE(path)
        if f.tags is None:
            f.add_tags()
        _id3_frames(f.tags, meta, cover)
        f.save()
