import os
import re
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()


def _extract_artist(title: str, channel: str) -> str:
    """
    Video başlığından sanatçı adını çıkarır.
    Öncelik: başlıktaki 'Sanatçı - Şarkı' kalıbı → channel adı → başlığın tamamı.
    """
    # "Sanatçı - Şarkı", "Sanatçı | Şarkı", "Sanatçı: Şarkı" kalıpları
    for sep in (" - ", " – ", " | ", ": "):
        if sep in title:
            candidate = title.split(sep)[0].strip()
            # Makul uzunlukta ve şarkı/klip sözcükleri içermiyorsa kullan
            noise = {"official", "video", "clip", "lyrics", "audio",
                     "ft", "feat", "prod", "remix", "vevo", "presents"}
            if 2 <= len(candidate) <= 50 and not any(
                w.lower() in noise for w in candidate.split()
            ):
                return candidate

    # Kanal adı varsa ve makul görünüyorsa kullan
    if channel and len(channel) <= 50 and "VEVO" not in channel.upper():
        return channel

    return title  # fallback: başlığın tamamı


def extract_video_id(url: str) -> str:
    m = re.search(r"(?:v=|/v/|youtu\.be/|/embed/)([a-zA-Z0-9_-]{11})", url)
    if not m:
        raise ValueError(
            "Geçersiz YouTube URL'si. "
            "Desteklenen formatlar: youtu.be/..., youtube.com/watch?v=..."
        )
    return m.group(1)


def fetch_youtube_data(url: str) -> tuple:
    from googleapiclient.discovery import build

    yt_key = os.getenv("YOUTUBE_API_KEY")
    if not yt_key:
        raise ValueError("YOUTUBE_API_KEY .env dosyasında bulunamadı.")

    video_id = extract_video_id(url)
    youtube = build("youtube", "v3", developerKey=yt_key, cache_discovery=False)

    video_resp = youtube.videos().list(part="snippet", id=video_id).execute()
    if not video_resp.get("items"):
        raise ValueError("Video bulunamadı veya erişilemiyor.")
    snippet = video_resp["items"][0]["snippet"]
    title = snippet["title"]
    channel = snippet.get("channelTitle", "")

    artist_name = _extract_artist(title, channel)
    safe_name = re.sub(r"[^\w\s-]", "", artist_name).strip().replace(" ", "_")[:60]

    comments = []
    req = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=100,
        order="relevance",
        textFormat="plainText",
    )
    while req and len(comments) < 100:
        resp = req.execute()
        for item in resp.get("items", []):
            snippet = item["snippet"]["topLevelComment"]["snippet"]
            text = snippet["textDisplay"].strip().replace("\n", " ")
            date = snippet.get("publishedAt", "")
            if text:
                comments.append({"text": text, "date": date})
        req = youtube.commentThreads().list_next(req, resp)

    if not comments:
        raise ValueError("Videodan yorum çekilemedi (yorumlar kapalı olabilir).")

    return safe_name, comments[:100], title


def split_by_date(comments: list) -> tuple:
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    recent, older = [], []
    for c in comments:
        try:
            dt = datetime.fromisoformat(c["date"].replace("Z", "+00:00"))
            bucket = recent if dt >= cutoff else older
        except (ValueError, KeyError):
            bucket = older
        bucket.append(f"- {c['text']}")

    return "\n".join(recent), "\n".join(older)
