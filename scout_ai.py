import subprocess
import sys

from dotenv import load_dotenv

load_dotenv()

from modules.config import DATA_DIR, REPORTS_DIR
from modules.report import build_summary_html, process_and_save
from modules.youtube_client import fetch_youtube_data, split_by_date


def run_single() -> None:
    print("\nSanatçı adını girin (boşluk yerine alt çizgi, örn: Mehmet_Aslan):")
    artist_name = input("  Ad: ").strip()
    if not artist_name:
        print("Hata: Sanatçı adı boş olamaz.")
        sys.exit(1)

    print("\nYorumları yapıştırın. Bitirmek için boş satır bırakıp Enter'a basın:\n")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if not line.strip():
            break
        lines.append(line)

    if not lines:
        print("Hata: En az bir yorum girilmeli.")
        sys.exit(1)

    _analyze_and_open(artist_name, "\n".join(lines))


def run_batch() -> None:
    if not DATA_DIR.exists():
        print(f"Hata: '{DATA_DIR}' klasörü bulunamadı!")
        sys.exit(1)

    txt_files = sorted(DATA_DIR.glob("*.txt"))
    if not txt_files:
        print(f"Hata: '{DATA_DIR}' klasöründe .txt dosyası bulunamadı!")
        sys.exit(1)

    REPORTS_DIR.mkdir(exist_ok=True)
    results = []
    print(f"\n{len(txt_files)} sanatçı dosyası bulundu.\n")

    for txt_file in txt_files:
        artist_name = txt_file.stem
        print(f"Analiz ediliyor: {artist_name}...")
        try:
            results.append(process_and_save(artist_name, txt_file.read_text(encoding="utf-8")))
        except Exception as e:
            print(f"  Hata ({artist_name}): {e}")

    if results:
        summary_path = REPORTS_DIR / "_ozet_rapor.html"
        summary_path.write_text(build_summary_html(results), encoding="utf-8")
        best = max(results, key=lambda x: x["scores"]["Londra Uyumluluğu"])
        print(f"\nÖzet rapor → {summary_path}")
        print(f"En uygun aday: {best['artist'].replace('_', ' ')} ({best['scores']['Londra Uyumluluğu']}/10)")

    print("\nTamamlandı.")


def run_youtube() -> None:
    print("\nYouTube video linkini yapıştırın:")
    url = input("  URL: ").strip()
    if not url:
        print("Hata: URL boş olamaz.")
        sys.exit(1)

    print("\nVideo bilgileri alınıyor...")
    try:
        artist_name, comments_list, title = fetch_youtube_data(url)
    except Exception as e:
        print(f"Hata: {e}")
        sys.exit(1)

    recent_str, older_str = split_by_date(comments_list)
    raw_comments = "\n".join(f"- {c['text']}" for c in comments_list)

    print(f"  Video       : {title}")
    print(f"  Ad          : {artist_name.replace('_', ' ')}")
    print(f"  Son 3 ay    : {len(recent_str.splitlines()) if recent_str else 0} yorum")
    print(f"  Daha eskiler: {len(older_str.splitlines()) if older_str else 0} yorum")

    edited = input(f"\nSanatçı adını onaylayın veya değiştirin [{artist_name.replace('_', ' ')}]: ").strip()
    if edited:
        artist_name = edited.replace(" ", "_")

    _analyze_and_open(artist_name, raw_comments, recent_str, older_str)


def _analyze_and_open(
    artist_name: str,
    raw_comments: str,
    recent_str: str = None,
    older_str: str = None,
) -> None:
    print(f"\nAnaliz ediliyor: {artist_name.replace('_', ' ')}...")
    try:
        result = process_and_save(artist_name, raw_comments, recent_str, older_str)
        print(f"Londra Pazarı Puanı: {result['scores']['Londra Uyumluluğu']}/10")
        subprocess.run(["open", str(REPORTS_DIR / f"{artist_name}_rapor.html")])
    except Exception as e:
        print(f"Hata: {e}")
        sys.exit(1)


def main():
    print("=" * 42)
    print("   ETHNOTECH AI SCOUT")
    print("=" * 42)
    print("\n[1] Tekli giriş   — terminal'den yorum gir")
    print("[2] Toplu analiz  — Data/ klasöründen oku")
    print("[3] YouTube linki — yorumları otomatik çek")
    print()

    choice = input("Mod seçin (1/2/3): ").strip().lower()

    if choice in ("1", "tekli"):
        run_single()
    elif choice in ("2", "batch", "toplu"):
        run_batch()
    elif choice in ("3", "youtube", "yt"):
        run_youtube()
    else:
        print("Geçersiz seçim. 1, 2 veya 3 girin.")
        sys.exit(1)


if __name__ == "__main__":
    main()
