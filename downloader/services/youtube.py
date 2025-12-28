import requests
from django.conf import settings


YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


def search_youtube_videos(query: str, page_token: str | None = None, max_results: int = 12) -> dict:
    """
    Appelle YouTube Data API v3 (search.list) pour récupérer une liste de vidéos.
    Retourne: items + next/prev page token.
    """
    if not settings.YOUTUBE_API_KEY:
        raise RuntimeError("YOUTUBE_API_KEY manquante. Ajoute-la dans ton .env puis relance le serveur.")

    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "key": settings.YOUTUBE_API_KEY,
        "safeSearch": "moderate",
    }
    if page_token:
        params["pageToken"] = page_token

    response = requests.get(YOUTUBE_SEARCH_URL, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    results = []
    for item in data.get("items", []):
        video_id = (item.get("id") or {}).get("videoId")
        if not video_id:
            continue

        snippet = item.get("snippet") or {}
        thumbs = snippet.get("thumbnails") or {}
        thumb = thumbs.get("medium") or thumbs.get("high") or thumbs.get("default") or {}

        results.append({
            "video_id": video_id,
            "title": snippet.get("title") or "",
            "channel_title": snippet.get("channelTitle") or "",
            "published_at": snippet.get("publishedAt") or "",
            "thumbnail_url": thumb.get("url") or "",
        })

    return {
        "items": results,
        "next_page_token": data.get("nextPageToken"),
        "prev_page_token": data.get("prevPageToken"),
    }
