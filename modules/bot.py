"""
Hunter Bot — Otomatik Takip Modülü

Kullanım:
  python3 modules/bot.py            → 24 saatte bir çalışır (bloklayan)
  python3 modules/bot.py --once     → tek seferlik çalışır, çıkar
  python3 modules/bot.py --hours 6  → 6 saatte bir çalışır
"""
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Kök dizini Python yoluna ekle (modules/ içinden çalıştırıldığında)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.alerts import process_signals
from modules.database import get_latest_scores, get_watchlist, update_watchlist_check
from modules.report import process_and_save
from modules.youtube_client import fetch_youtube_data, split_by_date

# ── Log sistemi ───────────────────────────────────────────────
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_DIR / "bot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("HunterBot")


# ── Tek sanatçı kontrolü ──────────────────────────────────────
def check_artist(artist_name: str, youtube_url: str, last_check: str | None) -> bool:
    """Sanatçıyı kontrol et, yeni yorum varsa analizi güncelle. True → güncellendi."""
    log.info(f"Kontrol: {artist_name}")
    try:
        prev_scores = get_latest_scores(artist_name)
        _, comments_list, _ = fetch_youtube_data(youtube_url)

        if last_check:
            cutoff = datetime.fromisoformat(last_check)
            if cutoff.tzinfo is None:
                cutoff = cutoff.replace(tzinfo=timezone.utc)

            new = [
                c for c in comments_list
                if c.get("date") and
                datetime.fromisoformat(c["date"].replace("Z", "+00:00")) > cutoff
            ]
            if not new:
                log.info(f"  → Yeni yorum yok, atlandı.")
                return False
            log.info(f"  → {len(new)} yeni yorum bulundu, analiz güncelleniyor...")
        else:
            log.info(f"  → İlk kontrol, analiz başlatılıyor...")

        recent_str, older_str = split_by_date(comments_list)
        raw_comments = "\n".join(f"- {c['text']}" for c in comments_list)
        result = process_and_save(artist_name, raw_comments, recent_str, older_str)
        update_watchlist_check(youtube_url, datetime.now(timezone.utc).isoformat(timespec="seconds"))

        signals = process_signals(artist_name, result["scores"], prev_scores)
        if signals:
            log.info(f"  → {len(signals)} kritik sinyal tetiklendi!")
        else:
            # Alarm koşulu olmasa bile rutin güncelleme bildirimi gönder
            s = result["scores"]
            display = artist_name.replace("_", " ")
            from modules.alerts import send_telegram
            send_telegram(
                f"🔄 <b>Rapor Güncellendi</b>\n\n"
                f"👤 {display}\n"
                f"🎯 Londra: <b>{s['Londra Uyumluluğu']}/10</b>  "
                f"⚡ Karizma: {s['Karizma']}  "
                f"🌀 Gizem: {s['Gizem']}  "
                f"🎤 Sahne: {s['Sahne Enerjisi']}\n"
                f"<i>Hunter Bot tarafından güncellendi.</i>"
            )

        log.info(f"  → Rapor güncellendi: {artist_name}")
        return True

    except Exception as e:
        log.error(f"  → Hata ({artist_name}): {e}")
        return False


# ── Ana döngü ─────────────────────────────────────────────────
def run_bot() -> dict:
    log.info("=" * 55)
    log.info("Hunter Bot çalışıyor")
    log.info("=" * 55)

    watchlist = get_watchlist()
    if not watchlist:
        log.info("Takip listesi boş. app.py üzerinden sanatçı ekleyin.")
        return {"total": 0, "updated": 0}

    log.info(f"Takip listesi: {len(watchlist)} sanatçı")
    updated = 0
    for entry in watchlist:
        if check_artist(entry["artist_name"], entry["youtube_url"], entry["last_check_date"]):
            updated += 1

    log.info(f"Tamamlandı → {updated}/{len(watchlist)} sanatçı güncellendi.")
    log.info("=" * 55)
    return {"total": len(watchlist), "updated": updated}


# ── Giriş noktası ─────────────────────────────────────────────
if __name__ == "__main__":
    args = sys.argv[1:]

    if "--once" in args:
        run_bot()
        sys.exit(0)

    hours = 24
    if "--hours" in args:
        idx = args.index("--hours")
        if idx + 1 < len(args):
            hours = int(args[idx + 1])

    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
    except ImportError:
        log.error("apscheduler kurulu değil: pip install apscheduler")
        sys.exit(1)

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(run_bot, "interval", hours=hours, next_run_time=datetime.now(timezone.utc))

    log.info(f"Zamanlayıcı başlatıldı — her {hours} saatte bir çalışacak.")
    log.info("Durdurmak için Ctrl+C basın.")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        log.info("Hunter Bot durduruldu.")
