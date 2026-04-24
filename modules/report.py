import re
from datetime import datetime
from pathlib import Path
from string import Template

from modules.chart import score_color, generate_radar_chart
from modules.config import REPORTS_DIR, TEMPLATES_DIR
from modules.database import load_all, save_analysis
from modules.groq_client import analyze_artist, analyze_with_trend, extract_scores


def _load_template(name: str) -> Template:
    return Template((TEMPLATES_DIR / name).read_text(encoding="utf-8"))


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


_TREND_CONFIG = {
    "Yükselen Yıldız": ("trend-rising",  "⬆"),
    "Stabil":           ("trend-stable",  "→"),
    "Düşüşte":          ("trend-declining","⬇"),
}


def build_artist_html(
    report_text: str,
    artist_name: str,
    scores: dict,
    chart_b64: str,
    trend_label: str = None,
) -> str:
    london = scores["Londra Uyumluluğu"]
    display_name = artist_name.replace("_", " ")

    persona_items = ""
    for label in ["Karizma", "Gizem", "Sahne Enerjisi"]:
        v = scores[label]
        persona_items += (
            f'<div class="persona-item">'
            f'<div class="p-label">{label}</div>'
            f'<div class="p-score" style="color:{score_color(v)}">{v}</div>'
            f"</div>"
        )

    if trend_label and trend_label in _TREND_CONFIG:
        css_class, icon = _TREND_CONFIG[trend_label]
        trend_badge = f'<div class="trend-badge {css_class}">{icon} {trend_label}</div>'
    else:
        trend_badge = ""

    return _load_template("artist_report.html").substitute(
        display_name=display_name,
        date=datetime.now().strftime("%d %B %Y, %H:%M"),
        year=datetime.now().year,
        london_score=london,
        badge_color=score_color(london),
        persona_items=persona_items,
        chart_b64=chart_b64,
        report_body=format_report_body(report_text),
        trend_badge=trend_badge,
    )


def build_summary_html(results: list = None) -> str:
    all_records = load_all()
    if not all_records:
        all_records = results or []
    ranked = sorted(all_records, key=lambda x: x["scores"]["Londra Uyumluluğu"], reverse=True)
    best = ranked[0]
    medals = ["🥇", "🥈", "🥉"]

    rows = ""
    for i, r in enumerate(ranked):
        s = r["scores"]
        medal = medals[i] if i < 3 else f"#{i + 1}"
        analyzed_at = r.get("analyzed_at", "")[:10]
        rows += (
            f"<tr>"
            f"<td>{medal}</td>"
            f'<td><a href="{r["artist"]}_rapor.html">{r["artist"].replace("_", " ")}</a></td>'
            f'<td style="color:{score_color(s["Karizma"])};text-align:center">{s["Karizma"]}/10</td>'
            f'<td style="color:{score_color(s["Gizem"])};text-align:center">{s["Gizem"]}/10</td>'
            f'<td style="color:{score_color(s["Sahne Enerjisi"])};text-align:center">{s["Sahne Enerjisi"]}/10</td>'
            f'<td style="color:{score_color(s["Londra Uyumluluğu"])};text-align:center;font-weight:700">'
            f'{s["Londra Uyumluluğu"]}/10</td>'
            f'<td style="color:#555;text-align:center;font-size:12px">{analyzed_at}</td>'
            f"</tr>"
        )

    return _load_template("summary_report.html").substitute(
        date=datetime.now().strftime("%d %B %Y"),
        year=datetime.now().year,
        best_name=best["artist"].replace("_", " "),
        best_score=best["scores"]["Londra Uyumluluğu"],
        table_rows=rows,
    )


def process_and_save(
    artist_name: str,
    raw_comments: str,
    recent_str: str = None,
    older_str: str = None,
) -> dict:
    if recent_str is not None and older_str is not None:
        report_text, trend_label = analyze_with_trend(recent_str, older_str, artist_name)
    else:
        report_text = analyze_artist(raw_comments, artist_name)
        trend_label = None

    scores = extract_scores(report_text)
    chart_b64 = generate_radar_chart(scores, artist_name)
    html = build_artist_html(report_text, artist_name, scores, chart_b64, trend_label)

    REPORTS_DIR.mkdir(exist_ok=True)
    out = REPORTS_DIR / f"{artist_name}_rapor.html"
    out.write_text(html, encoding="utf-8")
    print(f"  Kaydedildi → {out}")

    save_analysis(
        artist_name=artist_name,
        scores=scores,
        trend_label=trend_label,
        report_text=report_text,
        report_path=str(out),
    )

    summary_path = REPORTS_DIR / "_ozet_rapor.html"
    summary_path.write_text(build_summary_html(), encoding="utf-8")

    return {"artist": artist_name, "scores": scores}
