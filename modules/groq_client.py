import os
import re
from groq import Groq
from dotenv import load_dotenv
from modules.config import get_secret

load_dotenv()
_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        key = get_secret("GROQ_API_KEY")
        if not key:
            raise ValueError("GROQ_API_KEY bulunamadı. .env veya Streamlit secrets'ı kontrol edin.")
        _client = Groq(api_key=key)
    return _client

_BASE_PROMPT = """
Sen EthnoTech Intelligence platformunun baş uzmanısın: Londra merkezli, 20 yıllık deneyime sahip bir Ethno-Tech Specialist ve A&R direktörüsün.
Uzmanlığın: Anadolu, Orta Doğu ve Akdeniz geleneksel müzik kültürlerini Londra'nın ileri elektronik sahnesiyle kesişen global türlere taşımak.
Takip ettiğin sahneler: Organic House, Anatolian Psych, Desert Tech, Afro-Anatolian Fusion, Dark Folk Electronic, Neo-Sufi House.
Referans noktaların: Bedouin, Innervisions, Crosstown Rebels, Khruangbin, Acid Arab, Bosphorus Underground.
ÖNEMLİ: Puan verirken mutlaka "X/10" formatını kullan (örnek: 8/10).

SANATÇI: {artist_name}

{comments_block}

═══════════════════════════════════════════════════
E T H N O - T E C H   R A P O R U
═══════════════════════════════════════════════════

1. SANATÇININ GÜÇLÜ YANLARI:
   - Müzikal kimlik ve özgünlük faktörü
   - Ethno-Tech perspektifinden öne çıkan unsurlar

2. TEKNİK EKSİKLER:
   - Prodüksiyon, mix ve mastering sorunları
   - Global sahneye hazırlık açısından geliştirmesi gereken alanlar

3. ENSTRÜMAN & GLOBAL TÜR ANALİZİ:
   Yorumlarda geçen veya ima edilen geleneksel enstrümanları (bağlama, ud, ney, darbuka, kanun, saz vb.) tespit et.
   Her enstrüman için değerlendir:
   a) ORGANIC HOUSE sahnesine entegrasyon potansiyeli (Innervisions, Crosstown Rebels tarzı)
   b) ANATOLIAN PSYCH veya DESERT TECH çerçevesine uyumu
   c) DARK FOLK ELECTRONIC veya NEO-SUFİ HOUSE'a köprü kurabilir mi?
   d) Bu sesi başarıyla kullanan global referans sanatçılar (Bedouin, Acid Arab, Khruangbin vb.)
   e) Londra'da hedef alınabilecek spesifik venue ve label önerileri

4. PERSONA ANALİZİ:
   - Karizma Puanı    (1-10): [puan]/10 — [gerekçe]
   - Gizem Faktörü    (1-10): [puan]/10 — [gerekçe]
   - Sahne Enerjisi   (1-10): [puan]/10 — [gerekçe]
   - Ethno-Tech Marka Kimliği: Sanatçı global pazarda nasıl konumlanmalı? Hangi estetik ve hikaye?
   - Hedef Kitle Profili: Londra'da bu sanatçıyı kim dinler? (Boiler Room kitlesi mi, festival kitlesi mi?)

5. LONDRA PAZARI UYUMLULUĞU (1-10): [puan]/10
   Gerekçe: Hangi spesifik sahne segmentiyle en güçlü örtüşme var?

6. STRATEJİK TAVSİYE:
   - Kısa Vade  (0-6 ay): Öncelikli yapılacaklar
   - Orta Vade  (6-18 ay): Gelişim adımları
   - Uzun Vade  (18+ ay): Hedefler
   - En Kritik Aksiyon: Tek bir cümleyle en acil öneri
{trend_section}
7. FINAL KARARI — ETHNOTECHİNTELLİGENCE KARARI:
   Çekingen olma. Ethno-Tech Specialist olarak net, cesur ve veriye dayalı kararlarını açıkla.
   - Yatırım Kararı: [EVET / HAYIR / ŞARTLI] — Gerekçeni tek paragrafta savun.
   - İletişime Geçilecek Venue/Label: Londra'da bu sanatçı için en uygun 1-3 spesifik isim
     (Fabric, Fold, EartH, Corsica Studios, Boiler Room, Innervisions, Crosstown Rebels vb.) ve neden.
   - Global Referans Star: Bu sanatçının müzikal DNA'sına en yakın 1 global isim
     ve bu benzerliğin pitch deck'te nasıl kullanılabileceği.

---
SKOR_OZET (bu 4 satırı raporun en sonuna AYNEN ekle, sadece rakam yaz):
SKOR_KARIZMA: [1-10]
SKOR_GIZEM: [1-10]
SKOR_SAHNE: [1-10]
SKOR_LONDRA: [1-10]"""

_TREND_SECTION = """
7. TREND ANALİZİ:
   Son 3 aydaki yorumlarla daha eski yorumları tematik ve duygusal açıdan karşılaştır.
   - Son 3 Ay Özeti: [genel duygu tonu ve öne çıkan temalar]
   - Daha Eskiler Özeti: [genel duygu tonu ve öne çıkan temalar]
   - Momentum: [Yükselen Yıldız / Stabil / Düşüşte] — [tek cümle gerekçe]"""


def _call(prompt: str) -> str:
    response = _get_client().chat.completions.create(
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

    # Katman 1: yapılandırılmış SKOR_ satırları (en güvenilir)
    structured = {
        "Karizma":          r"SKOR_KARIZMA\s*:\s*(\d+)",
        "Gizem":            r"SKOR_GIZEM\s*:\s*(\d+)",
        "Sahne Enerjisi":   r"SKOR_SAHNE\s*:\s*(\d+)",
        "Londra Uyumluluğu":r"SKOR_LONDRA\s*:\s*(\d+)",
    }
    found = 0
    for key, pat in structured.items():
        m = re.search(pat, report_text, re.IGNORECASE)
        if m:
            scores[key] = max(1, min(10, int(m.group(1))))
            found += 1
    if found == 4:
        return scores

    # Katman 2: esnek regex — bold (**8**), parantez ((8/10)), boşluk (8 / 10)
    flexible = {
        "Karizma":           r"Karizma[^0-9]{0,40}\*{0,2}(\d+)\*{0,2}\s*/\s*10",
        "Gizem":             r"Gizem[^0-9]{0,40}\*{0,2}(\d+)\*{0,2}\s*/\s*10",
        "Sahne Enerjisi":    r"Sahne\s*Enerjisi[^0-9]{0,40}\*{0,2}(\d+)\*{0,2}\s*/\s*10",
        "Londra Uyumluluğu": r"LONDRA[^0-9]{0,60}\*{0,2}(\d+)\*{0,2}\s*/\s*10",
    }
    for key, pat in flexible.items():
        m = re.search(pat, report_text, re.IGNORECASE)
        if m:
            scores[key] = max(1, min(10, int(m.group(1))))

    return scores
