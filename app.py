import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

from modules.config import REPORTS_DIR
from modules.database import load_all
from modules.report import process_and_save
from modules.youtube_client import fetch_youtube_data, split_by_date

st.set_page_config(
    page_title="EthnoTech AI Scout",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  [data-testid="stSidebar"] { background:#0f0f1a; }
  [data-testid="stSidebar"] * { color:#e0e0e0 !important; }
  .stButton > button {
    width:100%; background:#e94560; color:#fff; border:none;
    border-radius:8px; font-weight:700; padding:10px;
  }
  .stButton > button:hover { background:#c73652; }
  .artist-btn > button {
    background:transparent !important; color:#e0e0e0 !important;
    border:1px solid #2a2a4a !important; margin-bottom:4px;
    text-align:left !important; font-size:13px !important;
  }
  .artist-btn > button:hover { border-color:#e94560 !important; }
  div[data-testid="stTabs"] button { font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ── Session State ──────────────────────────────────────────────
for key, default in [("report_html", None), ("current_artist", None)]:
    if key not in st.session_state:
        st.session_state[key] = default


def _run_analysis(artist_name: str, raw_comments: str,
                  recent_str: str = None, older_str: str = None) -> None:
    result = process_and_save(artist_name, raw_comments, recent_str, older_str)
    html_path = REPORTS_DIR / f"{artist_name}_rapor.html"
    if html_path.exists():
        st.session_state.report_html = html_path.read_text(encoding="utf-8")
        st.session_state.current_artist = artist_name
    return result


def _load_artist_report(artist_name: str) -> None:
    html_path = REPORTS_DIR / f"{artist_name}_rapor.html"
    if html_path.exists():
        st.session_state.report_html = html_path.read_text(encoding="utf-8")
        st.session_state.current_artist = artist_name


# ── SIDEBAR ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎵 EthnoTech AI Scout")
    st.caption("A&R Intelligence Platform")
    st.divider()

    mode = st.radio("Analiz Modu", ["YouTube Linki", "Manuel Giriş"],
                    label_visibility="collapsed")

    # ── YouTube modu ──
    if mode == "YouTube Linki":
        url = st.text_input("YouTube URL",
                            placeholder="https://youtube.com/watch?v=...")
        artist_override = st.text_input("Sanatçı Adı (opsiyonel)",
                                        placeholder="Boş bırakırsan video başlığı kullanılır")

        if st.button("Analiz Başlat", key="yt_btn"):
            if not url.strip():
                st.error("Lütfen bir YouTube linki girin.")
            else:
                try:
                    with st.spinner("Video bilgileri alınıyor..."):
                        artist_name, comments_list, title = fetch_youtube_data(url)

                    if artist_override.strip():
                        artist_name = artist_override.strip().replace(" ", "_")

                    recent_str, older_str = split_by_date(comments_list)
                    raw_comments = "\n".join(f"- {c['text']}" for c in comments_list)
                    recent_count = len(recent_str.splitlines()) if recent_str else 0
                    older_count = len(older_str.splitlines()) if older_str else 0

                    st.info(
                        f"**{title}**\n\n"
                        f"Son 3 ay: **{recent_count}** yorum  \n"
                        f"Daha eskiler: **{older_count}** yorum"
                    )

                    with st.spinner("Analiz yapılıyor..."):
                        _run_analysis(artist_name, raw_comments, recent_str, older_str)

                    st.success("Analiz tamamlandı!")
                    st.rerun()

                except Exception as e:
                    st.error(f"Hata: {e}")

    # ── Manuel giriş modu ──
    else:
        artist_name_input = st.text_input("Sanatçı Adı",
                                          placeholder="Mehmet Aslan")
        comments_input = st.text_area(
            "Yorumlar (her satıra bir yorum)",
            height=220,
            placeholder="- Ritim duygusu inanılmaz...\n- Ud kullanımı çok özgün..."
        )

        if st.button("Analiz Başlat", key="manual_btn"):
            if not artist_name_input.strip() or not comments_input.strip():
                st.error("Sanatçı adı ve en az bir yorum zorunlu.")
            else:
                try:
                    artist_name = artist_name_input.strip().replace(" ", "_")
                    with st.spinner("Analiz yapılıyor..."):
                        _run_analysis(artist_name, comments_input)
                    st.success("Analiz tamamlandı!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Hata: {e}")

    # ── Kayıtlı sanatçılar listesi ──
    st.divider()
    records = load_all()
    if records:
        st.markdown("**Kayıtlı Sanatçılar**")
        ranked = sorted(records,
                        key=lambda x: x["scores"]["Londra Uyumluluğu"],
                        reverse=True)
        for r in ranked:
            display = r["artist"].replace("_", " ")
            score = r["scores"]["Londra Uyumluluğu"]
            with st.container():
                st.markdown('<div class="artist-btn">', unsafe_allow_html=True)
                if st.button(f"{display}  ·  {score}/10", key=f"list_{r['artist']}"):
                    _load_artist_report(r["artist"])
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)


# ── ANA ALAN ───────────────────────────────────────────────────
tab_report, tab_compare = st.tabs(["📄 Sanatçı Raporu", "📊 Kıyaslama Tablosu"])

# Rapor sekmesi
with tab_report:
    if st.session_state.report_html:
        components.html(st.session_state.report_html, height=1500, scrolling=True)
    else:
        st.markdown("""
        <div style="text-align:center;padding:100px 40px;color:#555;">
          <div style="font-size:48px;margin-bottom:16px;">🎵</div>
          <h2 style="color:#888;font-weight:600;">Henüz rapor seçilmedi</h2>
          <p style="color:#555;margin-top:8px;">
            Sol panelden bir YouTube linki girin veya kayıtlı sanatçıya tıklayın.
          </p>
        </div>
        """, unsafe_allow_html=True)

# Kıyaslama sekmesi
with tab_compare:
    records = load_all()

    if not records:
        st.info("Henüz analiz yapılmadı. Sol panelden bir analiz başlatın.")
    else:
        ranked = sorted(records,
                        key=lambda x: x["scores"]["Londra Uyumluluğu"],
                        reverse=True)
        best = ranked[0]

        # Özet metrikler
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Toplam Sanatçı", len(records))
        with col2:
            st.metric("En Yüksek Puan",
                      f"{best['scores']['Londra Uyumluluğu']}/10",
                      best["artist"].replace("_", " "))
        with col3:
            avg = sum(r["scores"]["Londra Uyumluluğu"] for r in records) / len(records)
            st.metric("Ortalama Londra Puanı", f"{avg:.1f}/10")

        st.divider()

        # İnteraktif tablo
        medals = ["🥇", "🥈", "🥉"]
        rows = []
        for i, r in enumerate(ranked):
            s = r["scores"]
            rows.append({
                "Sıra": medals[i] if i < 3 else f"#{i + 1}",
                "Sanatçı": r["artist"].replace("_", " "),
                "Karizma": s["Karizma"],
                "Gizem": s["Gizem"],
                "Sahne Enerjisi": s["Sahne Enerjisi"],
                "Londra Uyumluluğu": s["Londra Uyumluluğu"],
                "Tarih": r.get("analyzed_at", "")[:10],
            })

        df = pd.DataFrame(rows)

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            height=min(80 + len(rows) * 35, 500),
            column_config={
                "Sıra": st.column_config.TextColumn("", width="small"),
                "Sanatçı": st.column_config.TextColumn("Sanatçı"),
                "Karizma": st.column_config.ProgressColumn(
                    "Karizma", min_value=0, max_value=10, format="%d/10"),
                "Gizem": st.column_config.ProgressColumn(
                    "Gizem", min_value=0, max_value=10, format="%d/10"),
                "Sahne Enerjisi": st.column_config.ProgressColumn(
                    "Sahne Enerjisi", min_value=0, max_value=10, format="%d/10"),
                "Londra Uyumluluğu": st.column_config.ProgressColumn(
                    "Londra Uyumluluğu", min_value=0, max_value=10, format="%d/10"),
                "Tarih": st.column_config.TextColumn("Tarih", width="small"),
            },
        )

        st.success(
            f"🏆 En uygun aday: **{best['artist'].replace('_', ' ')}**"
            f"  —  Londra Uyumluluğu: {best['scores']['Londra Uyumluluğu']}/10"
        )
