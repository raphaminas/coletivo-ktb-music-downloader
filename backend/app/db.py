"""Persistência simples em SQLite: projetos, faixas, cache de downloads e configurações."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import os
import sys

def get_data_dir() -> Path:
    custom = os.environ.get("DJ_DATA_DIR")
    if custom:
        d = Path(custom)
    elif getattr(sys, "frozen", False):
        if sys.platform == "win32":
            base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
            d = Path(base) / "DJ Downloader"
        elif sys.platform == "darwin":
            d = Path.home() / "Library" / "Application Support" / "DJ Downloader"
        else:
            d = Path.home() / ".config" / "dj-downloader"
    else:
        d = Path(__file__).resolve().parent.parent / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d

DATA_DIR = get_data_dir()
DB_PATH = DATA_DIR / "dj.sqlite3"

DEFAULT_SETTINGS: dict[str, Any] = {
    # "mp3" (320 CBR), "wav" (PCM 16-bit/44.1k) ou "m4a" (AAC original, sem recompressão)
    "format": "mp3",
    "output_dir": str(Path.home() / "Music" / "DJ Downloader"),
    "cookies_browser": "chrome",  # "" para desativar
    # Nome do perfil do Chrome (ex.: "Profile 1", "Default") ou "" para o perfil principal
    "cookies_profile": "",
    "filename_pattern": "{artist} - {title}",
    "min_bitrate": 192,
    "concurrency": 2,
}

_lock = threading.RLock()
_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
_conn.row_factory = sqlite3.Row
_conn.execute("PRAGMA journal_mode=WAL")
_conn.executescript(
    """
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        kind TEXT NOT NULL,
        source_url TEXT,
        cover TEXT,
        created_at REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS tracks (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        position INTEGER NOT NULL,
        data TEXT NOT NULL,
        FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_tracks_project ON tracks(project_id, position);
    CREATE TABLE IF NOT EXISTS downloads (
        video_id TEXT NOT NULL,
        format TEXT NOT NULL,
        path TEXT NOT NULL,
        source_abr REAL,
        created_at REAL NOT NULL,
        PRIMARY KEY (video_id, format)
    );
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """
)
_conn.commit()


def new_id() -> str:
    return uuid.uuid4().hex[:12]


# ---------- settings ----------

def get_settings() -> dict[str, Any]:
    with _lock:
        rows = _conn.execute("SELECT key, value FROM settings").fetchall()
    s = dict(DEFAULT_SETTINGS)
    for r in rows:
        s[r["key"]] = json.loads(r["value"])
    return s


def update_settings(values: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        for k, v in values.items():
            if k in DEFAULT_SETTINGS:
                _conn.execute(
                    "INSERT INTO settings(key, value) VALUES(?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (k, json.dumps(v)),
                )
        _conn.commit()
    return get_settings()


# ---------- projects ----------

def create_project(name: str, kind: str, source_url: str | None, cover: str | None,
                   project_id: str | None = None) -> dict:
    pid = project_id or new_id()
    with _lock:
        _conn.execute(
            "INSERT OR IGNORE INTO projects(id, name, kind, source_url, cover, created_at) "
            "VALUES(?,?,?,?,?,?)",
            (pid, name, kind, source_url, cover, time.time()),
        )
        _conn.commit()
    return get_project_meta(pid)  # type: ignore[return-value]


def get_project_meta(pid: str) -> dict | None:
    with _lock:
        r = _conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    return dict(r) if r else None


def rename_project(pid: str, name: str) -> None:
    with _lock:
        _conn.execute("UPDATE projects SET name=? WHERE id=?", (name, pid))
        _conn.commit()


def delete_project(pid: str) -> None:
    with _lock:
        _conn.execute("DELETE FROM tracks WHERE project_id=?", (pid,))
        _conn.execute("DELETE FROM projects WHERE id=?", (pid,))
        _conn.commit()


def list_projects() -> list[dict]:
    with _lock:
        rows = _conn.execute(
            "SELECT p.*, "
            "(SELECT COUNT(*) FROM tracks t WHERE t.project_id=p.id) AS track_count, "
            "(SELECT COUNT(*) FROM tracks t WHERE t.project_id=p.id "
            "   AND json_extract(t.data, '$.download.status')='done') AS done_count "
            "FROM projects p ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_project(pid: str) -> dict | None:
    meta = get_project_meta(pid)
    if not meta:
        return None
    meta["tracks"] = list_tracks(pid)
    return meta


# ---------- tracks ----------

def add_tracks(pid: str, tracks: list[dict]) -> None:
    with _lock:
        start = _conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 FROM tracks WHERE project_id=?", (pid,)
        ).fetchone()[0]
        for i, t in enumerate(tracks):
            t.setdefault("id", new_id())
            t["project_id"] = pid
            _conn.execute(
                "INSERT INTO tracks(id, project_id, position, data) VALUES(?,?,?,?)",
                (t["id"], pid, start + i, json.dumps(t)),
            )
        _conn.commit()


def list_tracks(pid: str) -> list[dict]:
    with _lock:
        rows = _conn.execute(
            "SELECT data FROM tracks WHERE project_id=? ORDER BY position", (pid,)
        ).fetchall()
    return [json.loads(r["data"]) for r in rows]


def get_track(tid: str) -> dict | None:
    with _lock:
        r = _conn.execute("SELECT data FROM tracks WHERE id=?", (tid,)).fetchone()
    return json.loads(r["data"]) if r else None


def save_track(track: dict) -> None:
    with _lock:
        _conn.execute("UPDATE tracks SET data=? WHERE id=?", (json.dumps(track), track["id"]))
        _conn.commit()


def delete_track(tid: str) -> None:
    with _lock:
        _conn.execute("DELETE FROM tracks WHERE id=?", (tid,))
        _conn.commit()


# ---------- download cache ----------

def cached_download(video_id: str, fmt: str) -> dict | None:
    with _lock:
        r = _conn.execute(
            "SELECT * FROM downloads WHERE video_id=? AND format=?", (video_id, fmt)
        ).fetchone()
    if r and Path(r["path"]).exists():
        return dict(r)
    return None


def remember_download(video_id: str, fmt: str, path: str, source_abr: float | None) -> None:
    with _lock:
        _conn.execute(
            "INSERT INTO downloads(video_id, format, path, source_abr, created_at) VALUES(?,?,?,?,?) "
            "ON CONFLICT(video_id, format) DO UPDATE SET path=excluded.path, "
            "source_abr=excluded.source_abr, created_at=excluded.created_at",
            (video_id, fmt, path, source_abr, time.time()),
        )
        _conn.commit()
