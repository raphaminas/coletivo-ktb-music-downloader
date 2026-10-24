"""Motor de match: busca no YouTube Music e pontua candidatos para uma faixa de origem."""
from __future__ import annotations

import asyncio
import re
import threading
import unicodedata
from functools import lru_cache

from rapidfuzz import fuzz
from ytmusicapi import YTMusic

_local = threading.local()


def _ytm() -> YTMusic:
    # YTMusic não é thread-safe: uma instância por thread.
    if not hasattr(_local, "ytm"):
        _local.ytm = YTMusic(language="en")
    return _local.ytm


# ---------- normalização ----------

VERSION_TAGS: dict[str, re.Pattern] = {
    "live": re.compile(r"\b(live|ao vivo|en vivo|unplugged|live at|live from)\b"),
    "cover": re.compile(r"\b(cover|tribute|made famous|in the style of|originally performed)\b"),
    "karaoke": re.compile(r"\b(karaoke|instrumental|backing track|playback)\b"),
    "8d": re.compile(r"\b(8d|16d|3d audio)\b"),
    "sped_up": re.compile(r"\b(sped up|speed up|nightcore)\b"),
    "slowed": re.compile(r"\b(slowed|reverb)\b"),
    "remix": re.compile(r"\b(remix|rmx|bootleg|mashup|vip mix|rework)\b"),
    "extended": re.compile(r"\b(extended|club mix|12\"|12 inch|full length|original mix|dub mix)\b"),
    "acoustic": re.compile(r"\b(acoustic|acustico|acústico)\b"),
    "radio_edit": re.compile(r"\b(radio edit|radio version|clean)\b"),
}
# Penalidade quando o candidato tem a tag e a faixa de origem não.
TAG_PENALTY = {
    "live": 0.35, "cover": 0.5, "karaoke": 0.6, "8d": 0.5, "sped_up": 0.5, "slowed": 0.5,
    "remix": 0.3, "extended": 0.12, "acoustic": 0.25, "radio_edit": 0.05,
}
TAG_LABEL = {
    "extended": "Extended", "live": "Ao vivo", "remix": "Remix", "acoustic": "Acústico",
    "radio_edit": "Radio Edit", "cover": "Cover", "karaoke": "Karaokê/Instrumental",
    "8d": "8D", "sped_up": "Sped up", "slowed": "Slowed",
}

NOISE = re.compile(
    r"\s*[\(\[][^\)\]]*\b(feat|ft|with|prod|remaster(ed)?|official|video|audio|lyrics?|"
    r"letra|visualizer|hd|hq|4k)\b[^\)\]]*[\)\]]",
    re.I,
)
DASH_SUFFIX = re.compile(r"\s+-\s+(\d{4}\s+)?(remaster(ed)?|mono|stereo|single version|from .*)\b.*$", re.I)
FEAT = re.compile(r"\s+(feat\.?|ft\.?|featuring)\s+.*$", re.I)
UNOFFICIAL = re.compile(r"\b(unofficial|tiktok|fan made|fanmade|bootleg|mashup|intro outro|dj [a-z]+ (mix|edit|remix))\b")


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def norm(s: str) -> str:
    s = strip_accents(s or "").lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[^\w\s\"]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def core_title(title: str) -> str:
    """Título sem feat., remaster, (Official Video) etc. Mantém marcadores de versão."""
    t = NOISE.sub("", title or "")
    t = DASH_SUFFIX.sub("", t)
    t = FEAT.sub("", t)
    return t.strip()


def bare_title(title: str) -> str:
    """Título sem nada entre parênteses/colchetes nem sufixos após ' - '."""
    t = re.sub(r"[\(\[].*?[\)\]]", "", title or "")
    t = re.split(r"\s+-\s+", t)[0]
    return FEAT.sub("", t).strip()


def tags_of(text: str) -> set[str]:
    n = norm(text)
    return {k for k, rx in VERSION_TAGS.items() if rx.search(n)}


def version_label(title: str) -> str | None:
    """Rótulo da versão a partir do título (ex.: 'Extended Mix')."""
    m = re.search(r"[\(\[]([^\)\]]*(mix|edit|version|live|ao vivo|remix|acoustic|ac[uú]stico)[^\)\]]*)[\)\]]",
                  title or "", re.I)
    if m:
        return m.group(1).strip()
    m = re.search(r"\s-\s([^-]*(mix|edit|version|live|ao vivo|remix)[^-]*)$", title or "", re.I)
    return m.group(1).strip() if m else None


def hires_thumb(url: str | None, size: int = 1200) -> str | None:
    if not url:
        return None
    if "googleusercontent.com" in url or "ggpht.com" in url:
        return re.sub(r"=w\d+-h\d+.*$", f"=w{size}-h{size}-l90-rj", url)
    return url


# ---------- candidatos ----------

def _candidate_from_search(r: dict) -> dict | None:
    vid = r.get("videoId")
    if not vid:
        return None
    vtype = r.get("videoType") or ""
    kind = "song" if r.get("resultType") == "song" or vtype == "MUSIC_VIDEO_TYPE_ATV" else "video"
    thumbs = r.get("thumbnails") or []
    return {
        "video_id": vid,
        "title": r.get("title") or "",
        "artists": [a["name"] for a in r.get("artists") or [] if a.get("name")],
        "album": (r.get("album") or {}).get("name"),
        "duration": r.get("duration_seconds"),
        "thumbnail": hires_thumb(thumbs[-1]["url"]) if thumbs else None,
        "kind": kind,
        "video_type": vtype,
        "explicit": bool(r.get("isExplicit")),
    }


@lru_cache(maxsize=2048)
def _search_cached(query: str, filt: str, limit: int) -> tuple:
    try:
        res = _ytm().search(query, filter=filt, limit=limit)
    except Exception:
        res = []
    out = []
    for r in res:
        c = _candidate_from_search(r)
        if c:
            out.append(c)
    return tuple(out)


def search(query: str, filt: str = "songs", limit: int = 10) -> list[dict]:
    return [dict(c) for c in _search_cached(query.strip(), filt, limit)]


# ---------- pontuação ----------

def _duration_score(src: int | None, cand: int | None) -> float:
    if not src or not cand:
        return 0.6
    d = abs(src - cand)
    if d <= 3:
        return 1.0
    if d <= 7:
        return 0.85
    if d <= 15:
        return 0.55
    if d <= 30:
        return 0.25
    return 0.0


def _artist_score(src_artists: list[str], cand: dict) -> float:
    if not src_artists:
        return 0.6
    cand_names = [norm(a.replace(" - Topic", "")) for a in cand["artists"]]
    blob = " ".join(cand_names) + " " + norm(cand["title"])
    main = norm(src_artists[0])
    main_hit = max([fuzz.ratio(main, c) for c in cand_names] + [fuzz.partial_ratio(main, blob)]) / 100
    if len(src_artists) == 1:
        return main_hit
    others = [fuzz.partial_ratio(norm(a), blob) / 100 for a in src_artists[1:]]
    return 0.75 * main_hit + 0.25 * (sum(others) / len(others))


def score(source: dict, cand: dict, ignore_duration: bool = False) -> float:
    src_title = source.get("title") or ""
    st, ct = norm(bare_title(src_title)), norm(bare_title(cand["title"]))
    title_sim = max(fuzz.ratio(st, ct), fuzz.token_set_ratio(norm(core_title(src_title)),
                                                             norm(core_title(cand["title"])))) / 100
    artist_sim = _artist_score(source.get("artists") or [], cand)
    dur = 0.8 if ignore_duration else _duration_score(source.get("duration"), cand.get("duration"))
    kind = 1.0 if cand["kind"] == "song" else (0.6 if cand.get("video_type") == "MUSIC_VIDEO_TYPE_OMV" else 0.35)

    s = 0.35 * title_sim + 0.30 * artist_sim + 0.25 * dur + 0.10 * kind

    src_tags = tags_of(src_title)
    cand_tags = tags_of(cand["title"] + " " + (cand.get("album") or ""))
    for tag in cand_tags - src_tags:
        if ignore_duration and tag == "extended":
            continue
        s -= TAG_PENALTY[tag]
    # Origem é remix/ao vivo e candidato não: penaliza também (versão diferente).
    for tag in src_tags - cand_tags:
        if tag in ("remix", "live", "acoustic"):
            s -= 0.15
    return round(max(0.0, min(1.0, s)), 3)


def confidence(s: float) -> str:
    if s >= 0.82:
        return "high"
    if s >= 0.62:
        return "medium"
    return "low"


def _decorate(c: dict, s: float) -> dict:
    c = dict(c)
    c["score"] = s
    c["tags"] = sorted(tags_of(c["title"]))
    c["version"] = version_label(c["title"])
    return c


def _query_for(source: dict) -> str:
    artists = source.get("artists") or []
    return f"{' '.join(artists[:2])} {core_title(source.get('title', ''))}".strip()


def match_sync(source: dict) -> dict:
    """Retorna {candidates, selected, confidence, alternatives}."""
    q = _query_for(source)
    pool: dict[str, dict] = {}
    for c in search(q, "songs", 10):
        pool.setdefault(c["video_id"], c)
    ranked = sorted((_decorate(c, score(source, c)) for c in pool.values()),
                    key=lambda c: c["score"], reverse=True)

    if not ranked or ranked[0]["score"] < 0.82:
        for c in search(q, "videos", 6):
            if c["video_id"] not in pool:
                pool[c["video_id"]] = c
                ranked.append(_decorate(c, score(source, c)))
        ranked.sort(key=lambda c: c["score"], reverse=True)

    alternatives = find_alternatives(source, pool, ranked[0] if ranked else None)
    best = ranked[0] if ranked else None
    return {
        "candidates": ranked[:6],
        "selected": best,
        "confidence": confidence(best["score"]) if best else "low",
        "alternatives": alternatives,
    }


def find_alternatives(source: dict, pool: dict[str, dict], best: dict | None) -> list[dict]:
    """Sugestões para DJ: Extended/Club Mix e versão de estúdio quando a original é ao vivo."""
    src_tags = tags_of(source.get("title", ""))
    alts: list[dict] = []
    seen = {best["video_id"]} if best else set()

    def consider(c: dict, label: str, kind: str, need_tag: str | None = None, forbid: set[str] = frozenset()):
        if c["video_id"] in seen:
            return
        ctags = tags_of(c["title"] + " " + (c.get("album") or ""))
        if need_tag and need_tag not in tags_of(c["title"]):
            return
        if ctags & forbid:
            return
        if UNOFFICIAL.search(norm(c["title"])):
            return
        artists = source.get("artists") or []
        if c["kind"] != "song":
            # Vídeo comum só vale se vier do canal oficial do artista.
            chan = norm((c["artists"] or [""])[0].replace(" - Topic", ""))
            if not artists or fuzz.ratio(norm(artists[0]), chan) < 85:
                return
        tsim = fuzz.ratio(norm(bare_title(source.get("title", ""))), norm(bare_title(c["title"]))) / 100
        if tsim < 0.85 or _artist_score(artists, c) < 0.7:
            return
        d = _decorate(c, score(source, c, ignore_duration=True))
        d["alt_kind"] = kind
        d["alt_label"] = label
        seen.add(c["video_id"])
        alts.append(d)

    if "extended" not in src_tags:
        artist = (source.get("artists") or [""])[0]
        base = bare_title(source.get("title", ""))
        for c in search(f"{artist} {base} extended mix", "songs", 8) + search(
                f"{artist} {base} extended", "videos", 5):
            consider(c, version_label(c["title"]) or "Extended", "extended", need_tag="extended",
                     forbid={"cover", "karaoke", "8d", "sped_up", "slowed", "live"}
                     | ({"remix"} if "remix" not in src_tags else set()))

    if "live" in src_tags:
        studio_src = dict(source, title=re.sub(VERSION_TAGS["live"], "", norm(source.get("title", ""))))
        pool2 = list(pool.values()) + search(_query_for(studio_src), "songs", 8)
        for c in pool2:
            consider(c, "Versão de estúdio", "studio",
                     forbid={"live", "cover", "karaoke", "8d", "sped_up", "slowed", "remix"})
            if any(a["alt_kind"] == "studio" for a in alts):
                break

    alts.sort(key=lambda a: (a["alt_kind"] != "extended", -a["score"]))
    return alts[:4]


async def match(source: dict) -> dict:
    return await asyncio.to_thread(match_sync, source)


# ---------- metadados de um vídeo específico ----------

def video_info_sync(video_id: str) -> dict:
    """Metadados de um videoId (link colado). Converte em candidato + origem."""
    song = _ytm().get_song(video_id)
    vd = song.get("videoDetails") or {}
    title = vd.get("title") or ""
    author = (vd.get("author") or "").replace(" - Topic", "")
    thumbs = (vd.get("thumbnail") or {}).get("thumbnails") or []
    vtype = vd.get("musicVideoType") or ""
    artists = [author] if author else []
    src_title = title
    # Vídeo comum "Artista - Título": separa.
    if vtype != "MUSIC_VIDEO_TYPE_ATV" and " - " in title:
        a, t = title.split(" - ", 1)
        artists, src_title = [a.strip()], core_title(t)
    cand = {
        "video_id": video_id,
        "title": title,
        "artists": artists,
        "album": None,
        "duration": int(vd.get("lengthSeconds") or 0) or None,
        "thumbnail": hires_thumb(thumbs[-1]["url"]) if thumbs else None,
        "kind": "song" if vtype == "MUSIC_VIDEO_TYPE_ATV" else "video",
        "video_type": vtype,
        "explicit": False,
    }
    source = {
        "title": src_title,
        "artists": artists,
        "duration": cand["duration"],
        "album": None,
        "cover": cand["thumbnail"],
    }
    return {"source": source, "candidate": cand}


async def video_info(video_id: str) -> dict:
    return await asyncio.to_thread(video_info_sync, video_id)
