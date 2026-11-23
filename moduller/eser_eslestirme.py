"""Bellekte kaynakça sınırı incelemesi ve hedef eser aday eşleştirmesi.

Dosya/ağ işlemi yapmaz. Metin içi kullanımı veya atıf stilini doğrulamaz.
Hedef künye çağıran tarafından verilir; manuel kararlar okunmaz/değiştirilmez.
"""

from copy import deepcopy
from difflib import SequenceMatcher
import re
import unicodedata


def _karsilastirma_metni(metin):
    """Yalnızca karşılaştırma görünümü; ham kanıtın yerine geçmez."""
    metin = unicodedata.normalize("NFKD", metin.casefold().replace("ı", "i"))
    metin = "".join(c for c in metin if not unicodedata.combining(c))
    return " ".join(re.findall(r"\w+", metin))


def _pdf_konumlari(parcalar):
    return [{k: p[k] for k in (
        "pdf_sayfa", "orijinal_karakter_baslangic", "orijinal_karakter_bitis"
    )} for p in parcalar]


def kayit_sinirlarini_incele(kayit_bilgileri):
    """Tüm belirsiz kayıtları, komşularını ve alternatif sınırları gösterir.

    Bu inceleme mevcut kayıt durumlarını kesinleştirmez veya sınırları taşımaz.
    """
    if kayit_bilgileri.get("durum") != "kayitlar_olusturuldu":
        return {"durum": "degerlendirilemedi", "kayitlar": [],
                "gerekce": "Geçerli kayıt oluşturma sonucu yok."}
    kayitlar = kayit_bilgileri["kayitlar"]
    incelemeler = []
    for sira, kayit in enumerate(kayitlar):
        if kayit["durum"] != "incelenmeli":
            continue
        konumlar = _pdf_konumlari(kayit["ham_metin_parcalari"])
        alternatifler = []
        for karar in kayit_bilgileri.get("sinir_kararlari", []):
            aday = karar["aday"]
            if any(p["pdf_sayfa"] == aday["pdf_sayfa"] and
                   p["orijinal_karakter_baslangic"] <= aday["orijinal_karakter_baslangic"] <
                   p["orijinal_karakter_bitis"] for p in konumlar):
                alternatifler.append(deepcopy(karar))
        incelemeler.append({
            "kayit_id": kayit["kayit_id"], "durum": "incelenmeli",
            "onceki_kayit": kayitlar[sira - 1]["kayit_id"] if sira else None,
            "sonraki_kayit": kayitlar[sira + 1]["kayit_id"] if sira + 1 < len(kayitlar) else None,
            "pdf_konumlari": konumlar,
            "gerekceler": list(kayit["belirsizlik_gerekceleri"]),
            "alternatif_baslangiclar": alternatifler,
            "alternatif_bitis_konumlari": [
                {"pdf_sayfa": a["aday"]["pdf_sayfa"],
                 "karakter": a["aday"]["orijinal_karakter_baslangic"],
                 "gerekce": "İç adaydan önce bitirme / sonraki kayıt olarak ayırma olasılığı."}
                for a in alternatifler if not a["sinir"]
            ] + ([{
                "pdf_sayfa": kayitlar[sira + 1]["ham_metin_parcalari"][0]["pdf_sayfa"],
                "karakter": kayitlar[sira + 1]["ham_metin_parcalari"][0]["orijinal_karakter_baslangic"],
                "gerekce": "Komşu başlangıç sınırı; birleşme alternatifi ayrıca incelenmeli.",
            }] if sira + 1 < len(kayitlar) else []),
            "alternatif_bitis": (
                "Sonraki kaydın başlangıcı/önceki kayda birleşme olasılığı ayrıca incelenmeli; sınır değiştirilmedi."
            ),
        })
    return {"durum": "incelendi", "kayitlar": incelemeler,
            "kayit_disi_bolgeler": deepcopy(kayit_bilgileri.get("kayit_disi_bolgeler", [])),
            "gerekce": "Yalnızca inceleme raporu; hiçbir belirsizlik otomatik çözülmedi."}


def _baslik_kaniti(metin, hedef_baslik):
    hedef = _karsilastirma_metni(hedef_baslik)
    gorunum = _karsilastirma_metni(metin)
    # Hedefin daha uzun başka bir başlığın yalnızca alt dizisi olması yeterli değil.
    baslik_deseni = r"^[\s.,:;\-]*" + r"[\W_]+".join(re.escape(k) for k in hedef.split())
    baslik_deseni += r"(?=\s*(?:[.,]|$))"
    tam = bool(hedef) and bool(re.search(baslik_deseni, _karsilastirma_alanlari(metin)))
    kelimeler = gorunum.split()
    uzunluk = len(hedef.split())
    puan = 0.0
    # Kaydın tamamı yerine başlık uzunluğuna yakın pencereler karşılaştırılır.
    for boy in range(max(1, uzunluk - 2), uzunluk + 3):
        for sira in range(max(0, len(kelimeler) - boy + 1)):
            puan = max(puan, SequenceMatcher(None, hedef, " ".join(kelimeler[sira:sira + boy])).ratio())
    return {"tam_normalize_eslesme": tam, "benzerlik": 1.0 if tam else round(puan, 4)}


def _baglac_at(soyad):
    """'ve Arslan' / 'and Smith' gibi bağlaçlı yakalamalarda baştaki bağlacı atar.

    Kaynakçada 'Başar, R. ve Arslan, M. (2017)' yazılışında 've' soyadın parçası sayılmamalı."""
    parcalar = soyad.split()
    while len(parcalar) > 1 and parcalar[0].casefold() in {"ve", "and", "ile", "&"}:
        parcalar = parcalar[1:]
    return " ".join(parcalar)


def _doi_degeri(deger):
    deger = deger.casefold().strip()
    return re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", deger).rstrip(".,;)")


def _bibliyografik_farklar(ham, hedef):
    farklar = []
    for etiket, anahtar in (("cilt", "volume"), ("sayi", "issue")):
        eslesme = re.search(rf"\b{etiket}\s*:\s*(\d+)", _karsilastirma_alanlari(ham))
        if eslesme and hedef.get(anahtar) is not None and eslesme[1] != str(hedef[anahtar]):
            farklar.append({"alan": anahtar, "kayitta": eslesme[1],
                            "hedefte": hedef[anahtar], "tur": "bibliyografik_fark"})
    sayfa = re.search(r"\bss\s*\.?\s*(\d+(?:\s*[-–]\s*\d+)?)", ham, re.IGNORECASE)
    if sayfa and hedef.get("pages"):
        kayit_sayfa = re.sub(r"\s", "", sayfa[1]).replace("–", "-")
        hedef_sayfa = str(hedef["pages"]).replace("–", "-")
        if kayit_sayfa != hedef_sayfa:
            farklar.append({"alan": "pages", "kayitta": sayfa[1], "hedefte": hedef["pages"],
                            "tur": "bibliyografik_fark",
                            "gerekce": "Tek sayfa atıf konumu olabilir; tam yayın aralığıyla aynı değil, otomatik hata sayılmadı."})
    return farklar


def _karsilastirma_alanlari(metin):
    # Alan ayraçlarını koruyan ayrı görünüm; ham metni değiştirmez.
    metin = unicodedata.normalize("NFKD", metin.casefold().replace("ı", "i"))
    return "".join(c for c in metin if not unicodedata.combining(c))


def hedef_eseri_eslestir(kayit_bilgileri, hedef_eser):
    """Başlık + yazar + yıl ve varsa DOI kanıtlarını ayrı değerlendirir.

    Örnek hedef alanları: title, authors, year; isteğe bağlı doi, volume,
    issue, pages. Belirsiz kayıt sınırı varsa güçlü kimlik kanıtında bile
    sonuç incelenmeli kalır. Yokluk kararı yalnızca güvenilir kapsamda verilir.
    """
    sonuc = {"durum": "degerlendirilemedi", "hedef_eser": deepcopy(hedef_eser),
             "aday_kayitlar": [], "kanitlar": [], "celiskiler": [],
             "pdf_konumlari": [], "gerekce": ""}
    if (not isinstance(hedef_eser.get("title"), str) or not hedef_eser["title"].strip()
            or not hedef_eser.get("authors") or not hedef_eser.get("year")):
        sonuc["gerekce"] = "Hedefin başlık, yazar ve yıl bilgileri eksik."
        return sonuc
    if kayit_bilgileri.get("durum") != "kayitlar_olusturuldu" or not kayit_bilgileri.get("kayitlar"):
        sonuc["gerekce"] = "Güvenilir kayıt oluşturma sonucu yok."
        return sonuc

    soyadlar = {_karsilastirma_metni(a.split()[-1]) for a in hedef_eser["authors"]}
    hedef_doi = _doi_degeri(hedef_eser["doi"]) if hedef_eser.get("doi") else None
    for kayit in kayit_bilgileri["kayitlar"]:
        ham = "".join(p["metin"] for p in kayit["ham_metin_parcalari"])
        yil = re.search(r"\((18\d{2}|19\d{2}|20\d{2})[a-z]?\)", ham)
        onek = ham[:yil.start()] if yil else ""
        bulunan_soyadlar = {_karsilastirma_metni(_baglac_at(a)) for a in re.findall(
            r"([^\W\d_]+(?:[-’'][^\W\d_]+)*(?:[ \t]+[^\W\d_]+){0,3}),", onek)}
        baslik = _baslik_kaniti(ham[yil.end():] if yil else ham, hedef_eser["title"])
        doiler = sorted({_doi_degeri(d) for d in re.findall(r"10\.\d{4,9}/[^\s<>]+", ham, re.IGNORECASE)})
        yazar_uyum = bulunan_soyadlar == soyadlar
        yil_uyum = bool(yil and int(yil[1]) == int(hedef_eser["year"]))
        doi_uyum = bool(hedef_doi and hedef_doi in doiler)
        if not (baslik["benzerlik"] >= 0.65 or doi_uyum or
                (soyadlar & bulunan_soyadlar and yil_uyum)):
            continue

        celiskiler = []
        if bulunan_soyadlar and not yazar_uyum:
            celiskiler.append({"alan": "authors", "kayitta": sorted(bulunan_soyadlar),
                              "hedefte": sorted(soyadlar), "tur": "kimlik_celiskisi"})
        if yil and not yil_uyum:
            celiskiler.append({"alan": "year", "kayitta": int(yil[1]),
                              "hedefte": hedef_eser["year"], "tur": "kimlik_celiskisi",
                              "gerekce": "Yıl farkı; yayın/sürüm açıklaması incelenmeli, otomatik hata değildir."})
        if hedef_doi and doiler and (not doi_uyum or any(d != hedef_doi for d in doiler)):
            celiskiler.append({"alan": "doi", "kayitta": doiler, "hedefte": hedef_doi,
                              "tur": "kimlik_celiskisi", "gerekce": "DOI ilişkisi açıklanmadan eşit sayılmadı."})
        kimlik_guclu = baslik["tam_normalize_eslesme"] and yazar_uyum and yil_uyum and not celiskiler
        sinir_belirsiz = kayit["durum"] != "olusturuldu" or bool(kayit.get("belirsizlik_gerekceleri"))
        kanit = {"baslik": baslik, "yazar_soyadlari": sorted(bulunan_soyadlar),
                 "yazar_uyumu": yazar_uyum, "yil": int(yil[1]) if yil else None,
                 "yil_uyumu": yil_uyum, "doiler": doiler,
                 "doi_durumu": "eksik" if not doiler else "karsilastirildi" if hedef_doi else "hedef_doi_bilinmiyor",
                 "kimlik_kaniti_guclu": kimlik_guclu, "sinir_belirsiz": sinir_belirsiz}
        aday = {"kayit_id": kayit["kayit_id"],
                "durum": "eslesti" if kimlik_guclu and not sinir_belirsiz else "incelenmeli",
                "ham_metin_parcalari": deepcopy(kayit["ham_metin_parcalari"]),
                "pdf_konumlari": _pdf_konumlari(kayit["ham_metin_parcalari"]),
                "kanitlar": kanit, "celiskiler": celiskiler,
                "bibliyografik_farklar": _bibliyografik_farklar(ham, hedef_eser),
                "sinir_gerekceleri": list(kayit.get("belirsizlik_gerekceleri", []))}
        sonuc["aday_kayitlar"].append(aday)
        sonuc["kanitlar"].append({"kayit_id": kayit["kayit_id"], **kanit})
        sonuc["celiskiler"].extend({"kayit_id": kayit["kayit_id"], **c} for c in celiskiler)
        sonuc["pdf_konumlari"].extend(aday["pdf_konumlari"])

    adaylar = sonuc["aday_kayitlar"]
    if adaylar:
        sonuc["durum"] = "eslesti" if len(adaylar) == 1 and adaylar[0]["durum"] == "eslesti" else "incelenmeli"
        sonuc["gerekce"] = (
            "Tek kayıtta başlık, yazar ve yıl uyumlu; metin içi kullanım veya biçim doğrulanmadı."
            if sonuc["durum"] == "eslesti" else
            "Aday bulundu; sınır, kimlik çelişkisi, eksik kanıt veya çoklu aday nedeniyle insan incelemesi gerekli."
        )
        return sonuc

    # Kayıt dışı metin adayları da yokluk kararını sınırlayabilir.
    dis = kayit_bilgileri.get("kayit_disi_bolgeler", [])
    dis_hedef_riski = any(_baslik_kaniti(p["metin"], hedef_eser["title"])["benzerlik"] >= 0.65
                         for p in dis if p["metin"].strip())
    kapsam_belirsiz = any(k["durum"] != "olusturuldu" for k in kayit_bilgileri["kayitlar"])
    kapsam_belirsiz |= any("atanmamış" in p.get("gerekce", "") or "telif" in p.get("gerekce", "") for p in dis)
    sonuc["durum"] = "incelenmeli" if kapsam_belirsiz or dis_hedef_riski else "eslesmedi"
    sonuc["gerekce"] = (
        "Güçlü hedef adayı bulunmadı; belirsiz kayıt/kayıt dışı kapsam nedeniyle kesin yokluk kararı verilmedi."
        if sonuc["durum"] == "incelenmeli" else
        "İncelenen kaynakça kayıtlarında hedef eşleşmedi; bu bulgu öğrenci hatası veya metin içi kullanım kararı değildir."
    )
    return sonuc


def kayit_sinirlarini_kanitla_degerlendir(kayit_bilgileri):
    """Yeni bir görünümde yalnızca kanıtlı bölünmüş başlangıç sınırını çözer.

    Ham parçalar, kimlikler ve eski kararlar korunur. Soyad/baş harf/yıl veya
    Sayıştay/Başkanlığı/yıl dizisi aynı sayfada bitişik olmalıdır. Bu işlem
    eser kimliğini değil, fiziksel kayıt başlangıcını değerlendirir.
    """
    sonuc = deepcopy(kayit_bilgileri)
    sonuc.setdefault("sinir_degerlendirmeleri", [])
    if sonuc.get("durum") != "kayitlar_olusturuldu":
        return sonuc
    kayitlar = sonuc["kayitlar"]
    ilk_gerekce = "Bölünmüş başlangıç: baş harf/kurum ve sonraki yıl destekliyor; sınır geçici."
    son_gerekce = "Son sınır, bölünmüş bir başlangıç adayına dayanıyor."
    for sira, kayit in enumerate(kayitlar):
        parcalar = kayit["ham_metin_parcalari"]
        if len(parcalar) < 3 or ilk_gerekce not in kayit.get("belirsizlik_gerekceleri", []):
            continue
        ilk_uc = parcalar[:3]
        bitisik = all(
            a["pdf_sayfa"] == b["pdf_sayfa"] and
            a["orijinal_karakter_bitis"] == b["orijinal_karakter_baslangic"]
            for a, b in zip(ilk_uc, ilk_uc[1:])
        )
        satirlar = [p["metin"].strip() for p in ilk_uc]
        kisi = bool(re.fullmatch(r"[^\W\d_]+(?:[ '\-’][^\W\d_]+)*,", satirlar[0]) and
                    re.fullmatch(r"[^\W\d_]\.", satirlar[1]))
        kurum = satirlar[:2] == ["Sayıştay", "Başkanlığı"]
        yil = bool(re.fullmatch(r"\((?:18|19|20)\d{2}[a-z]?\)\.", satirlar[2]))
        if not (bitisik and yil and (kisi or kurum)):
            continue
        kayit["belirsizlik_gerekceleri"].remove(ilk_gerekce)
        if not kayit["belirsizlik_gerekceleri"]:
            kayit["durum"] = "olusturuldu"
        onceki = kayitlar[sira - 1] if sira else None
        onceki_cozuldu = False
        if onceki and onceki["ham_metin_parcalari"]:
            son = onceki["ham_metin_parcalari"][-1]
            if (son["pdf_sayfa"] == parcalar[0]["pdf_sayfa"] and
                    son["orijinal_karakter_bitis"] == parcalar[0]["orijinal_karakter_baslangic"] and
                    son["metin"].rstrip().endswith(".") and
                    son_gerekce in onceki["belirsizlik_gerekceleri"]):
                onceki["belirsizlik_gerekceleri"].remove(son_gerekce)
                if not onceki["belirsizlik_gerekceleri"]:
                    onceki["durum"] = "olusturuldu"
                onceki_cozuldu = True
        sonuc["sinir_degerlendirmeleri"].append({
            "kayit_id": kayit["kayit_id"],
            "onceki_kayit_id": onceki["kayit_id"] if onceki else None,
            "baslangic_siniri": "yapisal_kanitla_desteklendi",
            "onceki_bitis_desteklendi": onceki_cozuldu,
            "kanit_parcalari": deepcopy(ilk_uc),
            "gerekce": "Bitişik soyad/baş harf veya kurum dizisini parantezli yıl izliyor; önceki bitişin nokta ve komşuluk kontrolü ayrıca raporlandı.",
        })
    return sonuc


def _konumlu_normalize_metin(ham):
    """Her karşılaştırma karakterini orijinal karakter indeksine bağlar."""
    harfler, konumlar = [], []
    for sira, karakter in enumerate(ham):
        gorunum = unicodedata.normalize("NFKD", karakter.casefold().replace("ı", "i"))
        for harf in gorunum:
            if not unicodedata.combining(harf):
                harfler.append(harf)
                konumlar.append(sira)
    return "".join(harfler), konumlar


def metin_ici_atif_adaylarini_bul(sayfa_kayitlari, baslangic_bilgisi, hedef_eser):
    """İki yazarlı yazar-yıl atıf adaylarını yalnızca kaynakça öncesinde arar.

    bulundu, sözdizimsel atıf adayıdır; aynı soyadlı kişileri kesin ayıramaz ve
    kaynakça/iddia doğruluğunu kanıtlamaz. Küçük harf/Türkçe karakter farkları
    karşılaştırma görünümündedir. Aslan/Arslan gibi farklar incelenmeli kalır.
    """
    sonuc = {"durum": "degerlendirilemedi", "adaylar": [], "kapsam_sorunlari": [],
             "hedef_eser": deepcopy(hedef_eser), "gerekce": ""}
    if baslangic_bilgisi.get("durum") != "bulundu":
        sonuc["gerekce"] = "Kaynakça sınırı güvenilir değil; ana metin ayrılmadı."
        return sonuc
    if len(hedef_eser.get("authors", [])) != 2 or not hedef_eser.get("year"):
        sonuc["gerekce"] = "İlk prototip iki yazarlı, yılı bilinen hedef gerektirir."
        return sonuc
    sinir_sayfa = baslangic_bilgisi["pdf_sayfa"]
    sinir = baslangic_bilgisi["karakter_baslangic"]
    sinir_kayitlari = [p for p in sayfa_kayitlari if p["pdf_sayfa"] == sinir_sayfa]
    if (len(sinir_kayitlari) != 1 or not 0 <= sinir <= len(sinir_kayitlari[0]["metin"]) or
            sinir_kayitlari[0]["metin"][sinir:baslangic_bilgisi["karakter_bitis"]] != baslangic_bilgisi["baslik"]):
        sonuc["gerekce"] = "Kaynakça sınırı ham sayfayla uyuşmuyor."
        return sonuc
    soyadlar = [_karsilastirma_metni(a.split()[-1]) for a in hedef_eser["authors"]]
    bas_harfler = [[_karsilastirma_metni(k)[0] for k in a.split()[:-1]] for a in hedef_eser["authors"]]
    yazar = r"(?:[a-z]\.\s*){0,3}[a-z]+"
    ortak_son = r"(?=[\s,(]),?\s*\(?\s*(?P<yil>(?:18|19|20)\d{2}[a-z]?)(?:\s*[:,]\s*(?:s\.?\s*)?\d+(?:[-–]\d+)?)?[ \t]*\)?"
    cift = re.compile(rf"(?<!\w)\(?(?P<ilk>{yazar})\s+(?:ve|and|&)\s+(?P<ikinci>{yazar})" + ortak_son)
    tek = re.compile(rf"(?<!\w)\(?(?P<ilk>{yazar})" + ortak_son)
    alanlar = []
    tekrarlar = {}
    for numara in range(1, sinir_sayfa + 1):
        if sum(p["pdf_sayfa"] == numara for p in sayfa_kayitlari) != 1:
            sonuc["kapsam_sorunlari"].append({"pdf_sayfa": numara, "gerekce": "Sayfa eksik veya tekrarlı."})
    for p in sayfa_kayitlari:
        if p["pdf_sayfa"] > sinir_sayfa:
            continue
        ham = p["metin"][:sinir] if p["pdf_sayfa"] == sinir_sayfa else p["metin"]
        if p["metin_durumu"] != "okunabilir" or not p["metin"].strip():
            sonuc["kapsam_sorunlari"].append({"pdf_sayfa": p["pdf_sayfa"], "metin_durumu": p["metin_durumu"]})
        alanlar.append((p, ham))
        for satir in ham.splitlines():
            anahtar = _karsilastirma_metni(satir)
            if anahtar:
                tekrarlar.setdefault(anahtar, set()).add(p["pdf_sayfa"])

    for p, ham in alanlar:
        gorunum, harita = _konumlu_normalize_metin(ham)
        cift_araliklari = []
        for desen, iki_yazar in ((cift, True), (tek, False)):
            for eslesme in desen.finditer(gorunum):
                if not iki_yazar and any(a < eslesme.end() and eslesme.start() < b for a, b in cift_araliklari):
                    continue
                isimler = [eslesme["ilk"]] + ([eslesme["ikinci"]] if iki_yazar else [])
                bulunan = [re.findall(r"[a-z]+", i)[-1] for i in isimler]
                oranlar = [SequenceMatcher(None, s, t).ratio() for s, t in zip(bulunan, soyadlar)]
                ilgili = (any(s in soyadlar for s in bulunan) or
                          (iki_yazar and all(o >= 0.8 for o in oranlar)))
                if not ilgili:
                    continue
                a, b = harita[eslesme.start()], harita[eslesme.end() - 1] + 1
                if iki_yazar:
                    cift_araliklari.append(eslesme.span())
                gerekceler = []
                yazar_uyum = iki_yazar and bulunan == soyadlar
                if not yazar_uyum:
                    gerekceler.append("Eksik/farklı yazar soyadı; otomatik düzeltme yapılmadı.")
                yil_uyum = eslesme["yil"] == str(hedef_eser["year"])
                if not yil_uyum:
                    gerekceler.append("Yıl veya yıl eki hedefle farklı.")
                for sira, isim in enumerate(isimler):
                    verilen = re.findall(r"\b([a-z])\.", isim)
                    if verilen and verilen != bas_harfler[sira][:len(verilen)]:
                        gerekceler.append("Açık yazar baş harfleri hedefle uyuşmuyor.")
                satir_a = ham.rfind("\n", 0, a) + 1
                satir_b = ham.find("\n", b)
                satir = ham[satir_a:satir_b if satir_b >= 0 else len(ham)]
                if re.search(r"Journal|Dergisi|ISSN|Copyright|©", satir, re.IGNORECASE) or len(tekrarlar.get(_karsilastirma_metni(satir), set())) > 1:
                    gerekceler.append("Üstbilgi/altbilgi veya tekrarlanan satır riski.")
                if re.search(r"(?:©\s*Copyright|E-ISSN)", ham[:a], re.IGNORECASE):
                    gerekceler.append("Öncesinde telif/ISSN bölgesi var; ana metin kullanımı kesinleştirilmedi.")
                sonuc["adaylar"].append({
                    "pdf_sayfa": p["pdf_sayfa"], "orijinal_karakter_baslangic": a,
                    "orijinal_karakter_bitis": b, "ham_atif_metni": ham[a:b],
                    "yazar_kanitlari": bulunan, "yazar_uyumu": yazar_uyum,
                    "yil_kaniti": eslesme["yil"], "yil_uyumu": yil_uyum,
                    "durum": "incelenmeli" if gerekceler else "bulundu",
                    "gerekce": " ".join(gerekceler) if gerekceler else "İki soyad ve yıl uyumlu sözdizimsel atıf; kişi/eser/iddia doğruluğu ayrıca değerlendirilmelidir.",
                })
    sonuc["adaylar"].sort(key=lambda a: (a["pdf_sayfa"], a["orijinal_karakter_baslangic"]))
    if sonuc["kapsam_sorunlari"]:
        sonuc["durum"] = "incelenmeli" if sonuc["adaylar"] else "degerlendirilemedi"
    elif sonuc["adaylar"]:
        sonuc["durum"] = "bulundu" if any(a["durum"] == "bulundu" for a in sonuc["adaylar"]) else "incelenmeli"
    else:
        sonuc["durum"] = "bulunamadi"
    sonuc["gerekce"] = "Yalnızca kaynakça öncesi tarandı; bulunamama öğrenci hatası değildir. Soyad-yıl tek başına aynı soyadlı kişileri ayıramaz."
    return sonuc


def atif_kontrolunu_raporla(sayfa_kayitlari, baslangic_bilgisi, kayit_bilgileri, hedef_eser):
    """Kaynakça kimliği ile ana metin kullanımını birbirinden ayrı döndürür."""
    degerlendirilmis = kayit_sinirlarini_kanitla_degerlendir(kayit_bilgileri)
    return {
        "kaynakca_sonucu": hedef_eseri_eslestir(degerlendirilmis, hedef_eser),
        "metin_ici_sonucu": metin_ici_atif_adaylarini_bul(sayfa_kayitlari, baslangic_bilgisi, hedef_eser),
        "sinir_degerlendirmeleri": degerlendirilmis.get("sinir_degerlendirmeleri", []),
        "kalan_sinir_belirsizlikleri": kayit_sinirlarini_incele(degerlendirilmis),
        "gerekce": "Kaynakçada bulunma ve metin içi atıf birbirinin kanıtı sayılmadı; manuel kararlar değiştirilmedi.",
    }


def _kayit_yazar_yil_kanitlari(kayit):
    """Yazar ön ekini ve yılı çıkarır; başlıktaki soyadları yazar saymaz."""
    ham = "".join(p["metin"] for p in kayit["ham_metin_parcalari"])
    yil = re.search(r"\((?P<yil>(?:18|19|20)\d{2}[a-z]?)\)", ham, re.IGNORECASE)
    onek = ham[:yil.start()] if yil else ""
    harf = r"[^\W\d_]"
    kelime = rf"{harf}+(?:[-'’]{harf}+)*"
    desen = re.compile(
        rf"(?P<soyad>{kelime}(?:[ \t]+{kelime}){{0,3}}),\s*"
        rf"(?P<adlar>(?:[A-ZÇĞİÖŞÜ]\.\s*){{1,3}}|{kelime}(?:\s+[A-ZÇĞİÖŞÜ]\.)*)"
    )
    yazarlar = []
    for eslesme in desen.finditer(onek):
        adlar = re.findall(harf + "+", eslesme["adlar"])
        yazarlar.append({"soyad": _karsilastirma_metni(_baglac_at(eslesme["soyad"])),
                        "bas_harfler": [_karsilastirma_metni(a)[0] for a in adlar],
                        "ham_yazar": eslesme[0]})
    return {"yazarlar": yazarlar, "yil": yil["yil"].casefold() if yil else None}


def _atif_yil_sayfa_kanitlari(atif):
    """Atıftaki yıl ve sayfa yer belirtecini ayrı tutar; ham metni korur."""
    ham = atif["ham_atif_metni"]
    yil = re.search(r"(?<!\d)((?:18|19|20)\d{2}[a-z]?)(?!\d)", ham, re.IGNORECASE)
    sayfa = re.match(r"\s*[:,]\s*(?:s\.?\s*)?(\d+(?:\s*[-–]\s*\d+)?)", ham[yil.end():]) if yil else None
    gorunum, _ = _konumlu_normalize_metin(ham)
    bas_harfler = {
        m["soyad"]: re.findall(r"[a-z]", m["harfler"])
        for m in re.finditer(r"(?P<harfler>(?:[a-z]\.\s*){1,3})(?P<soyad>[a-z]+)", gorunum)
    }
    return {"yil": yil[1].casefold() if yil else None,
            "sayfa_bilgisi": sayfa[1] if sayfa else None,
            "bas_harfler": bas_harfler}


def atif_kaynakca_baglantilarini_kur(metin_ici_sonucu, kayit_bilgileri, hedef_eser):
    """Atıf adaylarını bütün makul kaynakça adaylarıyla karşılaştırır.

    Aynı yazar/yıldaki farklı başlıklar birlikte korunur. Metinde başlık
    bulunmaması çelişki değildir. baglandi; bilimsel destek, atıf stili veya
    aynı soyadlı kişilerin dış kaynaklarla doğrulanması anlamına gelmez.
    """
    sonuc = {"durum": "degerlendirilemedi", "baglantilar": [],
             "hedef_eser": deepcopy(hedef_eser), "gerekce": ""}
    if (kayit_bilgileri.get("durum") != "kayitlar_olusturuldu" or not kayit_bilgileri.get("kayitlar") or
            metin_ici_sonucu.get("durum") == "degerlendirilemedi"):
        sonuc["gerekce"] = "Kaynakça veya ana metin verisi güvenilir değerlendirilemiyor."
        return sonuc
    kimlik_sonucu = hedef_eseri_eslestir(kayit_bilgileri, hedef_eser)
    kimlikler = {a["kayit_id"]: a for a in kimlik_sonucu["aday_kayitlar"]}
    hedef_yazarlar = {
        _karsilastirma_metni(a.split()[-1]): [_karsilastirma_metni(k)[0] for k in a.split()[:-1]]
        for a in hedef_eser.get("authors", [])
    }
    tum_yazarlar = {k["kayit_id"]: _kayit_yazar_yil_kanitlari(k) for k in kayit_bilgileri["kayitlar"]}
    kapsam_sorunlu = bool(metin_ici_sonucu.get("kapsam_sorunlari"))
    kayitlar_belirsiz = any(k["durum"] != "olusturuldu" for k in kayit_bilgileri["kayitlar"])
    kayitlar_belirsiz |= any(
        "atanmamış" in p.get("gerekce", "") or "telif" in p.get("gerekce", "")
        for p in kayit_bilgileri.get("kayit_disi_bolgeler", [])
    )
    for atif in metin_ici_sonucu.get("adaylar", []):
        tarih = _atif_yil_sayfa_kanitlari(atif)
        atif_yazarlar = atif.get("yazar_kanitlari", [])
        adaylar = []
        for kayit in kayit_bilgileri["kayitlar"]:
            bilgi = tum_yazarlar[kayit["kayit_id"]]
            soyadlar = [a["soyad"] for a in bilgi["yazarlar"]]
            yil_uyum = bool(tarih["yil"] and tarih["yil"] == bilgi["yil"])
            yazar_uyum = bool(atif_yazarlar) and atif_yazarlar == soyadlar
            ortak = set(atif_yazarlar) & set(soyadlar)
            yakin = len(atif_yazarlar) == len(soyadlar) and bool(soyadlar) and all(
                SequenceMatcher(None, a, b).ratio() >= 0.8 for a, b in zip(atif_yazarlar, soyadlar)
            )
            kimlik = kimlikler.get(kayit["kayit_id"])
            if not ((yil_uyum and (ortak or yakin)) or (yazar_uyum and not yil_uyum) or kimlik):
                continue
            celiskiler, belirsizlikler = [], list(kayit.get("belirsizlik_gerekceleri", []))
            if not yazar_uyum:
                celiskiler.append("Yazar listesi eksik veya farklı; soyadlar otomatik düzeltilmedi.")
            if not yil_uyum:
                celiskiler.append("Metin içi yıl/eki ile kaynakça yılı/eki farklı veya eksik.")
            for yazar in bilgi["yazarlar"]:
                soyad, harfler = yazar["soyad"], yazar["bas_harfler"]
                acik_harfler = tarih["bas_harfler"].get(soyad)
                hedef_harfler = hedef_yazarlar.get(soyad)
                if acik_harfler and harfler and acik_harfler != harfler[:len(acik_harfler)]:
                    celiskiler.append("Atıf ile kaynakçadaki açık yazar baş harfleri uyuşmuyor.")
                if kimlik and hedef_harfler and harfler and harfler != hedef_harfler[:len(harfler)]:
                    celiskiler.append("Kaynakça yazar baş harfleri hedef kişiden farklı; aynı soyad farklı kişi riski.")
            if kimlik:
                celiskiler.extend(deepcopy(kimlik["celiskiler"]))
            if kayit["durum"] != "olusturuldu" and not belirsizlikler:
                belirsizlikler.append("Kaynakça kayıt sınırı belirsiz.")
            if atif["durum"] != "bulundu":
                belirsizlikler.append(atif.get("gerekce", "Metin içi aday belirsiz."))
            if not kimlik or kimlik["durum"] != "eslesti":
                belirsizlikler.append("Hedef eser kimliği bu kaynakça kaydı için kesinleşmedi.")
            adaylar.append({
                "kayit_id": kayit["kayit_id"],
                "pdf_konumlari": _pdf_konumlari(kayit["ham_metin_parcalari"]),
                "ham_metin_parcalari": deepcopy(kayit["ham_metin_parcalari"]),
                "yazar_yil_kanitlari": deepcopy(bilgi),
                "yazar_uyumu": yazar_uyum, "yil_uyumu": yil_uyum,
                "eser_kimligi_kanitlari": deepcopy(kimlik),
                "bibliyografik_farklar": deepcopy(kimlik["bibliyografik_farklar"]) if kimlik else [],
                "celiskiler": celiskiler, "belirsizlikler": belirsizlikler,
                "ayni_yil_makul_aday": yil_uyum and bool(ortak or yakin),
            })
        makul = [a for a in adaylar if a["ayni_yil_makul_aday"]]
        if kapsam_sorunlu:
            durum, gerekce = "degerlendirilemedi", "Eksik/okunamayan sayfalar nedeniyle kapsam güvenilir değil."
        elif len(makul) > 1:
            durum, gerekce = "incelenmeli", "Aynı yazar/yıl için birden fazla makul kaynak var; hepsi korundu."
        elif len(makul) == 1 and not makul[0]["celiskiler"] and not makul[0]["belirsizlikler"]:
            durum, gerekce = "baglandi", "Tek makul kaynak, yazar/yıl ve bağımsız hedef kimliği kanıtlarıyla desteklendi."
        elif adaylar or atif["durum"] != "bulundu" or kayitlar_belirsiz:
            durum, gerekce = "incelenmeli", "Eksik bilgi, kimlik/sınır belirsizliği veya çelişki nedeniyle kesin bağlantı yok."
        else:
            durum, gerekce = "baglanamadi", "İncelenen kayıtlar içinde uygun bağlantı bulunamadı; öğrenci hatası kararı değildir."
        sonuc["baglantilar"].append({
            "pdf_sayfa": atif["pdf_sayfa"],
            "orijinal_karakter_baslangic": atif["orijinal_karakter_baslangic"],
            "orijinal_karakter_bitis": atif["orijinal_karakter_bitis"],
            "ham_atif_metni": atif["ham_atif_metni"],
            "atif_kanitlari": {"yazarlar": list(atif_yazarlar), **tarih,
                               "baslik": "Metin içi atıfta yok; çelişki sayılmadı."},
            "aday_kayit_kimlikleri": [a["kayit_id"] for a in adaylar],
            "aday_kayitlar": adaylar,
            "celiskiler": [{"kayit_id": a["kayit_id"], "ayrinti": c} for a in adaylar for c in a["celiskiler"]],
            "belirsizlikler": [b for a in adaylar for b in a["belirsizlikler"]],
            "durum": durum, "gerekce": gerekce,
        })
    if kapsam_sorunlu:
        sonuc["durum"] = "degerlendirilemedi"
    elif not sonuc["baglantilar"]:
        sonuc["durum"] = "incelenmeli" if kayitlar_belirsiz else "baglanamadi"
    else:
        durumlar = {b["durum"] for b in sonuc["baglantilar"]}
        sonuc["durum"] = next(iter(durumlar)) if len(durumlar) == 1 else "incelenmeli"
    sonuc["gerekce"] = "Her atıf ayrı değerlendirildi; kaynakçada eser yokluğu, bilimsel destek veya biçim doğruluğu çıkarılmadı."
    return sonuc


def atif_kaynakca_raporunu_olustur(sayfa_kayitlari, baslangic_bilgisi, kayit_bilgileri, hedef_eser):
    """Önceki iki sonucu koruyup bağlantıları üçüncü, ayrı sonuç olarak ekler."""
    sonuc = atif_kontrolunu_raporla(sayfa_kayitlari, baslangic_bilgisi, kayit_bilgileri, hedef_eser)
    kayitlar = kayit_sinirlarini_kanitla_degerlendir(kayit_bilgileri)
    sonuc["baglanti_sonucu"] = atif_kaynakca_baglantilarini_kur(sonuc["metin_ici_sonucu"], kayitlar, hedef_eser)
    return sonuc