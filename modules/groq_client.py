import os
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
_client = Groq(api_key=os.environ["GROQ_API_KEY"])

_BASE_PROMPT = """
Sen Londra merkezli, 20 yıllık deneyime sahip bir Müzik A&R (Yetenek Avcısı) uzmanısın.
Anadolu ve Orta Doğu geleneksel enstrümanları ile Londra elektronik müzik sahnesi (Deep House, Techno, Afro-House) konusunda derin uzmanlığa sahipsin.
ÖNEMLİ: Puan verirken mutlaka "X/10" formatını kullan (örnek: 8/10).

SANATÇI: {artist_name}

{comments_block}

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
{trend_section}"""

_TREND_SECTION = """
7. TREND ANALİZİ:
   Son 3 aydaki yorumlarla daha eski yorumları tematik ve duygusal açıdan karşılaştır.
   - Son 3 Ay Özeti: [genel duygu tonu ve öne çıkan temalar]
   - Daha Eskiler Özeti: [genel duygu tonu ve öne çıkan temalar]
   - Momentum: [Yükselen Yıldız / Stabil / Düşüşte] — [tek cümle gerekçe]"""


def _call(prompt: str) -> str:
    response = _client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def analyze_artist(raw_comments: str, artist_name: str) -> str:
    comments_block = f"YORUMLAR:\n{raw_comments}"
    prompt = _BASE_PROMPT.format(
        artist_name=artist_name,
        comments_block=comments_block,
        trend_section="",
    )
    return _call(prompt)


def analyze_with_trend(recent_str: str, older_str: str, artist_name: str) -> tuple:
    recent_block = recent_str if recent_str else "(Bu dönemde yorum bulunamadı)"
    older_block = older_str if older_str else "(Bu dönemde yorum bulunamadı)"
    comments_block = (
        f"YORUMLAR — SON 3 AY ({len(recent_str.splitlines()) if recent_str else 0} yorum):\n"
        f"{recent_block}\n\n"
        f"YORUMLAR — DAHA ESKİLER ({len(older_str.splitlines()) if older_str else 0} yorum):\n"
        f"{older_block}"
    )
    prompt = _BASE_PROMPT.format(
        artist_name=artist_name,
        comments_block=comments_block,
        trend_section=_TREND_SECTION,
    )
    report_text = _call(prompt)
    trend_label = _extract_trend(report_text)
    return report_text, trend_label


def _extract_trend(text: str) -> str:
    m = re.search(r"Momentum:\s*(Yükselen Yıldız|Stabil|Düşüşte)", text, re.IGNORECASE)
    if m:
        label = m.group(1).strip()
        mapping = {
            "yükselen yıldız": "Yükselen Yıldız",
            "stabil": "Stabil",
            "düşüşte": "Düşüşte",
        }
        return mapping.get(label.lower(), label)
    return "Stabil"


def extract_scores(report_text: str) -> dict:
    scores = {"Karizma": 7, "Gizem": 7, "Sahne Enerjisi": 7, "Londra Uyumluluğu": 7}
    patterns = {
        "Karizma": r"Karizma[^0-9]*(\d+)/10",
        "Gizem": r"Gizem[^0-9]*(\d+)/10",
        "Sahne Enerjisi": r"Sahne Enerjisi[^0-9]*(\d+)/10",
        "Londra Uyumluluğu": r"LONDRA PAZARI UYUMLULUĞU[^0-9]*(\d+)/10",
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, report_text, re.IGNORECASE)
        if m:
            scores[key] = int(m.group(1))
    return scores
