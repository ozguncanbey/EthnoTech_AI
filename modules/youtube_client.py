import os
import re
from dotenv import load_dotenv

load_dotenv()


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
    title = video_resp["items"][0]["snippet"]["title"]
    safe_name = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_")[:60]

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
            text = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            text = text.strip().replace("\n", " ")
            if text:
                comments.append(f"- {text}")
        req = youtube.commentThreads().list_next(req, resp)

    if not comments:
        raise ValueError("Videodan yorum çekilemedi (yorumlar kapalı olabilir).")

    return safe_name, "\n".join(comments[:100]), title
