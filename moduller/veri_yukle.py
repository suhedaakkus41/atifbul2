"""Emine'nin (3. kişi) hazırladığı arayuz_verisi.json dosyasını okur.

Arayüz veriyi YALNIZCA bu dosya üzerinden okur. Şema değişirse sadece burası güncellenir.
Kayıtlarda bazı alanlar eksik olabilir; bu yüzden her yerde .get() kullanılır.
"""

import json
from pathlib import Path

VERI_YOLU = Path(__file__).resolve().parent.parent / "veri" / "arayuz_verisi.json"

# OpenAlex / Emine'nin tür adları -> ekranda göreceğimiz ad
TUR_ADLARI = {
    "article": "Makale",
    "book": "Kitap",
    "book-chapter": "Kitap bölümü",
    "proceedings-article": "Bildiri",
    "dissertation": "Tez",
    "dataset": "Veri seti",
}


def tur_adi(ham_tur):
    return TUR_ADLARI.get(ham_tur, "Diğer / bilinmiyor")


def _oku():
    with VERI_YOLU.open(encoding="utf-8-sig") as dosya:
        return json.load(dosya)


def yayinlari_yukle():
    """Hocanın yayınları (atıf ALAN eserler). Her kayıt sade bir sözlüktür."""
    sonuc = []
    for y in _oku().get("yayinlar", []):
        sonuc.append({
            "id": y.get("id"),
            "baslik": y.get("baslik") or "Başlıksız yayın",
            "tur": tur_adi(y.get("tur")),
            "yil": y.get("yil"),
            "doi": y.get("doi") or "",
            "yazarlar": y.get("yazarlar") or [],
        })
    return sonuc


def atiflari_yukle():
    """Hocanın yayınlarına yapılan atıflar. Her kayıt sade bir sözlüktür."""
    sonuc = []
    for a in _oku().get("atiflar", []):
        sonuc.append({
            "atif_alan_yayin_id": a.get("atif_alan_yayin_id"),
            "atif_alan_yayin": a.get("atif_alan_yayin_basligi") or "(başlık yok)",
            "atif_yapan_eser": a.get("atif_yapan_eser_basligi") or "(başlık yok)",
            "atif_yapan_tur": tur_adi(a.get("atif_yapan_eser_turu")),
            "yil": a.get("atif_yapan_eser_yili"),
            "doi": a.get("doi") or "",
            "durum": a.get("dogrulama_durumu") or "İncelenmeli",
            "kanit_url": a.get("kanit_url") or "",
            "oz_atif": a.get("oz_atif") or "bilinmiyor",
        })
    return sonuc


def pdf_kayitlarini_yukle():
    return _oku().get("pdf_kaynakca_adaylari", [])