"""
Hunter — Otomatik Sanatçı Tarama Modülü

YouTube Data API v3 aracılığıyla ethno-tech hashtagleri tarar;
bulunan videoların yorumlarını mevcut analiz pipeline'ına gönderir.

Hashtag kategorileri:
  INSTRUMENT  — enstrüman bazlı (kanun, oud, ney…)
  VIBE        — tür/sahne bazlı (organichouse, deserttech…)
  INSTITUTION — küratör/venue bazlı (boilerroom, kexp…)

Smart Query: Her kategoriye özel kalite filtresi terimi
  eklenerek alakasız videolar elenir, API birimi verimli kullanılır.

Maliyet optimizasyonu:
  - videoCategoryId=10 (Müzik) filtresi → sadece müzik kategorisi
  - Daha önce taranan video_id'ler DB'den kontrol edilerek atlanır
  - Yorum sayısı < MIN_COMMENTS olan videolar LLM'e gönderilmez
  - Her hashtag için verimlilik istatistiği (avg_london_score) kaydedilir
  - Tarama sonu özeti Telegram'a gönderilir
"""

import logging
import time

log = logging.getLogger("Hunter")


# ── Smart Hashtag Engine ──────────────────────────────────────
HASHTAG_CATEGORIES: dict[str, list[str]] = {
    # Geleneksel/etnik enstrüman etiketleri
    "INSTRUMENT": [
        "kanun", "oudplayer", "neymusic", "darbuka",
        "sazmusic", "baglama", "bendir", "duduk",
    ],
    # Tür ve sahne etiketleri
    "VIBE": [
        "organichouse", "anatolianpsych", "deserttech", "ethnotech",
        "worldelectronica", "neosufihouse", "darkfolkelectronic",
        "afrohouse", "bosphorus",
    ],
    # Küratör, venue ve yayın platformu etiketleri
    "INSTITUTION": [
        "boilerroom", "kexp", "innervisions",
        "fabriclondon", "residentadvisor", "crosstownrebels",
    ],
}

# Kategori başına YouTube sorgusuna eklenen kalite filtresi
# Smart Query örn: "#kanun live performance", "#organichouse set"
_CATEGORY_QUALIFIER: dict[str, str] = {
    "INSTRUMENT": "live performance",  # enstrüman canlı performansını hedefler
    "VIBE":       "set",               # DJ/live set içeriğini öne çıkarır
    "INSTITUTION": "",                 # venue/kurum etiketleri zaten spesifiktir
}

# DEFAULT_HASHTAGS: mevcut UI multiselect'inin beklediği düz liste
DEFAULT_HASHTAGS: list[str] = [
    h for cat in HASHTAG_CATEGORIES.values() for h in cat
]

MIN_COMMENTS = 5    # Bu eşiğin altındaki videolar LLM analizine gönderilmez
YT_SLEEP     = 0.4  # YouTube API istekleri arası bekleme (saniye)
IG_SLEEP     = 2.0  # Instagram scraping arası bekleme (saniye)


def _category_of(tag: str) -> str:
    """Bir hashtag'in hangi kategoriye ait olduğunu döner."""
    for cat, tags in HASHTAG_CATEGORIES.items():
        if tag in tags:
            return cat
    return "VIBE"   # bilinmeyen etiketleri VIBE olarak işle


def _smart_query(tag: str, category: str) -> str:
    """Kategoriye göre kalite filtresi eklenmiş YouTube arama sorgusu oluşturur."""
    qualifier = _CATEGORY_QUALIFIER.get(category, "")
    return f"#{tag} {qualifier}".strip() if qualifier else f"#{tag}"


# ── Yardımcı: DB'deki bilinen sanatçılar ──────────────────────
def _known_artists() -> set[str]:
    from modules.database import load_all
    return {r["artist"].lower() for r in load_all()}


# ── YouTube hashtag tarama ────────────────────────────────────
def scan_youtube_hashtag(tag: str, max_results: int = 5) -> list[dict]:
    """
    YouTube'da Smart Query ile arama yapar.
    Returns: [{"video_id": str, "video_url": str, "title": str, "channel": str}]
    Maliyet: 100 API unit / çağrı
    """
    from googleapiclient.discovery import build
    from modules.config import get_secret

    key = get_secret("YOUTUBE_API_KEY")
    if not key:
        raise ValueError("YOUTUBE_API_KEY bulunamadı.")

    category = _category_of(tag)
    query    = _smart_query(tag, category)
    log.debug(f"  Smart Query: '{query}' (kategori: {category})")

    youtube = build("youtube", "v3", developerKey=key, cache_discovery=False)
    resp = youtube.search().list(
        q=query,
        type="video",
        part="snippet",
        maxResults=max_results,
        # videoCategoryId=10: sadece 'Müzik' kategorisindeki videolar (kategori 10 = Music)
        # Vlog, konuşma ve alakasız içerikleri filtreler; API birimini verimli kullanır.
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
    Skip Logic  : video_id DB'de kayıtlıysa atlanır.
    Min Threshold: yorum < MIN_COMMENTS ise LLM'e gönderilmez.
    Returns: {"artist": str, "scores": dict} veya None (atlandı)
    """
    from modules.database import is_video_scanned, mark_video_scanned
    from modules.youtube_client import fetch_youtube_data, split_by_date
    from modules.report import process_and_save

    if is_video_scanned(video_id):
        log.info(f"  Atlandı (DB kayıtlı video): {video_id}")
        return None

    try:
        safe_name, comments, _ = fetch_youtube_data(video_url)

        if safe_name.lower() in _known_artists():
            log.info(f"  Atlandı (sanatçı DB'de): {safe_name}")
            mark_video_scanned(video_id, artist_name=safe_name,
                               was_analyzed=False, skip_reason="artist_exists")
            return None

        if len(comments) < MIN_COMMENTS:
            log.info(f"  Atlandı (yorum {len(comments)} < {MIN_COMMENTS}): {safe_name}")
            mark_video_scanned(video_id, artist_name=safe_name,
                               was_analyzed=False, skip_reason="low_comments")
            return None

        recent_str, older_str = split_by_date(comments)
        raw_comments = "\n".join(f"- {c['text']}" for c in comments)
        result = process_and_save(safe_name, raw_comments, recent_str, older_str)
        london = result["scores"].get("Londra Uyumluluğu", 0)
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
    from modules.alerts import send_telegram

    flag = "🚨" if stats.get("analyzed", 0) > 0 else "📊"
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
    msg += (
        f"✅ <b>{stats['analyzed']} yeni sanatçı veritabanına eklendi!</b>"
        if stats["analyzed"] > 0
        else "ℹ️ Bu taramada yeni potansiyel bulunamadı."
    )
    send_telegram(msg)


# ── Ana tarama döngüsü ────────────────────────────────────────
def run_hunter(
    hashtags: list[str] | None = None,
    max_yt_per_tag: int = 3,
    use_instagram: bool = False,
    progress_cb=None,       # fn(msg: str) → UI için canlı log
) -> dict:
    """
    Hashtagleri tarar, yeni sanatçıları analiz eder.
    Her hashtag için verimlilik istatistiği (avg_london_score) DB'ye kaydedilir.
    Returns: {"scanned": int, "analyzed": int, "skipped": int,
              "errors": int, "ig_leads": list[dict]}
    """
    from modules.database import record_hashtag_stats

    tags  = hashtags or DEFAULT_HASHTAGS
    stats = {"scanned": 0, "analyzed": 0, "skipped": 0, "errors": 0, "ig_leads": []}

    def _log(msg: str):
        log.info(msg)
        if progress_cb:
            progress_cb(msg)

    _log(f"Hunter başladı: {len(tags)} hashtag | YT max {max_yt_per_tag}/tag")

    for tag in tags:
        category      = _category_of(tag)
        tag_analyzed  = 0
        tag_score_sum = 0.0

        _log(f"── #{tag} [{category}] → Smart Query: '{_smart_query(tag, category)}'")

        # YouTube
        try:
            videos = scan_youtube_hashtag(tag, max_results=max_yt_per_tag)
            stats["scanned"] += len(videos)
            _log(f"   {len(videos)} video bulundu")

            for v in videos:
                result = _analyze_video(v["video_id"], v["video_url"])
                if result:
                    london = result["scores"].get("Londra Uyumluluğu", 0)
                    tag_analyzed  += 1
                    tag_score_sum += london
                    stats["analyzed"] += 1
                else:
                    stats["skipped"] += 1
                time.sleep(YT_SLEEP)

        except Exception as e:
            log.error(f"YouTube [{tag}] hatası: {e}")
            stats["errors"] += 1

        # Hashtag verimlilik istatistiği kaydet
        avg_score = tag_score_sum / tag_analyzed if tag_analyzed else 0.0
        try:
            record_hashtag_stats(
                hashtag=tag,
                category=category,
                videos_found=len(videos) if "videos" in dir() else 0,
                analyzed=tag_analyzed,
                avg_london_score=avg_score,
            )
        except Exception:
            pass

        # Instagram (opsiyonel, sadece lead keşfi)
        if use_instagram:
            try:
                leads = scan_instagram_hashtag(tag, max_posts=8)
                stats["ig_leads"].extend(leads)
                _log(f"   Instagram: {len(leads)} potansiyel hesap")
            except Exception as e:
                log.error(f"Instagram [{tag}] hatası: {e}")

        time.sleep(1.0)

    _log(
        f"Hunter tamamlandı → "
        f"{stats['analyzed']} analiz | "
        f"{stats['skipped']} atlandı | "
        f"{stats['errors']} hata"
    )

    try:
        _send_summary(stats, tags)
    except Exception as e:
        log.warning(f"Telegram özet gönderilemedi: {e}")

    return stats
