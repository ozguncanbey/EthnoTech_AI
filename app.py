import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

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
for key, default in [("report_html", None), ("current_artist", None),
                     ("last_yt_url", None), ("last_yt_artist", None)]:
    if key not in st.session_state:
        st.session_state[key] = default


def _run_analysis(artist_name: str, raw_comments: str,
                  recent_str: str = None, older_str: str = None) -> dict:
    prev_scores = get_latest_scores(artist_name)  # sinyal karşılaştırması için

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
            artist_name=artist_name,
            scores=scores,
            trend_label=trend_label,
            report_text=report_text,
            report_path=str(out),
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
                    with st.spinner("📡 Video bilgileri alınıyor..."):
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

                    _run_analysis(artist_name, raw_comments, recent_str, older_str)
                    st.session_state.last_yt_url = url
                    st.session_state.last_yt_artist = artist_name
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
                    _run_analysis(artist_name, comments_input)
                    st.rerun()
                except Exception as e:
                    st.error(f"Hata: {e}")

    # ── Takip listesine ekle ──
    if st.session_state.last_yt_url:
        st.divider()
        artist_disp = (st.session_state.last_yt_artist or "").replace("_", " ")
        st.caption(f"Son analiz: **{artist_disp}**")
        if st.button("📌 Takip Listesine Ekle", key="watchlist_add"):
            add_to_watchlist(
                st.session_state.last_yt_artist,
                st.session_state.last_yt_url,
            )
            st.success(f"{artist_disp} takip listesine eklendi!")

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
tab_report, tab_compare, tab_watch = st.tabs(
    ["📄 Sanatçı Raporu", "📊 Kıyaslama Tablosu", "🎯 Hunter Bot"]
)

# Rapor sekmesi
with tab_report:
    if st.session_state.report_html:
        components.html(st.session_state.report_html, height=1500, scrolling=True)

        # Puan geçmişi grafiği
        artist = st.session_state.current_artist
        if artist:
            history = get_score_history(artist)
            if len(history) >= 2:
                st.markdown(f"#### 📈 {artist.replace('_', ' ')} — Puan Geçmişi")
                df_hist = pd.DataFrame([{
                    "Tarih":              h["analysis_date"][:10],
                    "Karizma":            h["karizma"],
                    "Gizem":              h["gizem"],
                    "Sahne Enerjisi":     h["sahne_enerjisi"],
                    "Londra Uyumluluğu":  h["londra_uyumlulugu"],
                } for h in history]).set_index("Tarih")
                st.line_chart(df_hist, height=250)
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

# Hunter Bot sekmesi
with tab_watch:
    st.subheader("🎯 Hunter Bot — Otomatik Takip")
    st.caption("Takip listesindeki sanatçılar yeni yorum aldığında raporu otomatik günceller.")

    col_run, col_info = st.columns([1, 3])
    with col_run:
        if st.button("▶ Bot'u Şimdi Çalıştır", type="primary"):
            with st.spinner("Hunter Bot çalışıyor..."):
                result = run_bot()
            st.success(
                f"Tamamlandı — {result['updated']}/{result['total']} sanatçı güncellendi."
            )
    with col_info:
        st.info(
            "Terminal'den sürekli çalıştırmak için:\n\n"
            "`python3 modules/bot.py --hours 24`\n\n"
            "Tek seferlik: `python3 modules/bot.py --once`"
        )

    st.divider()

    watchlist = get_watchlist()
    if not watchlist:
        st.markdown("""
        <div style="text-align:center;padding:60px;color:#555;">
          <div style="font-size:36px">📌</div>
          <p style="margin-top:12px">Takip listesi boş.<br>
          Sol panelden bir YouTube analizi yapıp <b>Takip Listesine Ekle</b>'ye tıklayın.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"**{len(watchlist)} sanatçı takip ediliyor**")
        for entry in watchlist:
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 1])
                with c1:
                    st.markdown(f"**{entry['artist_name'].replace('_', ' ')}**")
                    st.caption(entry["youtube_url"])
                with c2:
                    last = entry["last_check_date"]
                    checked = last[:16].replace("T", " ") if last else "Henüz kontrol edilmedi"
                    added = entry["added_date"][:10] if entry["added_date"] else ""
                    st.caption(f"Son kontrol: {checked}")
                    st.caption(f"Eklenme: {added}")
                with c3:
                    if st.button("🗑 Çıkar", key=f"rm_{entry['youtube_url']}"):
                        remove_from_watchlist(entry["youtube_url"])
                        st.rerun()

    # Kritik sinyaller
    alerts = get_alerts(limit=10)
    if alerts:
        st.divider()
        st.markdown("**🚨 Son Kritik Sinyaller**")
        for a in alerts:
            icon = "🔴" if a["signal_type"] == "HIGH_SCORE" else "📈"
            label = "Yüksek Skor" if a["signal_type"] == "HIGH_SCORE" else "Yükselen"
            st.info(
                f"{icon} **{a['artist_name'].replace('_', ' ')}** — {label}  \n"
                f"{a['created_at'][:16].replace('T', ' ')}"
            )

    # Log görüntüleyici
    log_path = Path("logs/bot.log")
    if log_path.exists():
        st.divider()
        with st.expander("📋 Bot Logları"):
            lines = log_path.read_text(encoding="utf-8").splitlines()
            st.code("\n".join(lines[-50:]), language=None)  # son 50 satır
