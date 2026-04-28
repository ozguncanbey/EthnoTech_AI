import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from pathlib import Path

from modules.alerts import process_signals
from modules.bot import run_bot
from modules.chart import generate_radar_chart
from modules.config import REPORTS_DIR
from modules.database import (add_to_watchlist, get_alerts, get_hashtag_stats,
                               get_latest_scores, get_score_history, get_watchlist,
                               load_all, remove_from_watchlist, save_analysis)
from modules.groq_client import analyze_artist, analyze_with_trend, extract_scores
from modules.report import build_artist_html, build_summary_html
from modules.youtube_client import fetch_youtube_data, split_by_date

st.set_page_config(
    page_title="EthnoTech AI Scout",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════
# UI DESIGN SYSTEM — EthnoTech AI Scout v1.0
# Palette: Anthracite Dark × Neon Mint × Electric Purple
# ══════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,300..900;1,14..32,300..900&display=swap');

/* ── Design Tokens ── */
:root {
  /* Surfaces */
  --bg:      #0E1117;
  --bg2:     #161B22;
  --bg3:     #1E2530;

  /* Brand */
  --accent:  #00FFAA;
  --purple:  #8A2BE2;
  --cyan:    #00D4FF;
  --gold:    #FFD700;
  --red:     #FF4757;
  --pink:    #EC4899;

  /* Text */
  --text:    #E8EDF4;
  --muted:   #6B7280;

  /* Borders */
  --border:  #21262D;

  /* Gradients */
  --grad:       linear-gradient(135deg, #00FFAA, #00D4FF);
  --grad-hero:  linear-gradient(135deg, #00FFAA 0%, #8A2BE2 100%);
  --grad-g:     linear-gradient(90deg,  #00FFAA, #00D4FF);
  --grad-p:     linear-gradient(90deg,  #8A2BE2, #EC4899);
  --grad-o:     linear-gradient(90deg,  #FFD700, #FF9500);
  --grad-b:     linear-gradient(90deg,  #00D4FF, #0080FF);

  /* Glows */
  --glow-mint:   0 0 24px rgba(0,255,170,0.18);
  --glow-purple: 0 0 24px rgba(138,43,226,0.22);
  --glow-card:   0 12px 40px rgba(0,0,0,0.5);
}

/* ── Base ── */
html, body, [data-testid="stApp"] {
  background: var(--bg) !important;
  color: var(--text) !important;
  font-family: 'Inter', system-ui, sans-serif !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #30363D; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: var(--bg2) !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text) !important; }
[data-testid="stSidebar"] .stRadio label { font-size: 13px !important; }
[data-testid="stSidebar"] [data-testid="stTextInput"] input,
[data-testid="stSidebar"] textarea {
  background: var(--bg3) !important;
  border: 1px solid var(--border) !important;
  color: var(--text) !important;
  border-radius: 10px !important;
  font-size: 13px !important;
}
[data-testid="stSidebar"] [data-testid="stTextInput"] input:focus,
[data-testid="stSidebar"] textarea:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 2px rgba(0,255,170,0.15) !important;
}

/* ── Tabs ── */
div[data-testid="stTabs"] { border-bottom: 1px solid var(--border); }
div[data-testid="stTabs"] button {
  color: var(--muted) !important;
  font-weight: 600 !important;
  font-size: 14px !important;
  letter-spacing: 0.4px !important;
  padding: 12px 24px !important;
  transition: all 0.2s ease !important;
  border-radius: 0 !important;
}
div[data-testid="stTabs"] button:hover {
  color: var(--text) !important;
  background: rgba(255,255,255,0.03) !important;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
  color: var(--accent) !important;
  border-bottom: 2px solid var(--accent) !important;
  text-shadow: 0 0 16px rgba(0,255,170,0.4) !important;
}

/* ── Buttons ── */
.stButton > button {
  background: var(--grad) !important;
  color: #000 !important;
  border: none !important;
  border-radius: 10px !important;
  font-weight: 700 !important;
  font-size: 13px !important;
  letter-spacing: 0.5px !important;
  width: 100% !important;
  padding: 11px 18px !important;
  transition: opacity 0.18s, transform 0.15s, box-shadow 0.18s !important;
}
.stButton > button:hover {
  opacity: 0.9 !important;
  transform: translateY(-2px) !important;
  box-shadow: var(--glow-mint) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* ── Sidebar artist mini-buttons ── */
.sb-artist > button {
  background: var(--bg3) !important;
  color: var(--text) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  font-size: 12px !important;
  font-weight: 500 !important;
  text-align: left !important;
  margin-bottom: 4px !important;
  padding: 8px 12px !important;
  transition: all 0.15s !important;
}
.sb-artist > button:hover {
  border-color: var(--accent) !important;
  color: var(--accent) !important;
  background: rgba(0,255,170,0.06) !important;
}

/* ── st.metric ── */
[data-testid="stMetric"] {
  background: var(--bg2) !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
  padding: 18px 22px !important;
  transition: border-color 0.2s !important;
}
[data-testid="stMetric"]:hover { border-color: #30363D !important; }
[data-testid="stMetricValue"] {
  color: var(--text) !important;
  font-weight: 800 !important;
  font-size: 28px !important;
  letter-spacing: -0.5px !important;
}
[data-testid="stMetricLabel"] {
  color: var(--muted) !important;
  font-size: 11px !important;
  letter-spacing: 1px !important;
  text-transform: uppercase !important;
}

/* ── Alerts / Info boxes ── */
hr { border-color: var(--border) !important; }
[data-testid="stAlert"] {
  background: var(--bg3) !important;
  border-radius: 12px !important;
  border-left: 3px solid var(--accent) !important;
  font-size: 13px !important;
}

/* ── Progress bar ── */
[data-testid="stProgressBar"] > div {
  background: var(--grad) !important;
  border-radius: 4px !important;
}

/* ── st.status ── */
[data-testid="stStatusWidget"] {
  background: var(--bg2) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
}

/* ── LIVE PULSE ── */
.live-badge {
  position: fixed;
  top: 14px; right: 18px;
  z-index: 9999;
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(0,255,170,0.07);
  border: 1px solid rgba(0,255,170,0.2);
  border-radius: 20px;
  padding: 6px 14px;
  font-size: 10px;
  font-weight: 800;
  color: var(--accent);
  letter-spacing: 2px;
  text-transform: uppercase;
  backdrop-filter: blur(12px);
}
.pulse-dot {
  width: 7px; height: 7px;
  background: var(--accent);
  border-radius: 50%;
  animation: pulse-ring 2.5s ease-in-out infinite;
}
@keyframes pulse-ring {
  0%   { box-shadow: 0 0 0 0 rgba(0,255,170,0.8); }
  70%  { box-shadow: 0 0 0 8px rgba(0,255,170,0); }
  100% { box-shadow: 0 0 0 0 rgba(0,255,170,0); }
}

/* ── MAIN HEADER ── */
.main-header {
  padding: 36px 0 28px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 32px;
}
.brand-row { display: flex; align-items: center; gap: 14px; margin-bottom: 8px; }
.brand-icon {
  font-size: 30px;
  background: var(--grad-hero);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.brand-title {
  font-size: 28px;
  font-weight: 900;
  letter-spacing: -1px;
  background: var(--grad-hero);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.brand-sub {
  font-size: 11px;
  color: var(--muted);
  letter-spacing: 3px;
  text-transform: uppercase;
  margin-left: 44px;
}

/* ── ARTIST CARDS ── */
.artist-card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 26px 30px;
  margin-bottom: 16px;
  transition: all 0.25s ease;
  cursor: default;
  box-shadow: var(--glow-card);
}
.artist-card:hover {
  border-color: rgba(0,255,170,0.35);
  transform: translateY(-3px);
  box-shadow: var(--glow-card), 0 0 40px rgba(0,255,170,0.08);
}
.artist-card.sign-now-card {
  border-color: rgba(0,255,170,0.25);
  box-shadow: var(--glow-card), 0 0 30px rgba(0,255,170,0.1);
}
.card-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 24px;
}
.card-rank { font-size: 22px; min-width: 32px; }
.card-name {
  flex: 1;
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.3px;
}
.card-london {
  display: inline-block;
  font-size: 26px;
  font-weight: 900;
  letter-spacing: -0.5px;
  flex-shrink: 0;
}
.card-date {
  font-size: 11px;
  color: var(--muted);
  margin-left: 4px;
  align-self: flex-end;
  padding-bottom: 4px;
  flex-shrink: 0;
}
.card-trend {
  font-size: 11px;
  font-weight: 700;
  padding: 4px 11px;
  border-radius: 12px;
  letter-spacing: 0.5px;
}
.trend-r { background: rgba(0,255,170,0.1); color: #00FFAA; border: 1px solid rgba(0,255,170,0.3); }
.trend-s { background: rgba(255,215,0,0.1); color: #FFD700; border: 1px solid rgba(255,215,0,0.3); }
.trend-d { background: rgba(255,71,87,0.1); color: #FF4757; border: 1px solid rgba(255,71,87,0.3); }

/* ── SIGN NOW Badge ── */
.sign-now-badge {
  font-size: 10px;
  font-weight: 900;
  padding: 4px 11px;
  border-radius: 10px;
  letter-spacing: 1.2px;
  background: linear-gradient(135deg, rgba(0,255,170,0.2), rgba(138,43,226,0.2));
  color: var(--accent);
  border: 1px solid rgba(0,255,170,0.45);
  animation: sign-pulse 2.5s ease-in-out infinite;
}
.sign-now-badge.extreme {
  color: #fff;
  background: linear-gradient(135deg, rgba(138,43,226,0.3), rgba(236,72,153,0.3));
  border-color: rgba(138,43,226,0.5);
  animation: sign-pulse-purple 2.5s ease-in-out infinite;
}
@keyframes sign-pulse {
  0%,100% { box-shadow: 0 0 0 0 rgba(0,255,170,0.5); }
  50%      { box-shadow: 0 0 12px 4px rgba(0,255,170,0.15); }
}
@keyframes sign-pulse-purple {
  0%,100% { box-shadow: 0 0 0 0 rgba(138,43,226,0.5); }
  50%      { box-shadow: 0 0 12px 4px rgba(138,43,226,0.2); }
}

/* ── METRIC BARS ── */
.metric-row {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 12px;
}
.metric-label {
  width: 140px;
  font-size: 10px;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 1px;
  flex-shrink: 0;
}
.metric-track {
  flex: 1;
  height: 6px;
  background: var(--bg3);
  border-radius: 4px;
  overflow: hidden;
}
.metric-fill {
  height: 100%;
  border-radius: 4px;
  width: 0;
  animation: fillBar 1.2s cubic-bezier(.4,0,.2,1) forwards;
}
.mf-green  { background: var(--grad-g); }
.mf-blue   { background: var(--grad-b); }
.mf-orange { background: var(--grad-o); }
.mf-purple { background: var(--grad-p); }
@keyframes fillBar { to { width: var(--w); } }
.metric-val {
  width: 36px;
  text-align: right;
  font-size: 14px;
  font-weight: 800;
  color: var(--text);
  flex-shrink: 0;
  letter-spacing: -0.3px;
}

/* ── EMPTY STATE ── */
.empty-state {
  text-align: center;
  padding: 100px 40px;
}
.empty-icon { font-size: 56px; margin-bottom: 20px; opacity: 0.6; }
.empty-title {
  font-size: 22px;
  font-weight: 800;
  color: #374151;
  margin-bottom: 10px;
  letter-spacing: -0.3px;
}
.empty-sub { font-size: 14px; color: var(--muted); line-height: 1.7; }
.empty-cta {
  display: inline-block;
  margin-top: 20px;
  font-size: 12px;
  font-weight: 700;
  color: var(--accent);
  letter-spacing: 1.5px;
  text-transform: uppercase;
  border: 1px solid rgba(0,255,170,0.3);
  padding: 8px 20px;
  border-radius: 20px;
  background: rgba(0,255,170,0.06);
}

/* ── WATCHLIST ── */
.wl-name { font-weight: 700; font-size: 15px; color: var(--text); }
.wl-url  { font-size: 11px; color: var(--muted); margin-top: 2px; word-break: break-all; }
.wl-meta { font-size: 11px; color: var(--muted); }

/* ── ALERT PILL ── */
.alert-pill {
  display: flex;
  align-items: center;
  gap: 14px;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: 12px;
  padding: 13px 18px;
  margin-bottom: 8px;
  transition: border-color 0.2s;
}
.alert-pill:hover { border-color: rgba(0,255,170,0.25); }
.alert-pill.rising { border-left-color: var(--accent); }
.alert-pill.high   { border-left-color: var(--gold); }
.alert-artist { font-weight: 700; font-size: 14px; }
.alert-type   { font-size: 11px; color: var(--muted); margin-top: 2px; }
.alert-time   { margin-left: auto; font-size: 11px; color: var(--muted); white-space: nowrap; }

/* ── Info card (replaces st.info) ── */
.info-card {
  background: var(--bg3);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: 12px;
  padding: 14px 18px;
  font-size: 13px;
  color: var(--text);
  margin: 8px 0;
}

/* ── Sidebar version badge ── */
.version-badge {
  display: inline-block;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--muted);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 2px 7px;
  margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)

# ── Live Pulse (fixed) ────────────────────────────────────────
st.markdown("""
<div class="live-badge">
  <div class="pulse-dot"></div>
  LIVE
</div>
""", unsafe_allow_html=True)

# ── Session State ─────────────────────────────────────────────
for key, default in [("report_html", None), ("current_artist", None),
                     ("last_yt_url", None), ("last_yt_artist", None),
                     ("goto_report", None)]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Ek CSS: Sidebar Pills + Score Strip + Katalog ─────────────
st.markdown("""
<style>
/* Sidebar score pill row */
.sb-pill-row { display:flex; align-items:center; gap:8px; margin-bottom:5px; }
.sb-pill {
  min-width:42px; height:34px;
  display:flex; align-items:center; justify-content:center;
  border-radius:8px; flex-shrink:0;
  font-size:12px; font-weight:900;
}
.sb-pill-wrap > button {
  background: var(--bg3) !important;
  color: var(--text) !important;
  border: 1px solid var(--border) !important;
  border-radius:8px !important; font-size:12px !important;
  font-weight:600 !important; text-align:left !important;
  padding:6px 10px !important; margin:0 !important;
  transition:all 0.15s !important;
}
.sb-pill-wrap > button:hover {
  border-color: var(--accent) !important;
  color: var(--accent) !important;
}

/* Score Strip (Sanatçı Raporu üstü) */
.score-strip {
  border-radius:14px; padding:14px 24px;
  margin-bottom:20px; display:flex; align-items:center; gap:18px;
  position:relative; overflow:hidden;
}
.score-strip::before {
  content:''; position:absolute; inset:0;
  background:rgba(0,0,0,0.18); border-radius:14px;
}
.ss-score { font-size:38px; font-weight:900; color:#000; letter-spacing:-1.5px; position:relative; }
.ss-label { font-size:13px; font-weight:800; color:rgba(0,0,0,0.6);
            letter-spacing:1.5px; text-transform:uppercase; position:relative; }
.ss-sub   { font-size:11px; color:rgba(0,0,0,0.45); position:relative; }

/* Catalog cards */
.cat-card {
  background:var(--bg2); border:1px solid var(--border);
  border-radius:16px; padding:0; margin-bottom:14px;
  overflow:hidden; transition:all 0.2s ease;
}
.cat-card:hover {
  border-color:rgba(0,255,170,0.3);
  box-shadow:0 6px 24px rgba(0,0,0,0.4);
  transform:translateY(-2px);
}
.cat-header {
  padding:16px 18px 12px; display:flex;
  justify-content:space-between; align-items:flex-start;
}
.cat-score { font-size:30px; font-weight:900; letter-spacing:-1px; }
.cat-name  { font-size:15px; font-weight:700; color:var(--text); margin-top:2px; }
.cat-body  { padding:0 18px 16px; }
.cat-meta  { font-size:11px; color:var(--muted); margin-bottom:8px; }
.cat-tag {
  display:inline-block; font-size:10px; font-weight:700;
  padding:2px 8px; border-radius:6px; margin-right:4px;
  background:rgba(0,255,170,0.08); color:var(--accent);
  border:1px solid rgba(0,255,170,0.2);
}

/* YouTube CTA button in report */
.yt-cta-wrap {
  margin-bottom:16px;
}
.yt-cta-wrap a {
  display:inline-flex; align-items:center; gap:10px;
  background:rgba(255,0,0,0.12);
  border:2px solid rgba(255,68,68,0.5);
  color:#FF4444 !important; text-decoration:none;
  padding:10px 22px; border-radius:12px;
  font-weight:800; font-size:14px; letter-spacing:0.3px;
  transition:all 0.2s;
}
.yt-cta-wrap a:hover {
  background:rgba(255,0,0,0.2);
  box-shadow:0 0 20px rgba(255,0,0,0.2);
  transform:translateY(-1px);
}

/* Filter pill buttons */
.filter-pills { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:16px; }
.fpill {
  font-size:12px; font-weight:700; padding:5px 14px; border-radius:20px;
  border:1px solid var(--border); color:var(--muted); cursor:pointer;
  background:var(--bg2); transition:all 0.15s;
}
.fpill.active { border-color:var(--accent); color:var(--accent);
                background:rgba(0,255,170,0.08); }
</style>
""", unsafe_allow_html=True)


# ── Helper: Artist Card HTML ──────────────────────────────────
def _artist_card(r: dict, rank: str, delay_base: float = 0.0) -> str:
    s = r["scores"]
    name = r["artist"].replace("_", " ")
    date = r.get("analyzed_at", "")[:10]
    trend = r.get("trend_label")

    if trend == "Yükselen Yıldız":
        trend_html = '<span class="card-trend trend-r">⬆ Yükselen Yıldız</span>'
    elif trend == "Düşüşte":
        trend_html = '<span class="card-trend trend-d">⬇ Düşüşte</span>'
    elif trend == "Stabil":
        trend_html = '<span class="card-trend trend-s">→ Stabil</span>'
    else:
        trend_html = ""

    def bar(label, val, css_class, delay):
        pct     = float(val) * 10          # 9.3 → 93%
        val_str = f"{float(val):.1f}"      # "9.3"
        return (
            f'<div class="metric-row">'
            f'<span class="metric-label">{label}</span>'
            f'<div class="metric-track">'
            f'<div class="metric-fill {css_class}" style="--w:{pct}%;animation-delay:{delay:.2f}s"></div>'
            f'</div>'
            f'<span class="metric-val">{val_str}</span>'
            f'</div>'
        )

    bars = (
        bar("Karizma",           s["Karizma"],           "mf-green",  delay_base + 0.0) +
        bar("Gizem",             s["Gizem"],             "mf-blue",   delay_base + 0.12) +
        bar("Sahne Enerjisi",    s["Sahne Enerjisi"],    "mf-orange", delay_base + 0.24) +
        bar("Londra Uyumluluğu", s["Londra Uyumluluğu"],"mf-purple", delay_base + 0.36)
    )

    london = float(s["Londra Uyumluluğu"])
    if london >= 9.5:
        london_color = "#00FFAA"
        sign_badge   = '<span class="sign-now-badge extreme">🔥 SIGN NOW 9.5+</span>'
        card_class   = "artist-card sign-now-card"
    elif london >= 9.0:
        london_color = "#00FFAA"
        sign_badge   = '<span class="sign-now-badge">⚡ SIGN NOW</span>'
        card_class   = "artist-card sign-now-card"
    elif london >= 7.0:
        london_color = "#FFD700"
        sign_badge   = ""
        card_class   = "artist-card"
    else:
        london_color = "#FF4757"
        sign_badge   = ""
        card_class   = "artist-card"

    return (
        f'<div class="{card_class}">'
        f'<div class="card-header">'
        f'<span class="card-rank">{rank}</span>'
        f'<span class="card-name">{name}</span>'
        f'{trend_html}'
        f'{sign_badge}'
        f'<span class="card-london" style="background:none;-webkit-text-fill-color:{london_color};color:{london_color}">'
        f'{london:.1f}/10</span>'
        f'<span class="card-date">{date}</span>'
        f'</div>'
        f'{bars}'
        f'</div>'
    )


# ── Analysis runner ───────────────────────────────────────────
def _run_analysis(artist_name: str, raw_comments: str,
                  recent_str: str = None, older_str: str = None,
                  youtube_url: str = None) -> dict:
    prev_scores = get_latest_scores(artist_name)

    name_display = artist_name.replace("_", " ")
    with st.status(f"🎵 {name_display} analiz ediliyor...", expanded=True) as status:
        if recent_str is not None and older_str is not None:
            st.write("🤖 Llama 3.3 70B — trend analizi başlatıldı (15–20 sn)...")
            report_text, trend_label = analyze_with_trend(recent_str, older_str, artist_name)
        else:
            st.write("🤖 Llama 3.3 70B — yorum korpusu analiz ediliyor (15–20 sn)...")
            report_text = analyze_artist(raw_comments, artist_name)
            trend_label = None

        st.write("📊 Puanlar çıkarılıyor — radar grafiği oluşturuluyor...")
        scores = extract_scores(report_text)
        chart_b64 = generate_radar_chart(scores, artist_name)
        html = build_artist_html(report_text, artist_name, scores, chart_b64,
                                 trend_label, youtube_url)

        st.write("🚨 Yatırım sinyalleri kontrol ediliyor...")
        REPORTS_DIR.mkdir(exist_ok=True)
        out = REPORTS_DIR / f"{artist_name}_rapor.html"
        out.write_text(html, encoding="utf-8")
        save_analysis(
            artist_name=artist_name, scores=scores,
            trend_label=trend_label, report_text=report_text, report_path=str(out),
        )
        (REPORTS_DIR / "_ozet_rapor.html").write_text(build_summary_html(), encoding="utf-8")
        st.session_state.report_html = html
        st.session_state.current_artist = artist_name
        london = float(scores.get("Londra Uyumluluğu", 0))
        status.update(
            label=f"✅ {name_display} — {london:.1f}/10 London Score",
            state="complete", expanded=False
        )

    signals = process_signals(artist_name, scores, prev_scores, youtube_url=youtube_url)
    for sig in signals:
        st.toast(sig["message"].replace("<b>", "**").replace("</b>", "**"), icon="🚨")

    return {"artist": artist_name, "scores": scores}


def _load_artist_report(artist_name: str) -> None:
    # Önce dosyadan oku (hızlı yol)
    html_path = REPORTS_DIR / f"{artist_name}_rapor.html"
    if html_path.exists():
        st.session_state.report_html    = html_path.read_text(encoding="utf-8")
        st.session_state.current_artist = artist_name
        return

    # Dosya yoksa (örn. Streamlit Cloud) DB'den yeniden üret
    from modules.database import load_report_text, get_latest_scores
    from modules.report import build_artist_html
    from modules.chart import generate_radar_chart
    report_text = load_report_text(artist_name)
    scores      = get_latest_scores(artist_name)
    if report_text and scores:
        chart_b64 = generate_radar_chart(scores, artist_name)
        html = build_artist_html(report_text, artist_name, scores, chart_b64)
        REPORTS_DIR.mkdir(exist_ok=True)
        html_path.write_text(html, encoding="utf-8")
        st.session_state.report_html    = html
        st.session_state.current_artist = artist_name


# ── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:22px 0 16px;">
      <div style="font-size:22px;font-weight:900;letter-spacing:-0.8px;
                  background:linear-gradient(135deg,#00FFAA,#8A2BE2);
                  -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
        ◈ EthnoTech AI
      </div>
      <div style="font-size:10px;color:#6B7280;letter-spacing:2.5px;margin-top:3px;
                  text-transform:uppercase;">
        A&R Intelligence Platform
      </div>
      <span class="version-badge">v1.0 Scout</span>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    mode = st.radio("Analiz Modu", ["YouTube Linki", "Manuel Giriş"], label_visibility="collapsed")

    if mode == "YouTube Linki":
        url = st.text_input("YouTube URL", placeholder="https://youtube.com/watch?v=...")
        artist_override = st.text_input("Sanatçı Adı (opsiyonel)",
                                        placeholder="Boş bırakırsan otomatik tespit edilir")
        if st.button("▶  Analiz Başlat", key="yt_btn"):
            if not url.strip():
                st.error("Lütfen bir YouTube linki girin.")
            else:
                try:
                    with st.spinner("📡 Video bilgileri alınıyor..."):
                        artist_name, comments_list, title = fetch_youtube_data(url)
                    if artist_override.strip():
                        artist_name = artist_override.strip().replace(" ", "_")
                    recent_str, older_str = split_by_date(comments_list)
                    raw_comments = "\n".join(f"- {c['text']}" for c in comments_list)
                    recent_count = len(recent_str.splitlines()) if recent_str else 0
                    older_count  = len(older_str.splitlines())  if older_str  else 0
                    st.info(f"**{title}**\n\nSon 3 ay: **{recent_count}** · Eskiler: **{older_count}**")
                    _run_analysis(artist_name, raw_comments, recent_str, older_str,
                                  youtube_url=url)
                    st.session_state.last_yt_url    = url
                    st.session_state.last_yt_artist = artist_name
                    st.rerun()
                except Exception as e:
                    st.error(f"Hata: {e}")
    else:
        artist_name_input = st.text_input("Sanatçı Adı", placeholder="Mehmet Aslan")
        comments_input = st.text_area("Yorumlar", height=200,
                                      placeholder="- Bağlama kullanımı inanılmaz...\n- ...")
        if st.button("▶  Analiz Başlat", key="manual_btn"):
            if not artist_name_input.strip() or not comments_input.strip():
                st.error("Sanatçı adı ve en az bir yorum zorunlu.")
            else:
                try:
                    artist_name = artist_name_input.strip().replace(" ", "_")
                    _run_analysis(artist_name, comments_input)
                    st.rerun()
                except Exception as e:
                    st.error(f"Hata: {e}")

    if st.session_state.last_yt_url:
        st.divider()
        disp = (st.session_state.last_yt_artist or "").replace("_", " ")
        st.caption(f"Son analiz: **{disp}**")
        if st.button("📌 Takip Listesine Ekle", key="wl_add"):
            add_to_watchlist(st.session_state.last_yt_artist, st.session_state.last_yt_url)
            st.success(f"{disp} takip listesine eklendi!")

    records = load_all()
    if records:
        st.divider()
        st.markdown(
            '<div style="font-size:10px;color:#6B7280;letter-spacing:2px;'
            'text-transform:uppercase;margin-bottom:8px;">'
            f'Liderlik Tablosu &nbsp;·&nbsp; {len(records)} Sanatçı</div>',
            unsafe_allow_html=True
        )

        # Arama kutusu
        search_q = st.text_input(
            "search", placeholder="🔍 Sanatçı ara...",
            key="artist_search", label_visibility="collapsed"
        )

        ranked_sb = sorted(records, key=lambda x: x["scores"]["Londra Uyumluluğu"], reverse=True)
        if search_q:
            ranked_sb = [r for r in ranked_sb
                         if search_q.lower() in r["artist"].lower().replace("_", " ")]

        for r in ranked_sb:
            disp  = r["artist"].replace("_", " ")
            score = float(r["scores"]["Londra Uyumluluğu"])
            trend = r.get("trend_label", "")

            if score >= 9.0:
                sc, bg, br = "#00FFAA", "rgba(0,255,170,0.1)", "rgba(0,255,170,0.3)"
                sign = "⚡"
            elif score >= 7.0:
                sc, bg, br = "#FFD700", "rgba(255,215,0,0.1)", "rgba(255,215,0,0.3)"
                sign = ""
            else:
                sc, bg, br = "#FF4757", "rgba(255,71,87,0.1)", "rgba(255,71,87,0.3)"
                sign = ""

            t_icon = {"Yükselen Yıldız": "⬆", "Düşüşte": "⬇", "Stabil": "→"}.get(trend, "")

            # Score pill + isim butonu yan yana
            c1, c2 = st.columns([1, 3])
            with c1:
                st.markdown(
                    f'<div class="sb-pill" style="background:{bg};border:1px solid {br};">'
                    f'<span style="color:{sc}">{score:.1f}</span></div>',
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown('<div class="sb-pill-wrap">', unsafe_allow_html=True)
                if st.button(f"{disp} {sign}{t_icon}", key=f"sb_{r['artist']}",
                             use_container_width=True):
                    st.session_state.goto_report = r["artist"]
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)


# ── MAIN HEADER ───────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <div class="brand-row">
    <span class="brand-icon">◈</span>
    <span class="brand-title">EthnoTech AI Scout</span>
  </div>
  <div class="brand-sub">A&R Intelligence Platform &nbsp;·&nbsp; London Market Analysis</div>
</div>
""", unsafe_allow_html=True)

# ── goto_report handler: sidebar'dan tıklama → Sanatçı Raporu tab'ına geç ──
if st.session_state.goto_report:
    _load_artist_report(st.session_state.goto_report)
    st.session_state.goto_report = None
    # JS: Sanatçı Raporu sekmesi (index 1) tıkla
    components.html("""<script>
    setTimeout(function() {
        try {
            var tabs = window.parent.document.querySelectorAll(
                '[data-testid="stTabs"] button');
            if (tabs && tabs.length > 1) tabs[1].click();
        } catch(e) {}
    }, 250);
    </script>""", height=0)

# ── TABS ──────────────────────────────────────────────────────
tab_radar, tab_report, tab_catalog, tab_bot = st.tabs(
    ["◈ A&R Radar", "📄 Sanatçı Raporu", "◎ Katalog", "🎯 Hunter Bot"]
)

# ── TAB 1: A&R RADAR (default) ────────────────────────────────
# (Tab içeriği aşağıda tab_radar bloğunda)

# ── TAB 2: SANATÇI RAPORU ─────────────────────────────────────
with tab_report:
    all_records_rp = load_all()
    if not all_records_rp:
        st.markdown("""
        <div class="empty-state">
          <div class="empty-icon">◈</div>
          <div class="empty-title">Henüz analiz yapılmadı</div>
          <div class="empty-sub">Sol panelden bir YouTube linki veya yorum girin.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        ranked_rp = sorted(all_records_rp,
                           key=lambda x: x["scores"]["Londra Uyumluluğu"],
                           reverse=True)

        # Selectbox: tab sıfırlanmadan sanatçı değiştirmeyi sağlar
        chosen = st.selectbox(
            "Sanatçı",
            options=[r["artist"] for r in ranked_rp],
            format_func=lambda a: a.replace("_", " "),
            key="report_select",
            label_visibility="collapsed",
        )

        # Seçim değişince doğrudan yükle (st.rerun() gerekmez)
        if chosen:
            _load_artist_report(chosen)

        if st.session_state.report_html:
            artist = st.session_state.current_artist

            # ── Score Strip ──────────────────────────────────
            if artist:
                sc_data = get_latest_scores(artist)
                if sc_data:
                    london = float(sc_data.get("Londra Uyumluluğu", 0))
                    if london >= 9.5:
                        strip_bg  = "linear-gradient(135deg,#FFD700,#FF9500,#FFD700)"
                        strip_lbl = "⭐  LEGENDARY — Tarihî Fırsat"
                        strip_sub = "Bu fırsat penceresi kapanmadan harekete geç"
                    elif london >= 9.0:
                        strip_bg  = "linear-gradient(135deg,#00FFAA,#00D4FF)"
                        strip_lbl = "⚡  SIGN NOW — Güçlü Yatırım Adayı"
                        strip_sub = "Londra sahnesiyle yüksek uyum tespit edildi"
                    elif london >= 7.0:
                        strip_bg  = "linear-gradient(135deg,#6B7280,#374151)"
                        strip_lbl = "◎  Potansiyel Aday — Geliştirme Önerili"
                        strip_sub = "Doğru yönlendirmeyle üst kategoriye çıkabilir"
                    else:
                        strip_bg  = "linear-gradient(135deg,#FF4757,#c0392b)"
                        strip_lbl = "○  Hazır Değil — Ciddi Gelişim Gerekli"
                        strip_sub = "Şu an için yatırım önerilmez"
                    st.markdown(
                        f'<div class="score-strip" style="background:{strip_bg};">'
                        f'<div class="ss-score">{london:.1f}</div>'
                        f'<div>'
                        f'<div class="ss-label">{strip_lbl}</div>'
                        f'<div class="ss-sub">{strip_sub}</div>'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )

                # YouTube CTA (session_state'ten URL bul)
                yt_url = st.session_state.get("last_yt_url")
                if yt_url:
                    st.markdown(
                        f'<div class="yt-cta-wrap">'
                        f'<a href="{yt_url}" target="_blank">'
                        f'▶ YouTube\'da İzle &nbsp;— Kaynağa Git</a></div>',
                        unsafe_allow_html=True,
                    )

            components.html(st.session_state.report_html, height=1500, scrolling=True)

            if artist:
                history = get_score_history(artist)
                if len(history) >= 2:
                    st.markdown(
                        f'<div style="font-size:12px;font-weight:700;color:#6B7280;'
                        f'letter-spacing:2px;text-transform:uppercase;margin:28px 0 12px;">'
                        f'📈 {artist.replace("_", " ")} — Puan Geçmişi</div>',
                        unsafe_allow_html=True
                    )
                    df_h = pd.DataFrame([{
                        "Tarih":             h["analysis_date"][:10],
                        "Karizma":           h["karizma"],
                        "Gizem":             h["gizem"],
                        "Sahne Enerjisi":    h["sahne_enerjisi"],
                        "Londra Uyumluluğu": h["londra_uyumlulugu"],
                    } for h in history]).set_index("Tarih")
                    st.line_chart(df_h, height=220)
        else:
            st.markdown("""
            <div class="empty-state" style="padding:80px 20px">
              <div class="empty-icon">📄</div>
              <div class="empty-title">Rapor seç veya analiz başlat</div>
              <div class="empty-sub">Soldaki listeden bir sanatçıya tıkla<br>
              ya da yeni bir YouTube analizi yap.</div>
            </div>
            """, unsafe_allow_html=True)

# ── TAB 2: A&R RADAR ─────────────────────────────────────────
with tab_radar:
    records = load_all()
    if not records:
        st.markdown("""
        <div class="empty-state">
          <div class="empty-icon">📊</div>
          <div class="empty-title">Karşılaştırma için sanatçı yok</div>
          <div class="empty-sub">Sol panelden analiz başlatın.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        ranked = sorted(records, key=lambda x: x["scores"]["Londra Uyumluluğu"], reverse=True)
        best   = ranked[0]
        avg    = sum(r["scores"]["Londra Uyumluluğu"] for r in records) / len(records)

        # ── Summary metrics ──
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Toplam Sanatçı", len(records))
        with c2:
            st.metric("En Yüksek Puan", f"{float(best['scores']['Londra Uyumluluğu']):.1f}/10",
                      best["artist"].replace("_", " "))
        with c3:
            st.metric("Ortalama Puan", f"{avg:.1f}/10")
        with c4:
            alerts = get_alerts(limit=5)
            st.metric("Aktif Sinyal", len(alerts), "🚨" if alerts else "")

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

        # ── Artist cards — tek blokta render (Streamlit escaping önlemi) ──
        medals = ["🥇", "🥈", "🥉"]
        all_cards = "".join(
            _artist_card(r, medals[i] if i < 3 else f"#{i+1}", delay_base=i * 0.05)
            for i, r in enumerate(ranked)
        )
        st.markdown(all_cards, unsafe_allow_html=True)

        st.markdown(
            f'<div style="text-align:center;padding:16px;font-size:12px;color:#5a5a7a;">'
            f'🏆 &nbsp; En Uygun Aday: <b style="color:#00ff87">'
            f'{best["artist"].replace("_"," ")}</b> &nbsp;·&nbsp; '
            f'Londra Uyumluluğu: <b style="color:#00ff87">'
            f'{float(best["scores"]["Londra Uyumluluğu"]):.1f}/10</b></div>',
            unsafe_allow_html=True
        )

# ── TAB 3: KATALOG ────────────────────────────────────────────
with tab_catalog:
    cat_records = load_all()
    if not cat_records:
        st.markdown("""
        <div class="empty-state">
          <div class="empty-icon">◎</div>
          <div class="empty-title">Katalog boş</div>
          <div class="empty-sub">İlk analizini yaptığında sanatçılar burada görünür.</div>
          <span class="empty-cta">Keşfe Başla →</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="margin:4px 0 20px 0;">'
            '<div style="font-size:18px;font-weight:800;color:#E8EDF4;letter-spacing:-0.3px;">'
            '◎ Sanatçı Kataloğu</div>'
            '<div style="font-size:13px;color:#6B7280;margin-top:4px;">'
            'Tüm analizleri filtrele, karşılaştır ve raporlara hızlıca eriş.</div></div>',
            unsafe_allow_html=True,
        )

        # ── Filtreler ──────────────────────────────────────
        f1, f2, f3 = st.columns([2, 2, 2])
        with f1:
            score_filter = st.selectbox(
                "Skor Filtresi",
                ["Tümü", "⚡ 9.0+ (Sign Now)", "◎ 7.0–8.9 (Potansiyel)", "○ 7.0 altı"],
                key="cat_score_filter",
            )
        with f2:
            sort_by = st.selectbox(
                "Sıralama",
                ["Skora Göre (↓)", "Skora Göre (↑)", "Tarihe Göre (↓)", "İsme Göre (A→Z)"],
                key="cat_sort",
            )
        with f3:
            cat_search = st.text_input("", placeholder="🔍 Sanatçı ara...",
                                       key="cat_search", label_visibility="collapsed")

        # Filtre uygula
        filtered = list(cat_records)
        if score_filter == "⚡ 9.0+ (Sign Now)":
            filtered = [r for r in filtered if float(r["scores"]["Londra Uyumluluğu"]) >= 9.0]
        elif score_filter == "◎ 7.0–8.9 (Potansiyel)":
            filtered = [r for r in filtered
                        if 7.0 <= float(r["scores"]["Londra Uyumluluğu"]) < 9.0]
        elif score_filter == "○ 7.0 altı":
            filtered = [r for r in filtered if float(r["scores"]["Londra Uyumluluğu"]) < 7.0]
        if cat_search:
            filtered = [r for r in filtered
                        if cat_search.lower() in r["artist"].lower().replace("_", " ")]

        # Sıralama
        if sort_by == "Skora Göre (↓)":
            filtered.sort(key=lambda x: x["scores"]["Londra Uyumluluğu"], reverse=True)
        elif sort_by == "Skora Göre (↑)":
            filtered.sort(key=lambda x: x["scores"]["Londra Uyumluluğu"])
        elif sort_by == "Tarihe Göre (↓)":
            filtered.sort(key=lambda x: x.get("analyzed_at", ""), reverse=True)
        else:
            filtered.sort(key=lambda x: x["artist"])

        st.markdown(
            f'<div style="font-size:11px;color:#6B7280;margin-bottom:16px;">'
            f'{len(filtered)} sanatçı gösteriliyor</div>',
            unsafe_allow_html=True,
        )

        # ── Grid: 3 sütun ──────────────────────────────────
        cols = st.columns(3)
        for i, r in enumerate(filtered):
            name   = r["artist"].replace("_", " ")
            score  = float(r["scores"]["Londra Uyumluluğu"])
            date   = r.get("analyzed_at", "")[:10]
            trend  = r.get("trend_label") or ""
            trend_icon = {"Yükselen Yıldız": "⬆", "Düşüşte": "⬇", "Stabil": "→"}.get(trend, "")

            if score >= 9.5:
                hdr_bg, sc_color, badge = "linear-gradient(135deg,#FFD700,#FF9500)", "#000", "⭐ LEGENDARY"
            elif score >= 9.0:
                hdr_bg, sc_color, badge = "linear-gradient(135deg,#00FFAA,#00D4FF)", "#000", "⚡ SIGN NOW"
            elif score >= 7.0:
                hdr_bg, sc_color, badge = "linear-gradient(135deg,#1E2530,#21262D)", "#FFD700", "◎ Potansiyel"
            else:
                hdr_bg, sc_color, badge = "linear-gradient(135deg,#1a1010,#21262D)", "#FF4757", "○ Zayıf"

            with cols[i % 3]:
                st.markdown(
                    f'<div class="cat-card">'
                    f'<div class="cat-header" style="background:{hdr_bg};">'
                    f'<div>'
                    f'<div class="cat-score" style="color:{sc_color}">{score:.1f}</div>'
                    f'<div class="cat-name" style="color:{"#000" if score >= 9.0 else "#E8EDF4"}">{name}</div>'
                    f'</div>'
                    f'<div style="font-size:10px;font-weight:800;color:{"rgba(0,0,0,0.5)" if score >= 9.0 else "#6B7280"};'
                    f'letter-spacing:1px;text-align:right;">{badge}<br>{trend_icon}</div>'
                    f'</div>'
                    f'<div class="cat-body">'
                    f'<div class="cat-meta">Analiz: {date}</div>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if st.button("📄 Raporu Gör", key=f"cat_{r['artist']}_{i}",
                             use_container_width=True):
                    st.session_state.goto_report = r["artist"]
                    st.rerun()


# ── TAB 4: HUNTER BOT ─────────────────────────────────────────
with tab_bot:
    from modules.hunter import HASHTAG_CATEGORIES, run_hunter, _category_of, _smart_query

    bot_discover, bot_watchlist = st.tabs(["🔍 Yeni Sanatçı Keşfet", "📌 Takip & İzleme"])

    # ════════════════════════════════════════════════════════════
    # DISCOVERY MODE
    # ════════════════════════════════════════════════════════════
    with bot_discover:
        st.markdown(
            '<div style="margin:4px 0 20px 0;">'
            '<div style="font-size:18px;font-weight:700;color:#e8e8f4;">🔍 Discovery Mode</div>'
            '<div style="font-size:13px;color:#5a5a7a;margin-top:4px;">'
            'YouTube\'da seçtiğin hashtagleri tarar, hiç tanımadığın sanatçıları bulup '
            'AI ile puanlar ve veritabanına ekler.</div></div>',
            unsafe_allow_html=True,
        )

        # ── Hashtag seçici ────────────────────────────────────
        all_tags_flat = [h for cat in HASHTAG_CATEGORIES.values() for h in cat]
        tag_labels = {
            h: f"{h}  [{_category_of(h)}]"
            for h in all_tags_flat
        }
        disc_tags = st.multiselect(
            "Hangi hashtagleri tarayalım?",
            options=all_tags_flat,
            default=all_tags_flat[:5],
            format_func=lambda h: f"#{h}  ·  {_category_of(h)}",
            help="Seçilen her hashtag için YouTube'da Smart Query araması yapılır",
        )

        if disc_tags:
            # Smart Query önizleme (pill formatında)
            pills = "".join(
                f'<span style="display:inline-block;margin:3px 5px 3px 0;padding:4px 10px;'
                f'border-radius:20px;border:1px solid #1c1c30;font-size:11px;color:#5a5a7a;">'
                f'<b style="color:#00d4ff">#{t}</b>'
                f'<span style="color:#3a3a5a;margin:0 4px">→</span>'
                f'<span style="color:#e8e8f4">{_smart_query(t, _category_of(t))}</span>'
                f'</span>'
                for t in disc_tags
            )
            st.markdown(
                f'<div style="margin:8px 0 16px 0;line-height:2;">{pills}</div>',
                unsafe_allow_html=True,
            )

        d_col1, d_col2 = st.columns([2, 1])
        with d_col1:
            disc_max = st.slider(
                "Hashtag başına kaç video?", 1, 5, 3,
                help="Toplam API maliyeti = seçilen hashtag × bu sayı × 100 birim",
            )
        with d_col2:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            disc_count = len(disc_tags) * disc_max
            st.markdown(
                f'<div style="background:var(--bg2);border:1px solid var(--border);'
                f'border-radius:8px;padding:10px 14px;font-size:12px;">'
                f'<span style="color:#5a5a7a">Taranacak:</span> '
                f'<b style="color:#00ff87">~{disc_count} video</b><br>'
                f'<span style="color:#5a5a7a">API maliyeti:</span> '
                f'<b style="color:#facc15">~{len(disc_tags) * 100} birim</b>'
                f'</div>',
                unsafe_allow_html=True,
            )

        run_disc = st.button(
            "🔍  Yeni Sanatçıları Keşfet",
            type="primary",
            disabled=not disc_tags,
            use_container_width=True,
        )

        if run_disc:
            artists_before = {r["artist"] for r in load_all()}
            prog_bar = st.progress(0, text="🔍 YouTube derinliklerinde taranıyor...")
            log_lines = []

            def _disc_cb(msg: str):
                log_lines.append(msg)
                pct = min(int(len(log_lines) / max(len(disc_tags) * disc_max + 1, 1) * 100), 95)
                label = msg if len(msg) < 70 else msg[:67] + "..."
                prog_bar.progress(pct, text=label)

            with st.status("🔍 Keşif Modu aktif...", expanded=True) as disc_status:
                st.write("🔍 YouTube derinliklerinde taranıyor...")
                disc_stats = run_hunter(
                    hashtags=disc_tags,
                    max_yt_per_tag=disc_max,
                    use_instagram=False,
                    progress_cb=_disc_cb,
                )
                st.write("🤖 Llama 3.3 analizi tamamlandı")
                st.write("🚨 Yatırım sinyalleri değerlendiriliyor...")
                prog_bar.progress(100, text="✅ Tarama tamamlandı")
                n = disc_stats['analyzed']
                disc_status.update(
                    label=f"✅ Tamamlandı — {n} yeni sanatçı {'keşfedildi' if n else 'bulunamadı'}",
                    state="complete",
                )

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Taranan Video",  disc_stats["scanned"])
            m2.metric("Yeni Sanatçı",   disc_stats["analyzed"],
                      delta=f"+{disc_stats['analyzed']}" if disc_stats["analyzed"] else None)
            m3.metric("Elendi",         disc_stats["skipped"])
            m4.metric("Hata",           disc_stats["errors"])

            if disc_stats["analyzed"] > 0:
                # Yeni eklenen sanatçıları göster
                artists_after  = load_all()
                new_records    = [r for r in artists_after
                                  if r["artist"] not in artists_before]
                if new_records:
                    st.markdown(
                        '<div style="font-size:11px;color:#5a5a7a;letter-spacing:1.5px;'
                        'text-transform:uppercase;margin:20px 0 12px 0;">'
                        '✨ Yeni Keşfedilen Sanatçılar</div>',
                        unsafe_allow_html=True,
                    )
                    medals = ["🥇", "🥈", "🥉"]
                    all_cards = "".join(
                        _artist_card(r, medals[i] if i < 3 else "⭐", delay_base=i * 0.05)
                        for i, r in enumerate(
                            sorted(new_records,
                                   key=lambda x: x["scores"]["Londra Uyumluluğu"],
                                   reverse=True)
                        )
                    )
                    st.markdown(all_cards, unsafe_allow_html=True)
                st.rerun()
            else:
                st.markdown("""
                <div class="empty-state" style="padding:60px 20px">
                  <div class="empty-icon">🌐</div>
                  <div class="empty-title">Bu hashtaglerde yeni yetenek bulunamadı</div>
                  <div class="empty-sub">
                    Tüm videolar daha önce taranmış, zaten popüler veya yorum eşiğinin altında.<br>
                    Farklı hashtagler seç ya da "Video / Hashtag" sayısını artır.
                  </div>
                  <span class="empty-cta">Başka hashtagler dene →</span>
                </div>
                """, unsafe_allow_html=True)

        # ── Hashtag Performance (discovery tab'ında özet olarak) ─
        ht_data = get_hashtag_stats()
        if ht_data:
            with st.expander("📊  Hashtag Performance", expanded=False):
                cat_color = {"INSTRUMENT": "#00d4ff", "VIBE": "#00ff87", "INSTITUTION": "#a855f7"}
                rows_html = ""
                for row in ht_data:
                    score = row["avg_score"]
                    if score is None:
                        score_str, bar_color, bar_w = "—", "#333", 0
                    elif score >= 9:
                        score_str = f"<b style='color:#4ade80'>{score}</b>"
                        bar_color, bar_w = "#4ade80", int(score * 10)
                    elif score >= 7:
                        score_str = f"<b style='color:#facc15'>{score}</b>"
                        bar_color, bar_w = "#facc15", int(score * 10)
                    else:
                        score_str = f"<b style='color:#f87171'>{score}</b>"
                        bar_color, bar_w = "#f87171", int(score * 10)
                    cat      = row["category"]
                    last     = (row["last_scan"] or "")[:10]
                    cat_html = (
                        f'<span style="font-size:10px;padding:2px 7px;border-radius:6px;'
                        f'background:{cat_color.get(cat,"#555")}22;'
                        f'color:{cat_color.get(cat,"#aaa")};border:1px solid '
                        f'{cat_color.get(cat,"#555")}44;">{cat}</span>'
                    )
                    rows_html += (
                        f'<tr>'
                        f'<td style="padding:8px 10px;font-weight:600;color:#e8e8f4">#{row["hashtag"]}</td>'
                        f'<td style="padding:8px 10px;">{cat_html}</td>'
                        f'<td style="padding:8px 10px;text-align:center;color:#5a5a7a">{row["total_videos"]}</td>'
                        f'<td style="padding:8px 10px;text-align:center;color:#5a5a7a">{row["total_analyzed"]}</td>'
                        f'<td style="padding:8px 10px;text-align:center">'
                        f'<div style="display:flex;align-items:center;gap:8px;">'
                        f'<div style="flex:1;height:6px;background:#1c1c30;border-radius:3px;">'
                        f'<div style="width:{bar_w}%;height:100%;background:{bar_color};border-radius:3px;"></div>'
                        f'</div>{score_str}/10</div></td>'
                        f'<td style="padding:8px 10px;text-align:center;color:#5a5a7a;font-size:11px">{last}</td>'
                        f'</tr>'
                    )
                st.markdown(
                    f'<table style="width:100%;border-collapse:collapse;font-size:13px;">'
                    f'<thead><tr style="border-bottom:1px solid #1c1c30;">'
                    f'<th style="padding:6px 10px;text-align:left;color:#5a5a7a;font-size:11px">HASHTAG</th>'
                    f'<th style="padding:6px 10px;color:#5a5a7a;font-size:11px">KATEGORİ</th>'
                    f'<th style="padding:6px 10px;text-align:center;color:#5a5a7a;font-size:11px">VİDEO</th>'
                    f'<th style="padding:6px 10px;text-align:center;color:#5a5a7a;font-size:11px">ANALİZ</th>'
                    f'<th style="padding:6px 10px;text-align:center;color:#5a5a7a;font-size:11px">ORT. SKOR</th>'
                    f'<th style="padding:6px 10px;text-align:center;color:#5a5a7a;font-size:11px">SON TARAMA</th>'
                    f'</tr></thead><tbody>{rows_html}</tbody></table>',
                    unsafe_allow_html=True,
                )

    # ════════════════════════════════════════════════════════════
    # WATCHLIST & MONITORING
    # ════════════════════════════════════════════════════════════
    with bot_watchlist:
        st.markdown(
            '<div style="margin:4px 0 20px 0;">'
            '<div style="font-size:18px;font-weight:700;color:#e8e8f4;">📌 Takip & İzleme</div>'
            '<div style="font-size:13px;color:#5a5a7a;margin-top:4px;">'
            'Takip listesindekilerde yeni yorum çıkınca raporu otomatik günceller.</div></div>',
            unsafe_allow_html=True,
        )

        col_btn, col_info = st.columns([1, 2])
        with col_btn:
            if st.button("▶  Takip Listesini Güncelle", type="primary"):
                with st.spinner("Hunter Bot çalışıyor..."):
                    result = run_bot()
                st.success(f"Tamamlandı — {result['updated']}/{result['total']} güncellendi.")
        with col_info:
            st.markdown("""
            <div style="background:var(--bg2);border:1px solid var(--border);border-radius:10px;
                        padding:14px 18px;font-size:12px;color:#5a5a7a;line-height:1.8;">
              <code style="color:#00ff87">python3 modules/bot.py --hours 24</code> — sürekli mod<br>
              <code style="color:#00ff87">python3 modules/bot.py --once</code> — tek seferlik
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

        watchlist = get_watchlist()
        if not watchlist:
            st.markdown("""
            <div class="empty-state" style="padding:60px 40px;">
              <div class="empty-icon">📌</div>
              <div class="empty-title">Takip listesi boş</div>
              <div class="empty-sub">Bir YouTube analizi yapıp<br><b>Takip Listesine Ekle</b>'ye tıklayın.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="font-size:11px;color:#5a5a7a;letter-spacing:1.5px;'
                        f'text-transform:uppercase;margin-bottom:12px;">'
                        f'{len(watchlist)} Sanatçı Takip Ediliyor</div>', unsafe_allow_html=True)
            for entry in watchlist:
                c1, c2, c3 = st.columns([3, 2, 1])
                with c1:
                    st.markdown(
                        f'<div class="wl-name">{entry["artist_name"].replace("_"," ")}</div>'
                        f'<div class="wl-url">{entry["youtube_url"]}</div>',
                        unsafe_allow_html=True
                    )
                with c2:
                    last    = entry["last_check_date"]
                    checked = last[:16].replace("T", " ") if last else "Henüz kontrol edilmedi"
                    added   = entry["added_date"][:10]    if entry["added_date"] else ""
                    st.markdown(
                        f'<div class="wl-meta">Son kontrol: {checked}</div>'
                        f'<div class="wl-meta">Eklenme: {added}</div>',
                        unsafe_allow_html=True
                    )
                with c3:
                    if st.button("🗑", key=f"rm_{entry['youtube_url']}"):
                        remove_from_watchlist(entry["youtube_url"])
                        st.rerun()
                st.markdown('<hr style="border-color:#1c1c30;margin:8px 0;">', unsafe_allow_html=True)

        alerts = get_alerts(limit=10)
        if alerts:
            st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
            st.markdown('<div style="font-size:11px;color:#5a5a7a;letter-spacing:1.5px;'
                        'text-transform:uppercase;margin-bottom:12px;">🚨 Son Kritik Sinyaller</div>',
                        unsafe_allow_html=True)
            for a in alerts:
                icon  = "🟡" if a["signal_type"] == "HIGH_SCORE" else "🟢"
                label = "Yüksek Skor" if a["signal_type"] == "HIGH_SCORE" else "Yükselen"
                css   = "high" if a["signal_type"] == "HIGH_SCORE" else "rising"
                st.markdown(
                    f'<div class="alert-pill {css}">'
                    f'<div>{icon}</div>'
                    f'<div><div class="alert-artist">{a["artist_name"].replace("_"," ")}</div>'
                    f'<div class="alert-type">{label}</div></div>'
                    f'<div class="alert-time">{a["created_at"][:16].replace("T"," ")}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        log_path = Path("logs/bot.log")
        if log_path.exists():
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            with st.expander("📋 Bot Logları (son 50 satır)"):
                lines = log_path.read_text(encoding="utf-8").splitlines()
                st.code("\n".join(lines[-50:]), language=None)
