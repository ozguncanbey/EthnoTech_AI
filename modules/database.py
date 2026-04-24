"""
SQLite veritabanı katmanı.

Tablolar:
  artists  — id, name, last_analysis_date
  scores   — artist_id, karizma, gizem, sahne_enerjisi, londra_uyumlulugu, trend_label
  reports  — artist_id, full_report_text, report_path

Modül ilk import edildiğinde şemayı oluşturur ve
eğer eski JSON varsa tek seferlik olarak SQLite'a taşır.
"""
import json
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from modules.config import DB_JSON_PATH, DB_SQLITE_PATH

# ── Bağlantı yöneticisi ───────────────────────────────────────
@contextmanager
def _conn():
    DB_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_SQLITE_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


# ── Şema oluşturma ────────────────────────────────────────────
def _init_db() -> None:
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS artists (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                name               TEXT UNIQUE NOT NULL,
                last_analysis_date TEXT
            );
            CREATE TABLE IF NOT EXISTS scores (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_id          INTEGER NOT NULL
                                   REFERENCES artists(id) ON DELETE CASCADE,
                karizma            INTEGER DEFAULT 7,
                gizem              INTEGER DEFAULT 7,
                sahne_enerjisi     INTEGER DEFAULT 7,
                londra_uyumlulugu  INTEGER DEFAULT 7,
                trend_label        TEXT
            );
            CREATE TABLE IF NOT EXISTS reports (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_id          INTEGER NOT NULL
                                   REFERENCES artists(id) ON DELETE CASCADE,
                full_report_text   TEXT,
                report_path        TEXT
            );
            CREATE TABLE IF NOT EXISTS watchlist (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_name       TEXT NOT NULL,
                youtube_url       TEXT UNIQUE NOT NULL,
                added_date        TEXT,
                last_check_date   TEXT
            );
            CREATE TABLE IF NOT EXISTS score_history (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_id         INTEGER NOT NULL
                                  REFERENCES artists(id) ON DELETE CASCADE,
                analysis_date     TEXT NOT NULL,
                karizma           INTEGER DEFAULT 7,
                gizem             INTEGER DEFAULT 7,
                sahne_enerjisi    INTEGER DEFAULT 7,
                londra_uyumlulugu INTEGER DEFAULT 7,
                trend_label       TEXT
            );
            CREATE TABLE IF NOT EXISTS alerts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_name TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                message     TEXT,
                created_at  TEXT,
                notified    INTEGER DEFAULT 0
            );
        """)


# ── JSON → SQLite tek seferlik göç ───────────────────────────
def migrate_from_json() -> None:
    if not DB_JSON_PATH.exists():
        return
    with _conn() as con:
        count = con.execute("SELECT COUNT(*) FROM artists").fetchone()[0]
    if count > 0:
        return  # DB zaten dolu, göç tekrarlanmasın

    try:
        records = json.loads(DB_JSON_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    if not records:
        return

    for record in records:
        save_analysis(
            artist_name=record["artist"],
            scores=record["scores"],
            analyzed_at=record.get("analyzed_at"),
        )

    backup = DB_JSON_PATH.with_suffix(".json.bak")
    shutil.move(str(DB_JSON_PATH), str(backup))
    print(f"[DB] {len(records)} kayıt JSON'dan SQLite'a taşındı. Yedek: {backup}")


# ── Yazma ─────────────────────────────────────────────────────
def save_analysis(
    artist_name: str,
    scores: dict,
    trend_label: str = None,
    report_text: str = None,
    report_path: str = None,
    analyzed_at: str = None,
) -> None:
    now = analyzed_at or datetime.now().isoformat(timespec="seconds")

    with _conn() as con:
        # artists — upsert
        con.execute(
            """
            INSERT INTO artists (name, last_analysis_date)
            VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET last_analysis_date = excluded.last_analysis_date
            """,
            (artist_name, now),
        )
        artist_id = con.execute(
            "SELECT id FROM artists WHERE name = ?", (artist_name,)
        ).fetchone()["id"]

        # scores — sil + yeniden ekle
        con.execute("DELETE FROM scores WHERE artist_id = ?", (artist_id,))
        con.execute(
            """
            INSERT INTO scores
                (artist_id, karizma, gizem, sahne_enerjisi, londra_uyumlulugu, trend_label)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                artist_id,
                scores.get("Karizma", 7),
                scores.get("Gizem", 7),
                scores.get("Sahne Enerjisi", 7),
                scores.get("Londra Uyumluluğu", 7),
                trend_label,
            ),
        )

        # score_history — her analizde birikim (silinmez)
        con.execute(
            """
            INSERT INTO score_history
                (artist_id, analysis_date, karizma, gizem, sahne_enerjisi,
                 londra_uyumlulugu, trend_label)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                artist_id, now,
                scores.get("Karizma", 7),
                scores.get("Gizem", 7),
                scores.get("Sahne Enerjisi", 7),
                scores.get("Londra Uyumluluğu", 7),
                trend_label,
            ),
        )

        # reports — sil + yeniden ekle (opsiyonel)
        if report_text or report_path:
            con.execute("DELETE FROM reports WHERE artist_id = ?", (artist_id,))
            con.execute(
                "INSERT INTO reports (artist_id, full_report_text, report_path) VALUES (?, ?, ?)",
                (artist_id, report_text, report_path),
            )


# ── Okuma ─────────────────────────────────────────────────────
def load_all() -> list:
    """Geriye dönük uyumlu format: JSON dönemiyle aynı dict yapısı."""
    with _conn() as con:
        rows = con.execute(
            """
            SELECT  a.name,
                    a.last_analysis_date,
                    s.karizma,
                    s.gizem,
                    s.sahne_enerjisi,
                    s.londra_uyumlulugu,
                    s.trend_label
            FROM    artists a
            LEFT JOIN scores s ON s.artist_id = a.id
            ORDER BY s.londra_uyumlulugu DESC NULLS LAST, a.last_analysis_date DESC
            """
        ).fetchall()

    return [
        {
            "artist":      row["name"],
            "analyzed_at": row["last_analysis_date"] or "",
            "scores": {
                "Karizma":           row["karizma"]           or 7,
                "Gizem":             row["gizem"]             or 7,
                "Sahne Enerjisi":    row["sahne_enerjisi"]    or 7,
                "Londra Uyumluluğu": row["londra_uyumlulugu"] or 7,
            },
            "trend_label": row["trend_label"],
        }
        for row in rows
    ]


# ── Watchlist ─────────────────────────────────────────────────
def add_to_watchlist(artist_name: str, youtube_url: str) -> None:
    with _conn() as con:
        con.execute(
            """
            INSERT INTO watchlist (artist_name, youtube_url, added_date)
            VALUES (?, ?, ?)
            ON CONFLICT(youtube_url) DO UPDATE SET artist_name = excluded.artist_name
            """,
            (artist_name, youtube_url, datetime.now().isoformat(timespec="seconds")),
        )


def get_watchlist() -> list:
    with _conn() as con:
        rows = con.execute(
            """
            SELECT artist_name, youtube_url, added_date, last_check_date
            FROM   watchlist
            ORDER  BY added_date DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def update_watchlist_check(youtube_url: str, check_date: str) -> None:
    with _conn() as con:
        con.execute(
            "UPDATE watchlist SET last_check_date = ? WHERE youtube_url = ?",
            (check_date, youtube_url),
        )


def remove_from_watchlist(youtube_url: str) -> None:
    with _conn() as con:
        con.execute("DELETE FROM watchlist WHERE youtube_url = ?", (youtube_url,))


def get_latest_scores(artist_name: str) -> dict | None:
    """Sanatçının en güncel puanlarını döner (yoksa None)."""
    with _conn() as con:
        row = con.execute(
            """
            SELECT s.karizma, s.gizem, s.sahne_enerjisi, s.londra_uyumlulugu
            FROM   scores s
            JOIN   artists a ON a.id = s.artist_id
            WHERE  a.name = ?
            """,
            (artist_name,),
        ).fetchone()
    if not row:
        return None
    return {
        "Karizma":           row["karizma"],
        "Gizem":             row["gizem"],
        "Sahne Enerjisi":    row["sahne_enerjisi"],
        "Londra Uyumluluğu": row["londra_uyumlulugu"],
    }


def get_score_history(artist_name: str) -> list:
    """Sanatçının tüm tarihli puan geçmişini döner."""
    with _conn() as con:
        rows = con.execute(
            """
            SELECT  h.analysis_date, h.karizma, h.gizem,
                    h.sahne_enerjisi, h.londra_uyumlulugu, h.trend_label
            FROM    score_history h
            JOIN    artists a ON a.id = h.artist_id
            WHERE   a.name = ?
            ORDER   BY h.analysis_date ASC
            """,
            (artist_name,),
        ).fetchall()
    return [dict(row) for row in rows]


def save_alert(artist_name: str, signal_type: str, message: str) -> None:
    with _conn() as con:
        con.execute(
            """
            INSERT INTO alerts (artist_name, signal_type, message, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (artist_name, signal_type, message, datetime.now().isoformat(timespec="seconds")),
        )


def get_alerts(limit: int = 20) -> list:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM alerts ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def load_report_text(artist_name: str) -> str | None:
    """Sanatçının tam rapor metnini döner (varsa)."""
    with _conn() as con:
        row = con.execute(
            """
            SELECT r.full_report_text
            FROM   reports r
            JOIN   artists a ON a.id = r.artist_id
            WHERE  a.name = ?
            """,
            (artist_name,),
        ).fetchone()
    return row["full_report_text"] if row else None


# ── Başlangıç ─────────────────────────────────────────────────
_init_db()
migrate_from_json()
