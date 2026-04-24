import base64
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def score_color(score: int) -> str:
    """9-10: SIGN NOW (yeşil) | 7-8: ortalama (sarı) | ≤6: yetersiz (kırmızı)"""
    if score >= 9:
        return "#4ade80"
    elif score >= 7:
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
    ax.set_title(artist_name.replace("_", " "), color="white", size=12, fontweight="bold", pad=20)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", facecolor="#1a1a2e", dpi=150)
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")
