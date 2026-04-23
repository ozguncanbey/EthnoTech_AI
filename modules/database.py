import json
from datetime import datetime

from modules.config import DB_PATH


def load_all() -> list:
    if not DB_PATH.exists():
        return []
    try:
        return json.loads(DB_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_analysis(artist_name: str, scores: dict) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    records = load_all()

    for record in records:
        if record["artist"] == artist_name:
            record["scores"] = scores
            record["analyzed_at"] = datetime.now().isoformat(timespec="seconds")
            break
    else:
        records.append({
            "artist": artist_name,
            "scores": scores,
            "analyzed_at": datetime.now().isoformat(timespec="seconds"),
        })

    DB_PATH.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
