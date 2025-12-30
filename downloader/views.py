import os
import shutil
import tempfile
from urllib.parse import urlencode
from user_agents import parse as parse_ua 

from django.db.models import Q
from django.http import FileResponse
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from django.urls import reverse

from .models import DownloadEvent
from .forms import HomeForm, SignupForm
from .services.youtube import search_youtube_videos
from .services.ytdlp_service import (
    is_allowed_youtube_url,
    extract_video_info,
    build_audio_choices,
    build_video_choices,
)
from yt_dlp import YoutubeDL


def home(request):
    form = HomeForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        query = (form.cleaned_data.get("query") or "").strip()
        url = (form.cleaned_data.get("url") or "").strip()

        if query:
            qs = urlencode({"q": query})
            return redirect(f"{reverse('downloader:search')}?{qs}")

        if url:
            qs = urlencode({"url": url})
            return redirect(f"{reverse('downloader:options')}?{qs}")

    return render(request, "downloader/home.html", {"form": form})


def search(request):
    q = (request.GET.get("q") or "").strip()
    page = request.GET.get("page")

    if not q:
        return redirect("downloader:home")

    error = None
    payload = {"items": [], "next_page_token": None, "prev_page_token": None}

    try:
        payload = search_youtube_videos(query=q, page_token=page, max_results=12)
    except Exception as exc:
        error = str(exc)

    context = {
        "q": q,
        "items": payload["items"],
        "next_page_token": payload["next_page_token"],
        "prev_page_token": payload["prev_page_token"],
        "error": error,
    }
    return render(request, "downloader/search.html", context)


def select_video(request, video_id: str):
    """
    Quand l'utilisateur choisit une vidéo depuis la recherche,
    on construit son URL puis on redirige vers la page options (étape 3).
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    qs = urlencode({"url": url})
    return redirect(f"{reverse('downloader:options')}?{qs}")


def options(request):
    """
    Étape 3:
    - on reçoit une URL YouTube
    - on extrait les formats avec yt-dlp
    - on affiche 2 dropdowns (audio / video)
    """
    url = (request.GET.get("url") or "").strip()
    if not url:
        return redirect("downloader:home")

    if not is_allowed_youtube_url(url):
        return render(request, "downloader/options.html", {"error": "URL non supportée (YouTube uniquement).", "url": url})

    error = None
    info = None
    audio_choices = []
    video_choices = []

    try:
        info = extract_video_info(url)
        audio_choices = build_audio_choices(info)
        video_choices = build_video_choices(info)
    except Exception as exc:
        # error = str(exc)
        msg = str(exc)
        if "Sign in to confirm you’re not a bot" in msg or "confirm you're not a bot" in msg:
            error = (
                "YouTube bloque cette vidéo depuis notre serveur (vérification anti-bot). "
                "Essaie une autre vidéo. "
                "Pour certaines vidéos, le téléchargement peut nécessiter une connexion."
            )
        else:
            error = msg

    context = {
        "url": url,
        "error": error,
        "info": info,
        "audio_choices": audio_choices,
        "video_choices": video_choices,
    }
    return render(request, "downloader/options.html", context)

def _get_client_ip(request) -> str | None:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")

def download_media(request):
    """
    POST:
    - url
    - mode: audio|video
    - format_id: id du format choisi
    Télécharge sur un dossier temporaire puis renvoie le fichier au navigateur.
    """
    if request.method != "POST":
        return redirect("downloader:home")

    url = (request.POST.get("url") or "").strip()
    mode = (request.POST.get("mode") or "").strip()
    format_id = (request.POST.get("format_id") or "").strip()

    if not url or mode not in ("audio", "video") or not format_id:
        return redirect("downloader:home")

    if not is_allowed_youtube_url(url):
        return redirect(f"{reverse('downloader:options')}?{urlencode({'url': url})}")

    # Parse user agent (navigateur / OS / device)
    ua_str = request.META.get("HTTP_USER_AGENT", "")
    ua = parse_ua(ua_str)
    browser = f"{ua.browser.family} {ua.browser.version_string}".strip()
    os_name = f"{ua.os.family} {ua.os.version_string}".strip()
    device = ua.device.family or ""
    ip = _get_client_ip(request)

    # Re-extract info pour récupérer titre + label exact du format (fiable côté serveur)
    info = extract_video_info(url)
    title = info.get("title") or ""
    video_id = info.get("id") or ""

    chosen_format = None
    for f in (info.get("formats") or []):
        if str(f.get("format_id")) == format_id:
            chosen_format = f
            break

    ext = (chosen_format.get("ext") if chosen_format else "") or ""
    quality_label = ""

    if mode == "audio":
        abr = (chosen_format.get("abr") if chosen_format else None) or 0
        acodec = (chosen_format.get("acodec") if chosen_format else "") or ""
        quality_label = f"{int(abr)} kbps — {ext} ({acodec})" if abr else f"{ext} ({acodec})"
        ytdlp_format = format_id
    else:
        height = (chosen_format.get("height") if chosen_format else None) or ""
        has_audio = (chosen_format.get("acodec") if chosen_format else "none") not in (None, "none")
        suffix = "audio inclus" if has_audio else "fusion audio"
        quality_label = f"{height}p — {ext} ({suffix})" if height else f"{ext} ({suffix})"

        # Si la vidéo choisie n’a pas d’audio, on fusionne automatiquement avec le meilleur audio.
        # Cela nécessite FFmpeg.
        ytdlp_format = f"{format_id}+bestaudio/best"

    tmpdir = tempfile.mkdtemp(prefix="ytdlp_")

    try:
        # On force un nom stable pour retrouver le fichier facilement
        outtmpl = os.path.join(tmpdir, "%(title).150s [%(id)s].%(ext)s")

        ydl_opts = {
            "quiet": True,
            "noplaylist": True,
            "format": ytdlp_format,
            "outtmpl": outtmpl,
            "merge_output_format": "mp4" if mode == "video" else None,
        }

        # Retire la clé si None (yt-dlp n’aime pas certaines valeurs)
        if ydl_opts["merge_output_format"] is None:
            ydl_opts.pop("merge_output_format")

        with YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)

        # On récupère le fichier final téléchargé (hors .part)
        files = []
        for name in os.listdir(tmpdir):
            if name.endswith(".part"):
                continue
            files.append(os.path.join(tmpdir, name))

        if not files:
            return render(request, "downloader/options.html", {
                "url": url,
                "error": "Téléchargement terminé mais fichier introuvable. Vérifie FFmpeg si tu as choisi une qualité nécessitant une fusion.",
                "info": info,
                "audio_choices": [],
                "video_choices": [],
            })

        # Prend le fichier le plus gros (souvent le bon pour vidéo)
        filepath = max(files, key=lambda p: os.path.getsize(p))
        filename = os.path.basename(filepath)

        # Sauvegarder l'évènement
        DownloadEvent.objects.create(
            user=request.user if request.user.is_authenticated else None,
            video_url=url,
            video_id=str(video_id),
            title=title,
            mode=mode,
            format_id=format_id,
            ext=ext,
            quality_label=quality_label,
            ip_address=ip,
            user_agent=ua_str,
            browser=browser,
            os=os_name,
            device=device,
        )

        return FileResponse(open(filepath, "rb"), as_attachment=True, filename=filename)

    finally:
        # Pour un portfolio c’est OK, mais en prod il faut un nettoyage asynchrone.
        # Ici on supprime le dossier temporaire immédiatement.
        # (Selon l’OS, le fichier peut être encore ouvert : si tu vois des erreurs, on ajustera.)
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass

@login_required
def history(request):
    """
    Historique des téléchargements de l'utilisateur connecté.
    Filtres via GET:
    - q: recherche texte (title/video_id/url)
    - mode: audio|video|all
    - ip: ip exacte
    """
    qs = DownloadEvent.objects.filter(user=request.user)

    q = (request.GET.get("q") or "").strip()
    mode = (request.GET.get("mode") or "all").strip()
    ip = (request.GET.get("ip") or "").strip()

    if q:
        qs = qs.filter(
            Q(title__icontains=q) |
            Q(video_id__icontains=q) |
            Q(video_url__icontains=q) |
            Q(quality_label__icontains=q)
        )

    if mode in ("audio", "video"):
        qs = qs.filter(mode=mode)

    if ip:
        qs = qs.filter(ip_address=ip)

    paginator = Paginator(qs, 12)  # 12 lignes par page
    page_number = request.GET.get("page") or 1
    page_obj = paginator.get_page(page_number)

    return render(request, "downloader/history.html", {
        "page_obj": page_obj,
        "q": q,
        "mode": mode,
        "ip": ip,
    })

def signup(request):
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("downloader:home")
    return render(request, "registration/signup.html", {"form": form})

