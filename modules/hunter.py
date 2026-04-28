"""
Hunter — Otomatik Sanatçı Tarama Modülü

YouTube Data API v3 aracılığıyla ethno-tech hashtagleri tarar;
bulunan videoların yorumlarını mevcut analiz pipeline'ına gönderir.

Instagram desteği: instaloader (API'siz scraping, hız sınırlı).
Instagram taraması sadece potansiyel kullanıcı adı listesi döner;
tam analiz için sanatçının YouTube URL'si gerekir.

Maliyet optimizasyonu:
  - YouTube search.list: 100 unit/istek (10.000 ücretsiz/gün → ~100 tarama/gün)
  - videoCategoryId=10 (Müzik) filtresi alakasız videoları eliyor
  - Daha önce taranan video_id'ler DB'den kontrol edilerek atlanır
  - Yorum sayısı < MIN_COMMENTS olan videolar LLM'e gönderilmez
  - Tarama sonu özeti Telegram'a gönderilir
"""

import logging
import time

log = logging.getLogger("Hunter")

# ── Taranacak hashtagler (varsayılan) ─────────────────────────
DEFAULT_HASHTAGS = [
    "organichouse",
    "anatolianpsych",
    "deserttech",
    "afrohouse",
    "ethnotech",
    "worldelectronica",
    "neosufihouse",
    "anatolianmusic",
    "bosphorus",
]

MIN_COMMENTS = 5    # Bu eşiğin altındaki videolar LLM analizine gönderilmez
YT_SLEEP     = 0.4  # YouTube API istekleri arası bekleme (saniye)
IG_SLEEP     = 2.0  # Instagram scraping arası bekleme (saniye)


# ── Yardımcı: DB'deki bilinen sanatçılar ──────────────────────
def _known_artists() -> set[str]:
    from modules.database import load_all
    return {r["artist"].lower() for r in load_all()}


# ── YouTube hashtag tarama ────────────────────────────────────
def scan_youtube_hashtag(tag: str, max_results: int = 5) -> list[dict]:
    """
    YouTube'da '#tag' araması yapar.
    Returns: [{"video_id": str, "video_url": str, "title": str, "channel": str}]
    Maliyet: 100 API unit / çağrı
    """
    from googleapiclient.discovery import build
    from modules.config import get_secret

    key = get_secret("YOUTUBE_API_KEY")
    if not key:
        raise ValueError("YOUTUBE_API_KEY bulunamadı.")

    youtube = build("youtube", "v3", developerKey=key, cache_discovery=False)
    resp = youtube.search().list(
        q=f"#{tag}",
        type="video",
        part="snippet",
        maxResults=max_results,
        # videoCategoryId=10: sadece 'Müzik' kategorisindeki videolar (kategori 10 = Music)
        # Alakasız konuşma/vlog videolarını filtreler, API birimini verimli kullanır.
        videoCategoryId="10",
        order="relevance",
    ).execute()

    results = []
    for item in resp.get("items", []):
        vid_id = item["id"].get("videoId")
        if not vid_id:
            continue
        snippet = item["snippet"]
        results.append({
            "video_id":  vid_id,
            "video_url": f"https://www.youtube.com/watch?v={vid_id}",
            "title":     snippet.get("title", ""),
            "channel":   snippet.get("channelTitle", ""),
        })
    return results


# ── Instagram hashtag tarama (opsiyonel) ─────────────────────
def scan_instagram_hashtag(tag: str, max_posts: int = 10) -> list[dict]:
    """
    instaloader ile Instagram hashtag taraması.
    Login gerekmez ancak hız limitlerine tabidir.
    Returns: [{"username": str, "post_url": str, "caption_preview": str}]
    """
    try:
        import instaloader
    except ImportError:
        log.warning("instaloader kurulu değil: pip install instaloader")
        return []

    L = instaloader.Instaloader(
        quiet=True,
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
    )

    results = []
    try:
        hashtag = instaloader.Hashtag.from_name(L.context, tag)
        for i, post in enumerate(hashtag.get_posts()):
            if i >= max_posts:
                break
            results.append({
                "username":        post.owner_username,
                "post_url":        f"https://www.instagram.com/p/{post.shortcode}/",
                "caption_preview": (post.caption or "")[:200].replace("\n", " "),
            })
            time.sleep(IG_SLEEP)
    except Exception as e:
        log.warning(f"Instagram [{tag}] tarama hatası: {e}")

    return results


# ── Tek video analiz ──────────────────────────────────────────
def _analyze_video(video_id: str, video_url: str) -> dict | None:
    """
    Bir YouTube videosunun yorumlarını çekip analiz eder.
    Önce video_id DB'de kayıtlı mı diye kontrol eder (Skip Logic).
    Yorum sayısı MIN_COMMENTS altındaysa LLM'e gönderilmez (Minimum Threshold).
    Returns: {"artist": str, "scores": dict} veya None (atlandı)
    """
    from modules.database import is_video_scanned, mark_video_scanned
    from modules.youtube_client import fetch_youtube_data, split_by_date
    from modules.report import process_and_save

    # ── 1. Skip Logic: daha önce tarandı mı? ──────────────────
    if is_video_scanned(video_id):
        log.info(f"  Atlandı (DB'de kayıtlı video): {video_id}")
        return None

    try:
        safe_name, comments, _ = fetch_youtube_data(video_url)

        # ── 2. Sanatçı zaten analiz edilmiş mi? ───────────────
        if safe_name.lower() in _known_artists():
            log.info(f"  Atlandı (sanatçı DB'de): {safe_name}")
            mark_video_scanned(video_id, artist_name=safe_name,
                               was_analyzed=False, skip_reason="artist_exists")
            return None

        # ── 3. Minimum Threshold: yeterli yorum var mı? ───────
        if len(comments) < MIN_COMMENTS:
            log.info(f"  Atlandı (yorum {len(comments)} < {MIN_COMMENTS}): {safe_name}")
            mark_video_scanned(video_id, artist_name=safe_name,
                               was_analyzed=False, skip_reason="low_comments")
            return None

        recent_str, older_str = split_by_date(comments)
        raw_comments = "\n".join(f"- {c['text']}" for c in comments)
        result = process_and_save(safe_name, raw_comments, recent_str, older_str)
        london = result["scores"].get("Londra Uyumluluğu", "?")
        log.info(f"  ✓ Analiz: {safe_name} — Londra {london}/10")

        mark_video_scanned(video_id, artist_name=safe_name,
                           was_analyzed=True, skip_reason=None)
        return result

    except Exception as e:
        log.warning(f"  Hata ({video_url}): {e}")
        mark_video_scanned(video_id, was_analyzed=False, skip_reason=f"error: {e}")
        return None


# ── Telegram özet bildirimi ───────────────────────────────────
def _send_summary(stats: dict, hashtags: list[str]) -> None:
    """Tarama tamamlandığında Telegram'a günlük özet gönderir."""
    from modules.alerts import send_telegram

    potentials = stats.get("analyzed", 0)
    flag = "🚨" if potentials > 0 else "📊"
    msg = (
        f"{flag} <b>Hunter Tarama Özeti</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔍 Taranan Hashtagler: {len(hashtags)}\n"
        f"📹 Bulunan Video: {stats['scanned']}\n"
        f"⚡ LLM Analizi Yapılan: {stats['analyzed']}\n"
        f"⏭ Elenen (skip): {stats['skipped']}\n"
        f"❌ Hata: {stats['errors']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
    )
    if potentials > 0:
        msg += f"✅ <b>{potentials} yeni sanatçı veritabanına eklendi!</b>"
    else:
        msg += "ℹ️ Bu taramada yeni potansiyel bulunamadı."

    send_telegram(msg)


# ── Ana tarama döngüsü ────────────────────────────────────────
def run_hunter(
    hashtags: list[str] | None = None,
    max_yt_per_tag: int = 3,
    use_instagram: bool = False,
    progress_cb=None,           # opsiyonel: fn(msg: str) → UI için canlı log
) -> dict:
    """
    Hashtagleri tarar, yeni sanatçıları analiz eder.
    Returns: {"scanned": int, "analyzed": int, "skipped": int,
              "errors": int, "ig_leads": list[dict]}
    """
    tags  = hashtags or DEFAULT_HASHTAGS
    stats = {"scanned": 0, "analyzed": 0, "skipped": 0, "errors": 0, "ig_leads": []}

    def _log(msg: str):
        log.info(msg)
        if progress_cb:
            progress_cb(msg)

    _log(f"Hunter başladı: {len(tags)} hashtag | YT max {max_yt_per_tag}/tag")

    for tag in tags:
        _log(f"── #{tag}")

        # YouTube
        try:
            videos = scan_youtube_hashtag(tag, max_results=max_yt_per_tag)
            stats["scanned"] += len(videos)
            _log(f"   {len(videos)} video bulundu")

            for v in videos:
                result = _analyze_video(v["video_id"], v["video_url"])
                if result:
                    stats["analyzed"] += 1
                else:
                    stats["skipped"] += 1
                time.sleep(YT_SLEEP)

        except Exception as e:
            log.error(f"YouTube [{tag}] hatası: {e}")
            stats["errors"] += 1

        # Instagram (opsiyonel, sadece lead keşfi)
        if use_instagram:
            try:
                leads = scan_instagram_hashtag(tag, max_posts=8)
                stats["ig_leads"].extend(leads)
                _log(f"   Instagram: {len(leads)} potansiyel hesap")
            except Exception as e:
                log.error(f"Instagram [{tag}] hatası: {e}")

        time.sleep(1.0)  # tag'lar arası nefes

    _log(
        f"Hunter tamamlandı → "
        f"{stats['analyzed']} analiz | "
        f"{stats['skipped']} atlandı | "
        f"{stats['errors']} hata"
    )

    # ── Summary Notification ──────────────────────────────────
    try:
        _send_summary(stats, tags)
    except Exception as e:
        log.warning(f"Telegram özet gönderilemedi: {e}")

    return stats
