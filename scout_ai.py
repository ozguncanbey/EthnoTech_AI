import os
import sys
import re
import base64
import io
from pathlib import Path
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    print("Hata: .env dosyasında GROQ_API_KEY bulunamadı!")
    sys.exit(1)

client = Groq(api_key=api_key)

COMMENTS_DIR = Path("comments")
REPORTS_DIR = Path("Reports")


def analyze_artist(raw_comments: str, artist_name: str) -> str:
    prompt = f"""
Sen Londra merkezli, 20 yıllık deneyime sahip bir Müzik A&R (Yetenek Avcısı) uzmanısın.
Anadolu ve Orta Doğu geleneksel enstrümanları ile Londra elektronik müzik sahnesi (Deep House, Techno, Afro-House) konusunda derin uzmanlığa sahipsin.
Sana sunulan ham sosyal medya yorumlarını analiz et ve aşağıdaki formatta kapsamlı bir rapor hazırla.
ÖNEMLİ: Puan verirken mutlaka "X/10" formatını kullan (örnek: 8/10).

SANATÇI: {artist_name}

YORUMLAR:
{raw_comments}

═══════════════════════════════════════════════════
R A P O R
═══════════════════════════════════════════════════

1. SANATÇININ GÜÇLÜ YANLARI:
   - Müzikal güçler ve öne çıkan özellikler
   - Özgünlük faktörü

2. TEKNİK EKSİKLER:
   - Prodüksiyon ve mix sorunları
   - Geliştirmesi gereken alanlar

3. ENSTRÜMAN & SAHNE ANALİZİ:
   Yorumlarda geçen veya ima edilen geleneksel enstrümanları (bağlama, ud, ney, darbuka, kanun vb.) tespit et.
   Her enstrüman için ayrı ayrı değerlendir:
   a) Londra DEEP HOUSE sahnesindeki karşılığı ve füzyon potansiyeli
   b) Londra TECHNO sahnesindeki karşılığı ve füzyon potansiyeli
   c) Bu enstrümanı başarıyla kullanan referans sanatçılar (global örnekler)
   d) Londra'da hedef alınabilecek spesifik venue ve label önerileri

4. PERSONA ANALİZİ:
   - Karizma Puanı    (1-10): [puan]/10 — [gerekçe]
   - Gizem Faktörü    (1-10): [puan]/10 — [gerekçe]
   - Sahne Enerjisi   (1-10): [puan]/10 — [gerekçe]
   - Marka Kimliği: Sanatçının hikayesi ve imajı Londra pazarında nasıl konumlanmalı?
   - Hedef Kitle Profili: Londra'da bu sanatçıyı kim dinler, hangi etkinliklere gider?

5. LONDRA PAZARI UYUMLULUĞU (1-10): [puan]/10
   Gerekçe:

6. STRATEJİK TAVSİYE:
   - Kısa Vade  (0-6 ay): Öncelikli yapılacaklar
   - Orta Vade  (6-18 ay): Gelişim adımları
   - Uzun Vade  (18+ ay): Hedefler
   - En Kritik Aksiyon: Tek bir cümleyle en acil öneri
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def extract_scores(report_text: str) -> dict:
    defaults = {"Karizma": 7, "Gizem": 7, "Sahne Enerjisi": 7, "Londra Uyumluluğu": 7}
    patterns = {
        "Karizma": r"Karizma[^0-9]*(\d+)/10",
        "Gizem": r"Gizem[^0-9]*(\d+)/10",
        "Sahne Enerjisi": r"Sahne Enerjisi[^0-9]*(\d+)/10",
        "Londra Uyumluluğu": r"LONDRA PAZARI UYUMLULUĞU[^0-9]*(\d+)/10",
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, report_text, re.IGNORECASE)
        if m:
            defaults[key] = int(m.group(1))
    return defaults


def score_color(score: int) -> str:
    if score >= 8:
        return "#4ade80"
    elif score >= 6:
        return "#facc15"
    return "#f87171"


def generate_radar_chart(scores: dict, artist_name: str) -> str:
    labels = list(scores.keys())
    values = list(scores.values())
    values += values[:1]

    N = len(labels)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")

    ax.plot(angles, values, "o-", linewidth=2, color="#e94560")
    ax.fill(angles, values, alpha=0.25, color="#e94560")

    ax.set_ylim(0, 10)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, color="white", size=9, fontweight="bold")
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(["2", "4", "6", "8", "10"], color="#555", size=7)
    ax.grid(color="#444", alpha=0.4)
    ax.spines["polar"].set_color("#444")
    ax.set_title(artist_name, color="white", size=12, fontweight="bold", pad=20)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", facecolor="#1a1a2e", dpi=150)
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def format_report_body(text: str) -> str:
    lines = text.split("\n")
    html_lines = []
    in_list = False
    for line in lines:
        line = line.strip()
        if not line or line.startswith("═"):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("<br>")
            continue

        line = re.sub(
            r"(\d+)/10",
            lambda m: f'<span class="score" style="color:{score_color(int(m.group(1)))}">'
                      f"{m.group(1)}/10</span>",
            line,
        )

        if re.match(r"^\d+\.", line):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f'<h3 class="section-heading">{line}</h3>')
        elif line.startswith("- ") or line.startswith("• "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{line[2:]}</li>")
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<p>{line}</p>")

    if in_list:
        html_lines.append("</ul>")
    return "\n".join(html_lines)


def build_artist_html(report_text: str, artist_name: str, scores: dict, chart_b64: str) -> str:
    london = scores["Londra Uyumluluğu"]
    body = format_report_body(report_text)

    persona_items = ""
    for label in ["Karizma", "Gizem", "Sahne Enerjisi"]:
        v = scores[label]
        persona_items += f"""
        <div class="persona-item">
            <div class="p-label">{label}</div>
            <div class="p-score" style="color:{score_color(v)}">{v}</div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>EthnoTech AI Scout — {artist_name}</title>
<style>
  :root{{--bg:#0f0f1a;--card:#1a1a2e;--accent:#e94560;--text:#e0e0e0;--muted:#888;--border:#2a2a4a}}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;padding:40px 20px;line-height:1.75}}
  .container{{max-width:920px;margin:0 auto}}
  header{{border-left:4px solid var(--accent);padding:22px 26px;background:var(--card);border-radius:0 12px 12px 0;margin-bottom:32px}}
  .label{{color:var(--accent);font-size:11px;letter-spacing:3px;text-transform:uppercase;margin-bottom:6px}}
  header h1{{font-size:34px;font-weight:700}}
  .meta{{color:var(--muted);font-size:13px;margin-top:6px}}
  .score-badge{{display:inline-block;padding:5px 18px;border-radius:20px;font-size:17px;font-weight:700;
    background:rgba(255,255,255,.06);color:{score_color(london)};border:2px solid {score_color(london)};margin-top:12px}}
  .grid{{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-bottom:28px}}
  @media(max-width:620px){{.grid{{grid-template-columns:1fr}}}}
  .card{{background:var(--card);border-radius:12px;padding:24px;border:1px solid var(--border)}}
  .chart-card{{display:flex;align-items:center;justify-content:center}}
  .chart-card img{{width:100%;max-width:340px;border-radius:8px}}
  .persona-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:16px}}
  .persona-item{{background:rgba(255,255,255,.04);border-radius:8px;padding:14px;text-align:center}}
  .p-label{{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1px}}
  .p-score{{font-size:28px;font-weight:700;margin-top:4px}}
  .report-body{{background:var(--card);border-radius:12px;padding:32px;border:1px solid var(--border)}}
  .section-heading{{color:var(--accent);font-size:14px;font-weight:700;text-transform:uppercase;
    letter-spacing:1px;margin:26px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--border)}}
  p{{margin:5px 0}}
  ul{{margin:6px 0 6px 22px}}
  li{{margin-bottom:4px}}
  .score{{font-weight:700}}
  footer{{text-align:center;color:var(--muted);font-size:12px;margin-top:40px;
    padding-top:20px;border-top:1px solid var(--border)}}
</style>
</head>
<body>
<div class="container">
  <header>
    <div class="label">EthnoTech AI Scout — A&R Raporu</div>
    <h1>{artist_name}</h1>
    <div class="meta">Oluşturulma: {datetime.now().strftime("%d %B %Y, %H:%M")}</div>
    <div class="score-badge">Londra Pazarı: {london}/10</div>
  </header>

  <div class="grid">
    <div class="card">
      <div class="label">Persona Analizi</div>
      <div class="persona-grid">{persona_items}</div>
    </div>
    <div class="card chart-card">
      <img src="data:image/png;base64,{chart_b64}" alt="Radar Chart">
    </div>
  </div>

  <div class="report-body">{body}</div>

  <footer>EthnoTech AI Scout &nbsp;·&nbsp; Groq + Llama 3.3 70B &nbsp;·&nbsp; {datetime.now().year}</footer>
</div>
</body>
</html>"""


def build_summary_html(results: list) -> str:
    ranked = sorted(results, key=lambda x: x["scores"]["Londra Uyumluluğu"], reverse=True)
    best = ranked[0]
    medals = ["🥇", "🥈", "🥉"]

    rows = ""
    for i, r in enumerate(ranked):
        s = r["scores"]
        medal = medals[i] if i < 3 else f"#{i + 1}"
        lc = score_color(s["Londra Uyumluluğu"])
        rows += f"""
        <tr>
          <td>{medal}</td>
          <td><a href="{r['artist']}_rapor.html">{r['artist']}</a></td>
          <td style="color:{score_color(s['Karizma'])};text-align:center">{s['Karizma']}/10</td>
          <td style="color:{score_color(s['Gizem'])};text-align:center">{s['Gizem']}/10</td>
          <td style="color:{score_color(s['Sahne Enerjisi'])};text-align:center">{s['Sahne Enerjisi']}/10</td>
          <td style="color:{lc};text-align:center;font-weight:700">{s['Londra Uyumluluğu']}/10</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>EthnoTech AI Scout — Özet Rapor</title>
<style>
  body{{background:#0f0f1a;color:#e0e0e0;font-family:'Segoe UI',system-ui,sans-serif;padding:40px 20px}}
  .container{{max-width:880px;margin:0 auto}}
  .label{{color:#e94560;font-size:11px;letter-spacing:3px;text-transform:uppercase;margin-bottom:6px}}
  header{{border-left:4px solid #e94560;padding:22px 26px;background:#1a1a2e;border-radius:0 12px 12px 0;margin-bottom:32px}}
  header h1{{font-size:28px;font-weight:700}}
  .winner{{background:#1a1a2e;border-radius:12px;padding:32px;margin-bottom:28px;border:2px solid #e94560;text-align:center}}
  .winner h2{{color:#e94560;font-size:11px;letter-spacing:3px;text-transform:uppercase;margin-bottom:10px}}
  .winner .name{{font-size:38px;font-weight:700}}
  .winner .sub{{color:#888;margin-top:8px}}
  table{{width:100%;border-collapse:collapse;background:#1a1a2e;border-radius:12px;overflow:hidden}}
  th{{background:#16213e;padding:14px 16px;text-align:left;color:#888;font-size:11px;text-transform:uppercase;letter-spacing:1px}}
  td{{padding:14px 16px;border-bottom:1px solid #2a2a4a}}
  tr:last-child td{{border-bottom:none}}
  a{{color:#e94560;text-decoration:none}}
  footer{{text-align:center;color:#555;font-size:12px;margin-top:40px}}
</style>
</head>
<body>
<div class="container">
  <header>
    <div class="label">EthnoTech AI Scout</div>
    <h1>Özet Rapor — {datetime.now().strftime("%d %B %Y")}</h1>
  </header>
  <div class="winner">
    <h2>Londra Pazarı İçin En Uygun Aday</h2>
    <div class="name">{best['artist']}</div>
    <div class="sub">Londra Pazarı Uyumluluğu: {best['scores']['Londra Uyumluluğu']}/10</div>
  </div>
  <table>
    <thead>
      <tr>
        <th>#</th><th>Sanatçı</th>
        <th style="text-align:center">Karizma</th>
        <th style="text-align:center">Gizem</th>
        <th style="text-align:center">Sahne Enerjisi</th>
        <th style="text-align:center">Londra Uyumluluğu</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
  <footer>EthnoTech AI Scout &nbsp;·&nbsp; Groq + Llama 3.3 70B &nbsp;·&nbsp; {datetime.now().year}</footer>
</div>
</body>
</html>"""


def main():
    if not COMMENTS_DIR.exists():
        print(f"Hata: '{COMMENTS_DIR}' klasörü bulunamadı!")
        sys.exit(1)

    txt_files = sorted(COMMENTS_DIR.glob("*.txt"))
    if not txt_files:
        print(f"Hata: '{COMMENTS_DIR}' klasöründe .txt dosyası bulunamadı!")
        sys.exit(1)

    REPORTS_DIR.mkdir(exist_ok=True)
    results = []

    print(f"{len(txt_files)} sanatçı dosyası bulundu.\n")

    for txt_file in txt_files:
        artist_name = txt_file.stem
        print(f"Analiz ediliyor: {artist_name}...")
        raw_comments = txt_file.read_text(encoding="utf-8")
        try:
            report_text = analyze_artist(raw_comments, artist_name)
            scores = extract_scores(report_text)
            chart_b64 = generate_radar_chart(scores, artist_name)
            html = build_artist_html(report_text, artist_name, scores, chart_b64)

            out = REPORTS_DIR / f"{artist_name}_rapor.html"
            out.write_text(html, encoding="utf-8")
            print(f"  Kaydedildi → {out}")
            results.append({"artist": artist_name, "scores": scores})
        except Exception as e:
            print(f"  Hata ({artist_name}): {e}")

    if results:
        summary_path = REPORTS_DIR / "_ozet_rapor.html"
        summary_path.write_text(build_summary_html(results), encoding="utf-8")
        best = max(results, key=lambda x: x["scores"]["Londra Uyumluluğu"])
        print(f"\nÖzet rapor → {summary_path}")
        print(f"En uygun aday: {best['artist']} ({best['scores']['Londra Uyumluluğu']}/10)")

    print("\nTamamlandı.")


if __name__ == "__main__":
    main()
