"""PDF Analizi sekmesi için yardımcılar. Asıl PDF işini Begüm'ün kodu yapar
(atif_islem_akisi.belge_atif_kontrolu); burası yalnızca hazırlık ve sade özet üretir."""

import os
import tempfile



def hedef_eser_hazirla(baslik, yazarlar, yil, doi=""):
    """Begüm'ün kodunun beklediği hedef sözlüğü (title, authors, year, doi)."""
    hedef = {"title": baslik, "authors": list(yazarlar), "year": yil}
    if doi:
        hedef["doi"] = doi
    return hedef


def kanit_raporunu_metinlestir(rapor):
    from .atif_islem_akisi import kanit_raporunu_metinlestir as _metinlestir
    bos = rapor.get("bos_sayfalar")
    if bos is None:
        tani = "TANI: atif_islem_akisi.py ESKİ SÜRÜM (boş sayfa toleransı yok). Dosyayı yenileyin ve uygulamayı yeniden başlatın."
    else:
        durumlar = rapor["asamalar"].get("pdf_metin_cikarma", {}).get("sayfa_durumlari", [])
        hatali = [d["pdf_sayfa"] for d in durumlar if d["metin_durumu"] not in ("okunabilir", "bos")]
        tani = f"TANI: boş sayfa {len(bos)} adet {bos[:15]}; okuma hatası {len(hatali)} adet {hatali[:15]}"
    return tani + "\n" + _metinlestir(rapor)


def pdf_kontrol_et(pdf_baytlari, hedef_eser):
    """Yüklenen PDF'i geçici dosyaya yazıp kontrol eder; dosyayı hemen siler."""
    # pymupdf kurulu değilse uygulama açılsın, hata yalnızca bu sekmede görünsün diye burada içe aktarılır.
    from .atif_islem_akisi import belge_atif_kontrolu
    dosya = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    try:
        dosya.write(pdf_baytlari)
        dosya.close()
        return belge_atif_kontrolu(dosya.name, hedef_eser)
    finally:
        try:
            os.unlink(dosya.name)
        except OSError:
            pass


def ozet(rapor):
    """Raporu ekranda gösterilecek tek bir sonuca çevirir: (tur, baslik, aciklama)."""
    baglanti = rapor["hedef_baglanti_sonucu"]["durum"]
    kimlik = rapor["hedef_eser_kimligi_sonucu"]["durum"]
    if baglanti == "baglandi":
        return ("basari", "Atıf bulundu",
                "Hedef eser kaynakçada bulundu ve metin içindeki atıfla eşleştirildi.")
    if baglanti == "degerlendirilemedi" and kimlik == "degerlendirilemedi":
        return ("hata", "Değerlendirilemedi",
                "PDF güvenilir biçimde işlenemedi. Aşağıdaki aşamalardan nedenine bakın.")
    metin_ici = rapor["hedef_metin_ici_atif_sonucu"]["durum"]
    # Kaynakçada ya da metin içinde herhangi bir iz varsa "bulunamadı" demek yanıltıcı olur.
    if baglanti == "incelenmeli" or kimlik in ("eslesti", "incelenmeli") or metin_ici in ("bulundu", "incelenmeli"):
        return ("uyari", "İncelenmeli",
                "Olası bir eşleşme var ama otomatik karar verilemedi. Kanıtları elle kontrol edin.")
    return ("bilgi", "Atıf bulunamadı",
            "Bu PDF'te hedef esere atıf bulunamadı. Bu, belgede hata olduğu anlamına gelmez.")


def kaynakca_kaydi_metni(rapor):
    """Aday kaynakça kayıtları: [(kayit_id, sayfa, metin, etiket)].

    Güçlü eşleşme: başlık, yazarlar ve yıl birlikte uyuyor. Diğer adaylar yalnızca
    yazar soyadı ve yıl benzerliğiyle listelenmiş zayıf adaylardır."""
    sonuc = []
    for aday in rapor["hedef_eser_kimligi_sonucu"].get("aday_kayitlar", []):
        metin = " ".join("".join(p["metin"] for p in aday["ham_metin_parcalari"]).split())
        sayfa = aday["ham_metin_parcalari"][0]["pdf_sayfa"] if aday["ham_metin_parcalari"] else None
        kanit = aday.get("kanitlar", {})
        benz = (kanit.get("baslik") or {}).get("benzerlik") or 0
        yil_ok = bool(kanit.get("yil_uyumu"))
        yazar_ok = bool(kanit.get("yazar_uyumu"))
        if kanit.get("kimlik_kaniti_guclu"):
            etiket = "Güçlü eşleşme: başlık, yazar ve yıl uyuyor"
        elif benz >= 0.85 and yil_ok:
            fark = []
            if not yazar_ok:
                fark.append("yazar yazılışı farklı")
            if not (kanit.get("baslik") or {}).get("tam_normalize_eslesme"):
                fark.append("başlıkta küçük fark")
            etiket = f"Olası eşleşme: başlık %{round(benz * 100)} benzer, yıl uyuyor ({', '.join(fark) or 'küçük farklar'}); elle kontrol edin"
        else:
            etiket = f"Zayıf aday: başlık %{round(benz * 100)} benzer; yazar soyadı ve yıl benzediği için listelendi"
        sonuc.append((aday["kayit_id"], sayfa, metin, etiket))
    # güçlü eşleşmeler önce gösterilsin
    sirala = {"Güçlü": 0, "Olası": 1}
    sonuc.sort(key=lambda x: sirala.get(x[3].split()[0], 2))
    return sonuc