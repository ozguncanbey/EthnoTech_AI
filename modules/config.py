import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR      = _ROOT / "Data"
REPORTS_DIR   = _ROOT / "Reports"
TEMPLATES_DIR = _ROOT / "templates"
DB_JSON_PATH  = _ROOT / "database" / "all_analyses.json"
DB_SQLITE_PATH = _ROOT / "database" / "ethnotech_scout.db"


def get_secret(key: str) -> str:
    """
    .env (yerel) veya Streamlit Cloud secrets'tan API anahtarı döner.
    Önce os.environ'ı dener, bulamazsa st.secrets'a bakar.
    """
    val = os.getenv(key, "").strip()
    if val:
        return val
    try:
        import streamlit as st
        return str(st.secrets.get(key, ""))
    except Exception:
        return ""
