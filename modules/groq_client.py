import os
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
_client = Groq(api_key=os.environ["GROQ_API_KEY"])


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
    response = _client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


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
