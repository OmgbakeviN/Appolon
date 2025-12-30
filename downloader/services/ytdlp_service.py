from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from yt_dlp import YoutubeDL


YOUTUBE_HOSTS = {"www.youtube.com", "youtube.com", "m.youtube.com", "youtu.be"}


def is_allowed_youtube_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    return host in YOUTUBE_HOSTS


@dataclass
class FormatChoice:
    format_id: str
    label: str
    ext: str


def extract_video_info(url: str) -> dict[str, Any]:
    """
    Récupère les métadonnées + la liste de formats sans télécharger.
    """
    ydl_opts = {
        "quiet": True,
        "noplaylist": True,
        "skip_download": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info


def build_audio_choices(info: dict[str, Any]) -> list[FormatChoice]:
    """
    Construit une liste de formats audio-only triés par bitrate (abr).
    """
    formats = info.get("formats") or []
    audio_only = []

    for f in formats:
        if f.get("vcodec") == "none" and f.get("acodec") not in (None, "none"):
            abr = f.get("abr") or 0
            ext = f.get("ext") or ""
            acodec = f.get("acodec") or ""
            fid = str(f.get("format_id") or "")

            label = f"{int(abr)} kbps — {ext} ({acodec})" if abr else f"{ext} ({acodec})"
            audio_only.append((abr, FormatChoice(format_id=fid, label=label, ext=ext)))

    audio_only.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in audio_only]


def build_video_choices(info: dict[str, Any]) -> list[FormatChoice]:
    """
    Construit une liste “courte” de qualités vidéo (ex: 360p, 480p, 720p, 1080p...)
    On choisit un format par hauteur (height) en privilégiant :
    1) mp4
    2) format qui contient déjà l’audio (progressif)
    3) meilleur débit (tbr)
    """
    formats = info.get("formats") or []

    candidates = []
    for f in formats:
        if f.get("vcodec") in (None, "none"):
            continue
        height = f.get("height")
        if not height:
            continue

        ext = f.get("ext") or ""
        fid = str(f.get("format_id") or "")
        has_audio = f.get("acodec") not in (None, "none")
        tbr = f.get("tbr") or 0

        candidates.append({
            "height": int(height),
            "ext": ext,
            "format_id": fid,
            "has_audio": has_audio,
            "tbr": float(tbr),
        })

    best_by_height = {}
    for c in candidates:
        h = c["height"]
        if h not in best_by_height:
            best_by_height[h] = c
            continue

        current = best_by_height[h]

        def score(x: dict) -> tuple:
            # (préférer mp4), (préférer progressif), (débit)
            return (
                1 if x["ext"] == "mp4" else 0,
                1 if x["has_audio"] else 0,
                x["tbr"],
            )

        if score(c) > score(current):
            best_by_height[h] = c

    choices = []
    for h in sorted(best_by_height.keys()):
        c = best_by_height[h]
        suffix = " (audio inclus)" if c["has_audio"] else " (fusion audio)"
        label = f"{h}p — {c['ext']}{suffix}"
        choices.append(FormatChoice(format_id=c["format_id"], label=label, ext=c["ext"]))

    return choices
