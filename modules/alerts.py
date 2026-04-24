"""
Alert (Alarm) Sistemi — Yatırım Sinyali + Telegram Bildirimi

Sinyal koşulları:
  HIGH_SCORE : londra_uyumlulugu >= SCORE_THRESHOLD (varsayılan 9)
  RISING     : londra puanı önceki analize göre > RISE_THRESHOLD (varsayılan 1) arttı
"""
import logging

import requests
from dotenv import load_dotenv
from modules.config import get_secret

load_dotenv()

log = logging.getLogger("HunterBot")

SCORE_THRESHOLD = 9   # bu puan veya üzeri → HIGH_SCORE sinyali
RISE_THRESHOLD  = 1   # bu miktardan fazla artış → RISING sinyali


# ── Sinyal tespiti ────────────────────────────────────────────
def check_signals(
    artist_name: str,
    current: dict,
    previous: dict | None,
) -> list[dict]:
    signals = []
    london  = current.get("Londra Uyumluluğu", 0)
    display = artist_name.replace("_", " ")

    if london >= SCORE_THRESHOLD:
        signals.append({
            "type":    "HIGH_SCORE",
            "message": (
                f"🚨 <b>Yüksek Potansiyelli Sanatçı Bulundu!</b>\n"
                f"👤 {display}\n"
                f"🎯 Londra Uyumluluğu: <b>{london}/10</b>\n"
                f"💡 Yatırım Sinyali: GÜÇLÜ"
            ),
        })

    if previous:
        prev_london = previous.get("Londra Uyumluluğu", 0)
        rise = london - prev_london
        if rise > RISE_THRESHOLD:
            signals.append({
                "type":    "RISING",
                "message": (
                    f"📈 <b>Yükselen Sinyal!</b>\n"
                    f"👤 {display}\n"
                    f"🎯 Londra Puanı: {prev_london}/10 → <b>{london}/10</b> "
                    f"(<b>{rise:+d} puan</b>)"
                ),
            })

    return signals


# ── Telegram bildirimi ────────────────────────────────────────
def send_telegram(message: str) -> None:
    token    = get_secret("TELEGRAM_BOT_TOKEN")
    chat_ids = [c.strip() for c in get_secret("TELEGRAM_CHAT_IDS").split(",") if c.strip()]

    if not token or not chat_ids:
        log.warning("Telegram yapılandırılmamış — TELEGRAM_BOT_TOKEN veya TELEGRAM_CHAT_IDS eksik.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for chat_id in chat_ids:
        try:
            resp = requests.post(
                url,
                json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
                timeout=10,
            )
            if resp.ok:
                log.info(f"  Telegram → chat_id {chat_id} ✓")
            else:
                log.warning(f"  Telegram hatası: {resp.text[:200]}")
        except requests.RequestException as e:
            log.error(f"  Telegram bağlantı hatası: {e}")


# ── Ana akış (bot ve app tarafından çağrılır) ─────────────────
def process_signals(
    artist_name: str,
    current_scores: dict,
    prev_scores: dict | None,
) -> list[dict]:
    """Sinyalleri kontrol et, DB'ye kaydet ve Telegram'a gönder."""
    from modules.database import save_alert

    signals = check_signals(artist_name, current_scores, prev_scores)
    for sig in signals:
        log.info(f"KRİTİK SİNYAL [{sig['type']}]: {artist_name}")
        save_alert(artist_name, sig["type"], sig["message"])
        send_telegram(sig["message"])

    return signals
