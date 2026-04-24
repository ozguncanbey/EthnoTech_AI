import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from pathlib import Path

from modules.alerts import process_signals
from modules.bot import run_bot
from modules.chart import generate_radar_chart
from modules.config import REPORTS_DIR
from modules.database import (add_to_watchlist, get_alerts, get_latest_scores,
                               get_score_history, get_watchlist, load_all,
                               remove_from_watchlist, save_analysis)
from modules.groq_client import analyze_artist, analyze_with_trend, extract_scores
from modules.report import build_artist_html, build_summary_html
from modules.youtube_client import fetch_youtube_data, split_by_date

st.set_page_config(
    page_title="EthnoTech AI Scout",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── LUXURY CSS ────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
  --bg:      #07070f;
  --bg2:     #0e0e1a;
  --bg3:     #161625;
  --accent:  #00ff87;
  --gold:    #ffd700;
  --blue:    #00d4ff;
  --purple:  #a855f7;
  --pink:    #ec4899;
  --red:     #ff4757;
  --text:    #e8e8f4;
  --muted:   #5a5a7a;
  --border:  #1c1c30;
  --grad:    linear-gradient(135deg, #00ff87, #00d4ff);
  --grad-g:  linear-gradient(90deg,  #00ff87, #00d4ff);
  --grad-p:  linear-gradient(90deg,  #a855f7, #ec4899);
  --grad-o:  linear-gradient(90deg,  #ffd700, #ff9500);
  --grad-b:  linear-gradient(90deg,  #00d4ff, #0080ff);
}

html, body, [data-testid="stApp"] {
  background: var(--bg) !important;
  color: var(--text) !important;
  font-family: 'Inter', sans-serif !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg2); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

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
  border-radius: 8px !important;
}
[data-testid="stSidebar"] [data-testid="stTextInput"] input:focus,
[data-testid="stSidebar"] textarea:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 1px var(--accent) !important;
}

/* ── Tabs ── */
div[data-testid="stTabs"] {
  border-bottom: 1px solid var(--border);
}
div[data-testid="stTabs"] button {
  color: var(--muted) !important;
  font-weight: 600 !important;
  font-size: 14px !important;
  letter-spacing: 0.3px !important;
  padding: 10px 20px !important;
  transition: color 0.2s !important;
}
div[data-testid="stTabs"] button:hover { color: var(--text) !important; }
div[data-testid="stTabs"] button[aria-selected="true"] {
  color: var(--accent) !important;
  border-bottom: 2px solid var(--accent) !important;
}

/* ── Buttons ── */
.stButton > button {
  background: var(--grad) !important;
  color: #000 !important;
  border: none !important;
  border-radius: 8px !important;
  font-weight: 700 !important;
  font-size: 13px !important;
  letter-spacing: 0.5px !important;
  width: 100% !important;
  padding: 10px 16px !important;
  transition: opacity 0.2s, transform 0.15s !important;
}
.stButton > button:hover {
  opacity: 0.88 !important;
  transform: translateY(-1px) !important;
}

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
}
.sb-artist > button:hover {
  border-color: var(--accent) !important;
  color: var(--accent) !important;
}

/* ── st.metric override ── */
[data-testid="stMetric"] {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 18px 20px !important;
}
[data-testid="stMetricValue"] { color: var(--text) !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { color: var(--muted) !important; font-size: 12px !important; }

/* ── Divider ── */
hr { border-color: var(--border) !important; }

/* ── st.info / st.success / st.error ── */
[data-testid="stAlert"] {
  background: var(--bg3) !important;
  border-radius: 10px !important;
  border-left-color: var(--accent) !important;
}

/* ── LIVE PULSE ── */
.live-badge {
  position: fixed;
  top: 14px; right: 18px;
  z-index: 9999;
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(0,255,135,0.08);
  border: 1px solid rgba(0,255,135,0.25);
  border-radius: 20px;
  padding: 6px 14px;
  font-size: 11px;
  font-weight: 700;
  color: var(--accent);
  letter-spacing: 1.5px;
  text-transform: uppercase;
  backdrop-filter: blur(8px);
}
.pulse-dot {
  width: 8px; height: 8px;
  background: var(--accent);
  border-radius: 50%;
  animation: pulse-ring 2s ease-in-out infinite;
}
@keyframes pulse-ring {
  0%   { box-shadow: 0 0 0 0 rgba(0,255,135,0.8); }
  70%  { box-shadow: 0 0 0 9px rgba(0,255,135,0); }
  100% { box-shadow: 0 0 0 0 rgba(0,255,135,0); }
}

/* ── MAIN HEADER ── */
.main-header {
  padding: 32px 0 24px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 28px;
}
.brand-row {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 6px;
}
.brand-icon {
  font-size: 28px;
  background: var(--grad);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.brand-title {
  font-size: 26px;
  font-weight: 800;
  letter-spacing: -0.5px;
  background: var(--grad);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.brand-sub {
  font-size: 12px;
  color: var(--muted);
  letter-spacing: 2px;
  text-transform: uppercase;
  margin-left: 42px;
}

/* ── ARTIST CARDS ── */
.artist-card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px 28px;
  margin-bottom: 16px;
  transition: border-color 0.25s, transform 0.2s, box-shadow 0.25s;
  cursor: default;
}
.artist-card:hover {
  border-color: rgba(0,255,135,0.4);
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(0,255,135,0.06);
}
.card-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 22px;
}
.card-rank { font-size: 22px; min-width: 32px; }
.card-name {
  flex: 1;
  font-size: 19px;
  font-weight: 700;
  color: var(--text);
}
.card-london {
  font-size: 24px;
  font-weight: 800;
  background: var(--grad);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.card-date {
  font-size: 11px;
  color: var(--muted);
  margin-left: 8px;
  align-self: flex-end;
  padding-bottom: 3px;
}
.card-trend {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 12px;
  letter-spacing: 0.5px;
}
.trend-r { background: rgba(0,255,135,0.12); color: #00ff87; border: 1px solid rgba(0,255,135,0.3); }
.trend-s { background: rgba(255,215,0,0.12);  color: #ffd700; border: 1px solid rgba(255,215,0,0.3); }
.trend-d { background: rgba(255,71,87,0.12);  color: #ff4757; border: 1px solid rgba(255,71,87,0.3); }

/* ── METRIC BARS ── */
.metric-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}
.metric-label {
  width: 140px;
  font-size: 11px;
  font-weight: 600;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.8px;
  flex-shrink: 0;
}
.metric-track {
  flex: 1;
  height: 5px;
  background: var(--bg3);
  border-radius: 3px;
  overflow: hidden;
}
.metric-fill {
  height: 100%;
  border-radius: 3px;
  width: 0;
  animation: fillBar 1.1s cubic-bezier(.4,0,.2,1) forwards;
}
.mf-green  { background: var(--grad-g); }
.mf-blue   { background: var(--grad-b); }
.mf-orange { background: var(--grad-o); }
.mf-purple { background: var(--grad-p); }
@keyframes fillBar { to { width: var(--w); } }
.metric-val {
  width: 32px;
  text-align: right;
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
  flex-shrink: 0;
}

/* ── EMPTY STATE ── */
.empty-state {
  text-align: center;
  padding: 100px 40px;
  color: var(--muted);
}
.empty-icon { font-size: 52px; margin-bottom: 18px; }
.empty-title { font-size: 20px; font-weight: 700; color: #3a3a5c; margin-bottom: 8px; }
.empty-sub { font-size: 14px; color: var(--muted); }

/* ── WATCHLIST CARD ── */
.wl-card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 16px;
}
.wl-name { font-weight: 700; font-size: 15px; color: var(--text); }
.wl-url  { font-size: 11px; color: var(--muted); margin-top: 2px; }
.wl-meta { font-size: 11px; color: var(--muted); }

/* ── ALERT PILL ── */
.alert-pill {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: 10px;
  padding: 12px 16px;
  margin-bottom: 8px;
}
.alert-pill.rising { border-left-color: #00ff87; }
.alert-pill.high   { border-left-color: #ffd700; }
.alert-artist { font-weight: 700; font-size: 14px; }
.alert-type   { font-size: 11px; color: var(--muted); }
.alert-time   { margin-left: auto; font-size: 11px; color: var(--muted); }
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
                     ("last_yt_url", None), ("last_yt_artist", None)]:
    if key not in st.session_state:
        st.session_state[key] = default


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
        pct = val * 10
        return (
            f'<div class="metric-row">'
            f'<span class="metric-label">{label}</span>'
            f'<div class="metric-track">'
            f'<div class="metric-fill {css_class}" style="--w:{pct}%;animation-delay:{delay:.2f}s"></div>'
            f'</div>'
            f'<span class="metric-val">{val}</span>'
            f'</div>'
        )

    bars = (
        bar("Karizma",           s["Karizma"],           "mf-green",  delay_base + 0.0) +
        bar("Gizem",             s["Gizem"],             "mf-blue",   delay_base + 0.12) +
        bar("Sahne Enerjisi",    s["Sahne Enerjisi"],    "mf-orange", delay_base + 0.24) +
        bar("Londra Uyumluluğu", s["Londra Uyumluluğu"],"mf-purple", delay_base + 0.36)
    )

    return f"""
    <div class="artist-card">
      <div class="card-header">
        <div class="card-rank">{rank}</div>
        <div class="card-name">{name}</div>
        {trend_html}
        <div class="card-london">{s['Londra Uyumluluğu']}/10</div>
        <div class="card-date">{date}</div>
      </div>
      {bars}
    </div>
    """


# ── Analysis runner ───────────────────────────────────────────
def _run_analysis(artist_name: str, raw_comments: str,
                  recent_str: str = None, older_str: str = None) -> dict:
    prev_scores = get_latest_scores(artist_name)

    with st.status("Analiz başlatılıyor...", expanded=True) as status:
        if recent_str is not None and older_str is not None:
            st.write("🤖 Trend analizi için AI çağrılıyor (15-20 sn)...")
            report_text, trend_label = analyze_with_trend(recent_str, older_str, artist_name)
        else:
            st.write("🤖 AI analizi yapılıyor (15-20 sn)...")
            report_text = analyze_artist(raw_comments, artist_name)
            trend_label = None

        st.write("📊 Puanlar çıkarılıyor ve radar grafiği oluşturuluyor...")
        scores = extract_scores(report_text)
        chart_b64 = generate_radar_chart(scores, artist_name)
        html = build_artist_html(report_text, artist_name, scores, chart_b64, trend_label)

        st.write("💾 Rapor ve veritabanı kaydediliyor...")
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
        status.update(label="✅ Analiz tamamlandı!", state="complete", expanded=False)

    signals = process_signals(artist_name, scores, prev_scores)
    for sig in signals:
        st.toast(sig["message"].replace("<b>", "**").replace("</b>", "**"), icon="🚨")

    return {"artist": artist_name, "scores": scores}


def _load_artist_report(artist_name: str) -> None:
    html_path = REPORTS_DIR / f"{artist_name}_rapor.html"
    if html_path.exists():
        st.session_state.report_html = html_path.read_text(encoding="utf-8")
        st.session_state.current_artist = artist_name


# ── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:20px 0 12px;">
      <div style="font-size:20px;font-weight:800;background:linear-gradient(135deg,#00ff87,#00d4ff);
                  -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
        ◈ EthnoTech AI Scout
      </div>
      <div style="font-size:10px;color:#5a5a7a;letter-spacing:2px;margin-top:4px;">
        A&R INTELLIGENCE PLATFORM
      </div>
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
                    _run_analysis(artist_name, raw_comments, recent_str, older_str)
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
        st.markdown('<div style="font-size:11px;color:#5a5a7a;letter-spacing:1.5px;'
                    'text-transform:uppercase;margin-bottom:8px;">Sanatçılar</div>',
                    unsafe_allow_html=True)
        ranked_sb = sorted(records, key=lambda x: x["scores"]["Londra Uyumluluğu"], reverse=True)
        for r in ranked_sb:
            disp  = r["artist"].replace("_", " ")
            score = r["scores"]["Londra Uyumluluğu"]
            st.markdown('<div class="sb-artist">', unsafe_allow_html=True)
            if st.button(f"{disp}  ·  {score}/10", key=f"sb_{r['artist']}"):
                _load_artist_report(r["artist"])
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

# ── TABS ──────────────────────────────────────────────────────
tab_report, tab_radar, tab_bot = st.tabs(
    ["📄 Sanatçı Raporu", "◈ A&R Radar", "🎯 Hunter Bot"]
)

# ── TAB 1: SANATÇI RAPORU ─────────────────────────────────────
with tab_report:
    if st.session_state.report_html:
        components.html(st.session_state.report_html, height=1500, scrolling=True)

        artist = st.session_state.current_artist
        if artist:
            history = get_score_history(artist)
            if len(history) >= 2:
                st.markdown(
                    f'<div style="font-size:13px;font-weight:700;color:#5a5a7a;'
                    f'letter-spacing:1.5px;text-transform:uppercase;margin:24px 0 12px;">'
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
        <div class="empty-state">
          <div class="empty-icon">◈</div>
          <div class="empty-title">Henüz rapor seçilmedi</div>
          <div class="empty-sub">Sol panelden bir YouTube linki girin<br>
          veya kayıtlı bir sanatçıya tıklayın.</div>
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
            st.metric("En Yüksek Puan", f"{best['scores']['Londra Uyumluluğu']}/10",
                      best["artist"].replace("_", " "))
        with c3:
            st.metric("Ortalama Puan", f"{avg:.1f}/10")
        with c4:
            alerts = get_alerts(limit=5)
            st.metric("Aktif Sinyal", len(alerts), "🚨" if alerts else "")

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

        # ── Artist cards ──
        medals = ["🥇", "🥈", "🥉"]
        for i, r in enumerate(ranked):
            rank_label = medals[i] if i < 3 else f"#{i+1}"
            st.markdown(_artist_card(r, rank_label, delay_base=i * 0.05),
                        unsafe_allow_html=True)

        st.markdown(
            f'<div style="text-align:center;padding:16px;font-size:12px;color:#5a5a7a;">'
            f'🏆 &nbsp; En Uygun Aday: <b style="color:#00ff87">'
            f'{best["artist"].replace("_"," ")}</b> &nbsp;·&nbsp; '
            f'Londra Uyumluluğu: <b style="color:#00ff87">'
            f'{best["scores"]["Londra Uyumluluğu"]}/10</b></div>',
            unsafe_allow_html=True
        )

# ── TAB 3: HUNTER BOT ─────────────────────────────────────────
with tab_bot:
    st.markdown("""
    <div style="margin-bottom:20px;">
      <div style="font-size:18px;font-weight:700;color:#e8e8f4;">🎯 Hunter Bot</div>
      <div style="font-size:13px;color:#5a5a7a;margin-top:4px;">
        Takip listesindeki sanatçıları otomatik izler, yeni yorumlar geldiğinde raporu günceller.
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_btn, col_info = st.columns([1, 2])
    with col_btn:
        if st.button("▶  Bot'u Şimdi Çalıştır", type="primary"):
            with st.spinner("Hunter Bot çalışıyor..."):
                result = run_bot()
            st.success(f"Tamamlandı — {result['updated']}/{result['total']} sanatçı güncellendi.")
    with col_info:
        st.markdown("""
        <div style="background:var(--bg2);border:1px solid var(--border);border-radius:10px;
                    padding:14px 18px;font-size:12px;color:#5a5a7a;line-height:1.8;">
          <code style="color:#00ff87">python3 modules/bot.py --hours 24</code> — sürekli mod<br>
          <code style="color:#00ff87">python3 modules/bot.py --once</code> — tek seferlik
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Watchlist ──
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
                last = entry["last_check_date"]
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

    # ── Alerts ──
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

    # ── Log viewer ──
    log_path = Path("logs/bot.log")
    if log_path.exists():
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        with st.expander("📋 Bot Logları (son 50 satır)"):
            lines = log_path.read_text(encoding="utf-8").splitlines()
            st.code("\n".join(lines[-50:]), language=None)
