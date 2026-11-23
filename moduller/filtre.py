"""Arayüzün kullandığı küçük yardımcı fonksiyonlar (arama, tür grubu, yıl filtresi, DOI bağlantısı)."""

import re
import unicodedata

TUR_GRUPLARI = ["Makale", "Kitap", "Bildiri", "Diğer"]

# Veride şu an yalnızca Remzi Başar var (5-7. hafta kapsamı).
AKADEMISYENLER = [
    {"ad": "Remzi Başar", "kurum": "Düzce Üniversitesi"},
]


def tur_grubu(tur):
    """Ekrandaki tür adını 4 gruptan birine çevirir. Kitap bölümü 'Kitap' grubundadır."""
    if tur == "Makale":
        return "Makale"
    if tur in ("Kitap", "Kitap bölümü"):
        return "Kitap"
    if tur == "Bildiri":
        return "Bildiri"
    return "Diğer"


def ad_sadelestir(ad):
    """'Remzi BAŞAR' -> 'remzi basar' (Türkçe harfler ve büyük/küçük harf fark etmez)."""
    ad = (ad or "").replace("ı", "i").replace("İ", "i")
    ad = unicodedata.normalize("NFKD", ad.casefold())
    ad = "".join(c for c in ad if not unicodedata.combining(c))
    return " ".join(ad.split())


def akademisyen_bul(aranan, kurum="Tüm kurumlar"):
    """Yazılan ismin tüm sözcükleri adın içinde geçiyorsa akademisyeni döndürür."""
    sozcukler = ad_sadelestir(aranan).split()
    if not sozcukler:
        return []
    bulunanlar = []
    for kisi in AKADEMISYENLER:
        hedef = ad_sadelestir(kisi["ad"])
        if kurum != "Tüm kurumlar" and kisi["kurum"] != kurum:
            continue
        if all(s in hedef for s in sozcukler):
            bulunanlar.append(kisi)
    return bulunanlar


def doi_link(doi):
    """'10.1007/x' veya 'https://doi.org/10.1007/x' -> tıklanabilir doi.org adresi (boşsa None)."""
    doi = (doi or "").strip()
    if not doi:
        return None
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    return "https://doi.org/" + doi


def yil_int(deger):
    try:
        return int(deger)
    except (TypeError, ValueError):
        return None


def yil_araligi(atiflar):
    """Atıf yapan eserlerin en eski ve en yeni yılı. Yıl yoksa (None, None)."""
    yillar = [y for y in (yil_int(a.get("yil")) for a in atiflar) if y is not None]
    return (min(yillar), max(yillar)) if yillar else (None, None)


def atiflari_filtrele(atiflar, yayin_idleri, bas_yil, bit_yil, oz_atif_gizle=False):
    """Seçilen yayınlara yapılan atıfları, atıf yapan eserin yılına göre süzer.

    Yılı bilinmeyen atıflar silinmez (listede kalır).
    """
    sonuc = []
    for a in atiflar:
        if a.get("atif_alan_yayin_id") not in yayin_idleri:
            continue
        yil = yil_int(a.get("yil"))
        if yil is not None and not (bas_yil <= yil <= bit_yil):
            continue
        if oz_atif_gizle and a.get("oz_atif") == "evet":
            continue
        sonuc.append(a)
    return sonuc
