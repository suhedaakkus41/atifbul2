"""Tek PDF için yerel, çıktı yazmayan atıf kontrol akışı ve okunabilir rapor.

Yalnızca verilen PDF okunur; hedef künye çağırandan alınır. Import sırasında
işlem başlamaz. Genel değerlendirme öğrenci notu veya biçim puanı değildir.
"""

from copy import deepcopy
from pathlib import Path

from .pdf_parser import (
    pdf_sayfa_metinlerini_cikar,
    kaynakca_baslangicini_bul,
    kaynakca_sayfalarini_ayir,
    kaynakca_satirlarini_cikar,
    kaynakca_baslangic_adaylarini_bul,
    kaynakca_kayitlarini_olustur,
)
from .eser_eslestirme import (
    kayit_sinirlarini_kanitla_degerlendir,
    kayit_sinirlarini_incele,
    hedef_eseri_eslestir,
    metin_ici_atif_adaylarini_bul,
    atif_kaynakca_baglantilarini_kur,
)


def belge_atif_kontrolu(pdf_yolu, hedef_eser):
    """Mevcut yardımcıları sırayla çağırır; sonuç ve kanıtları bellekte tutar.

    Başarısız ön koşulda bağımlı adımlar çalışmaz. Kaynakça sonunun kesin
    bilinmediği ve raporun yalnızca verilen belgeyi kapsadığı korunur.
    """
    adlar = (
        "pdf_metin_cikarma", "kaynakca_baslangici", "kaynakca_bolgesi",
        "kaynakca_satirlari", "baslangic_adaylari", "kayit_olusturma",
        "sinir_degerlendirme", "eser_eslestirme", "metin_ici_tespit", "baglanti",
    )
    rapor = {
        "belge_adi": Path(pdf_yolu).name,
        "belge_yolu": str(Path(pdf_yolu).resolve()),
        "hedef_eser": deepcopy(hedef_eser),
        "pdf_sayfa_sayisi": None, "kaynakca_baslangic_sayfasi": None,
        "kaynakca_kayit_sayisi": None, "incelenecek_kayit_sayisi": None,
        "asamalar": {ad: {"durum": "engellendi", "gerekce": "Ön koşullar henüz tamamlanmadı."} for ad in adlar},
        "hedef_eser_kimligi_sonucu": {"durum": "degerlendirilemedi"},
        "hedef_kaynakca_kaydi_sonucu": {"durum": "degerlendirilemedi"},
        "hedef_metin_ici_atif_sonucu": {"durum": "degerlendirilemedi", "adaylar": []},
        "hedef_baglanti_sonucu": {"durum": "degerlendirilemedi", "baglantilar": []},
        "bibliyografik_farkliliklar": [], "belirsizlikler": [],
        "manuel_inceleme_noktalari": [], "genel_degerlendirme": "İşlem tamamlanmadı.",
        "atif_stili": {"durum": "degerlendirilemedi", "gerekce": "Standart belirtilmedi; stil puanlaması kapsam dışı."},
    }

    def calistir(ad, fonksiyon, *girdiler, kabul=None):
        try:
            sonuc = fonksiyon(*girdiler)
            durum = sonuc.get("durum", "tamamlandi") if isinstance(sonuc, dict) else "tamamlandi"
            gerekce = sonuc.get("gerekce", "") if isinstance(sonuc, dict) else ""
            rapor["asamalar"][ad] = {"durum": durum, "gerekce": gerekce}
            if kabul is not None and durum not in kabul:
                rapor["asamalar"][ad]["kanit"] = deepcopy(sonuc)
                rapor["belirsizlikler"].append(f"{ad}: {gerekce or durum}")
                return None
            return sonuc
        except Exception as hata:
            gerekce = f"{type(hata).__name__}: {hata}"
            rapor["asamalar"][ad] = {"durum": "degerlendirilemedi", "gerekce": gerekce}
            rapor["belirsizlikler"].append(f"{ad}: {gerekce}")
            return None

    def durdur(ad):
        for asama in rapor["asamalar"].values():
            if asama["durum"] == "engellendi":
                asama["gerekce"] = f"{ad} aşaması tamamlanamadı; bağımlı işlem yapılmadı."
        rapor["genel_degerlendirme"] = "Eksik/güvenilir olmayan veri nedeniyle akış durdu; yokluk veya öğrenci hatası kararı verilmedi."
        rapor["manuel_inceleme_noktalari"] = list(rapor["belirsizlikler"])
        return rapor

    sayfalar = calistir("pdf_metin_cikarma", pdf_sayfa_metinlerini_cikar, pdf_yolu)
    if not sayfalar:
        rapor["belirsizlikler"].append("PDF sayfa verisi elde edilemedi.")
        return durdur("pdf_metin_cikarma")
    rapor["pdf_sayfa_sayisi"] = len(sayfalar)
    # Boş sayfa (kapak, ara sayfa, tam sayfa görsel) tezlerde olağandır. Az sayıda boş sayfa
    # analizi durdurmaz; ancak kesin "yok" kararını engeller (aşağıda). Çıkarma hatası,
    # bozuk sayfa sırası veya çok sayıda boş sayfa (taranmış PDF olabilir) analizi durdurur.
    bos_sayfalar = [p["pdf_sayfa"] for p in sayfalar if p["metin_durumu"] == "bos"]
    sorunlar = [{"pdf_sayfa": p["pdf_sayfa"], "metin_durumu": p["metin_durumu"]}
                for p in sayfalar if p["metin_durumu"] not in ("okunabilir", "bos")]
    rapor["bos_sayfalar"] = bos_sayfalar
    rapor["asamalar"]["pdf_metin_cikarma"]["sayfa_durumlari"] = [
        {"pdf_sayfa": p["pdf_sayfa"], "metin_durumu": p["metin_durumu"]} for p in sayfalar
    ]
    bos_siniri = max(3, int(len(sayfalar) * 0.05))
    if sorunlar:
        rapor["belirsizlikler"].append({"sayfa_cikarma_sorunlari": sorunlar})
    if bos_sayfalar:
        rapor["asamalar"]["pdf_metin_cikarma"]["durum"] = "incelenmeli"
        rapor["asamalar"]["pdf_metin_cikarma"]["gerekce"] = f"Metni olmayan sayfalar (PDF sırası): {bos_sayfalar}"
        rapor["belirsizlikler"].append(f"Metni çıkarılamayan/boş sayfalar: {bos_sayfalar}")
    if ([p["pdf_sayfa"] for p in sayfalar] != list(range(1, len(sayfalar) + 1)) or
            sorunlar or len(bos_sayfalar) > bos_siniri):
        rapor["belirsizlikler"].append("Sayfa sırası veya çıkarma kapsamı güvenilir değil.")
        rapor["asamalar"]["pdf_metin_cikarma"]["durum"] = "degerlendirilemedi"
        rapor["asamalar"]["pdf_metin_cikarma"]["gerekce"] = (
            f"Boş sayfa: {len(bos_sayfalar)} (izin verilen en çok {bos_siniri}); "
            f"okuma hatası olan sayfa: {len(sorunlar)}; "
            f"sayfa sırası düzgün: {[p['pdf_sayfa'] for p in sayfalar] == list(range(1, len(sayfalar) + 1))}")
        return durdur("pdf_metin_cikarma")

    baslangic = calistir("kaynakca_baslangici", kaynakca_baslangicini_bul, sayfalar, kabul={"bulundu"})
    if baslangic is None:
        return durdur("kaynakca_baslangici")
    rapor["kaynakca_baslangic_sayfasi"] = baslangic["pdf_sayfa"]
    rapor["kaynakca_baslangic_kaniti"] = deepcopy(baslangic)
    bolge = calistir("kaynakca_bolgesi", kaynakca_sayfalarini_ayir, sayfalar, baslangic, kabul={"ayrildi"})
    if bolge is None:
        return durdur("kaynakca_bolgesi")
    satirlar = calistir("kaynakca_satirlari", kaynakca_satirlarini_cikar, bolge, kabul={"satirlar_cikarildi"})
    if satirlar is None:
        return durdur("kaynakca_satirlari")
    adaylar = calistir("baslangic_adaylari", kaynakca_baslangic_adaylarini_bul, satirlar, kabul={"adaylar_belirlendi"})
    if adaylar is None:
        return durdur("baslangic_adaylari")
    kayitlar = calistir("kayit_olusturma", kaynakca_kayitlarini_olustur, satirlar, adaylar, kabul={"kayitlar_olusturuldu"})
    if kayitlar is None:
        return durdur("kayit_olusturma")
    rapor["kaynakca_kayit_sayisi"] = len(kayitlar["kayitlar"])
    rapor["asamalar"]["kayit_olusturma"]["ilk_incelenecek_kayit_sayisi"] = sum(
        k["durum"] == "incelenmeli" for k in kayitlar["kayitlar"]
    )
    degerlendirilmis = calistir("sinir_degerlendirme", kayit_sinirlarini_kanitla_degerlendir, kayitlar, kabul={"kayitlar_olusturuldu"})
    if degerlendirilmis is None:
        return durdur("sinir_degerlendirme")
    inceleme = kayit_sinirlarini_incele(degerlendirilmis)
    rapor["incelenecek_kayit_sayisi"] = len(inceleme["kayitlar"])
    rapor["asamalar"]["sinir_degerlendirme"]["kalan_incelenecek_kayit_sayisi"] = len(inceleme["kayitlar"])
    rapor["sinir_inceleme_raporu"] = inceleme
    rapor["sinir_degerlendirmeleri"] = deepcopy(degerlendirilmis.get("sinir_degerlendirmeleri", []))
    rapor["kaynakca_kayitlari"] = degerlendirilmis
    kimlik = calistir("eser_eslestirme", hedef_eseri_eslestir, degerlendirilmis, hedef_eser,
                     kabul={"eslesti", "eslesmedi", "incelenmeli"})
    if kimlik is None:
        return durdur("eser_eslestirme")
    rapor["hedef_eser_kimligi_sonucu"] = kimlik
    rapor["hedef_kaynakca_kaydi_sonucu"] = {
        "durum": "bulundu" if kimlik["durum"] == "eslesti" else kimlik["durum"],
        "aday_kayit_kimlikleri": [a["kayit_id"] for a in kimlik["aday_kayitlar"]],
        "pdf_konumlari": deepcopy(kimlik["pdf_konumlari"]), "gerekce": kimlik["gerekce"],
    }
    rapor["bibliyografik_farkliliklar"] = [
        {"kayit_id": a["kayit_id"], **deepcopy(f)} for a in kimlik["aday_kayitlar"] for f in a["bibliyografik_farklar"]
    ]
    metin_ici = calistir("metin_ici_tespit", metin_ici_atif_adaylarini_bul, sayfalar, baslangic, hedef_eser,
                        kabul={"bulundu", "bulunamadi", "incelenmeli"})
    if metin_ici is None:
        return durdur("metin_ici_tespit")
    rapor["tum_metin_ici_adaylar"] = metin_ici
    hedef_adaylar = [a for a in metin_ici["adaylar"] if a["yazar_uyumu"] and a["yil_uyumu"]]
    rapor["hedef_metin_ici_atif_sonucu"] = {
        "durum": "bulundu" if any(a["durum"] == "bulundu" for a in hedef_adaylar) else
                 "incelenmeli" if hedef_adaylar or metin_ici.get("kapsam_sorunlari") else "bulunamadi",
        "adaylar": deepcopy(hedef_adaylar), "gerekce": metin_ici["gerekce"],
    }
    baglantilar = calistir("baglanti", atif_kaynakca_baglantilarini_kur, metin_ici, degerlendirilmis, hedef_eser,
                          kabul={"baglandi", "baglanamadi", "incelenmeli"})
    if baglantilar is None:
        return durdur("baglanti")
    rapor["tum_baglantilar"] = baglantilar
    basarili = [b for b in baglantilar["baglantilar"] if b["durum"] == "baglandi"]
    rapor["hedef_baglanti_sonucu"] = {
        "durum": "baglandi" if basarili else "incelenmeli" if kimlik["durum"] == "incelenmeli" or hedef_adaylar else "baglanamadi",
        "baglantilar": deepcopy(basarili), "basarili_baglanti_sayisi": len(basarili),
        "gerekce": "Hedef bağlantı diğer adaylardan ayrıldı; belgenin hatasız olduğu sonucu çıkarılmadı.",
    }
    rapor["diger_belirsiz_adaylar"] = deepcopy([b for b in baglantilar["baglantilar"] if b["durum"] != "baglandi"])
    rapor["manuel_inceleme_noktalari"] = [
        {"kayit_id": k["kayit_id"], "gerekceler": k["gerekceler"]} for k in inceleme["kayitlar"]
    ] + [{"metin_ici_aday": b["ham_atif_metni"], "gerekce": b["gerekce"]} for b in rapor["diger_belirsiz_adaylar"]]
    rapor["manuel_inceleme_noktalari"].extend(
        {"bibliyografik_fark": deepcopy(f)} for f in rapor["bibliyografik_farkliliklar"]
    )
    rapor["belirsizlikler"].extend(rapor["manuel_inceleme_noktalari"])
    rapor["genel_degerlendirme"] = (
        "Hedef atıf için kanıtlı bağlantı bulundu; diğer belirsizlikler ve bibliyografik farklar sürüyor."
        if basarili else "Başarılı hedef bağlantısı yok; bu sonuç eser yokluğu veya öğrenci hatası değildir."
    )
    if bos_sayfalar:
        # Boş sayfa bir içeriği gizlemiş olabilir; "bulunamadı" kesin sonuç sayılmaz.
        for ad, eski, yeni in (("hedef_eser_kimligi_sonucu", "eslesmedi", "incelenmeli"),
                               ("hedef_kaynakca_kaydi_sonucu", "eslesmedi", "incelenmeli"),
                               ("hedef_metin_ici_atif_sonucu", "bulunamadi", "incelenmeli"),
                               ("hedef_baglanti_sonucu", "baglanamadi", "incelenmeli")):
            if rapor[ad]["durum"] == eski:
                rapor[ad]["durum"] = yeni
                rapor[ad]["gerekce"] = (rapor[ad].get("gerekce", "") +
                                        f" Metni olmayan sayfalar ({bos_sayfalar}) nedeniyle kesin yokluk kararı verilmedi.").strip()
    return rapor


def kanit_raporunu_metinlestir(rapor):
    """Raporu yazmadan okunabilir metne dönüştürür; kanıtları değiştirmez."""
    satirlar = [
        f"Belge: {rapor['belge_adi']}",
        f"PDF sayfa sayısı: {rapor['pdf_sayfa_sayisi']}",
        f"Kaynakça başlangıcı: {rapor['kaynakca_baslangic_sayfasi']}",
        f"Kayıt grubu: {rapor['kaynakca_kayit_sayisi']}; incelenecek: {rapor['incelenecek_kayit_sayisi']}",
    ]
    for ad, asama in rapor["asamalar"].items():
        satirlar.append(f"Aşama {ad}: {asama['durum']} — {asama['gerekce']}")
    for ad in ("hedef_eser_kimligi_sonucu", "hedef_kaynakca_kaydi_sonucu",
               "hedef_metin_ici_atif_sonucu", "hedef_baglanti_sonucu"):
        satirlar.append(f"{ad}: {rapor[ad]['durum']}")
    for bag in rapor["hedef_baglanti_sonucu"].get("baglantilar", []):
        satirlar.append(f"Atıf PDF {bag['pdf_sayfa']} [{bag['orijinal_karakter_baslangic']},{bag['orijinal_karakter_bitis']}): {bag['ham_atif_metni']}")
        for aday in bag["aday_kayitlar"]:
            satirlar.append(f"Kaynakça {aday['kayit_id']}: {aday['pdf_konumlari']}")
    for fark in rapor["bibliyografik_farkliliklar"]:
        satirlar.append(f"Bibliyografik fark: {fark}")
    for nokta in rapor["manuel_inceleme_noktalari"]:
        satirlar.append(f"Manuel inceleme: {nokta}")
    satirlar.append(rapor["genel_degerlendirme"])
    satirlar.append("Atıf stili puanlanmadı; bilimsel iddia doğruluğu değerlendirilmedi.")
    return "\n".join(satirlar)