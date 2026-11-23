from pathlib import Path
import pymupdf


def pdf_sayfa_metinlerini_cikar(pdf_yolu):
    """Ham sayfa metinlerini, 1 tabanlı PDF sırası ve çıkarma durumuyla döndürür.

    Basılı sayfa numarasını belirlemez; OCR, ağ veya dosya yazımı yapmaz.
    'okunabilir', yalnızca boş olmayan metin çıkarıldığını belirtir;
    metnin doğruluğunu veya OCR kalitesini garanti etmez.
    """
    pdf_yolu = Path(pdf_yolu)
    if not pdf_yolu.is_file():
        raise FileNotFoundError(f"PDF bulunamadı: {pdf_yolu}")

    try:
        belge = pymupdf.open(pdf_yolu)
    except Exception as hata:
        raise ValueError(f"PDF açılamadı: {pdf_yolu}: {hata}") from hata

    with belge:
        if not belge.is_pdf:
            raise ValueError(f"Dosya geçerli bir PDF değil: {pdf_yolu}")
        if belge.needs_pass:
            raise ValueError(f"PDF parola gerektiriyor: {pdf_yolu}")

        sayfalar = []
        for sira in range(belge.page_count):
            try:
                metin = belge.load_page(sira).get_text("text")
                durum = "okunabilir" if metin.strip() else "bos"
            except Exception:
                # Hatalı sayfanın PDF sırasını koru; sonraki sayfaları işlemeye devam et.
                metin = ""
                durum = "cikarma_hatasi"

            sayfalar.append({
                "pdf_sayfa": sira + 1,
                "metin": metin,
                "metin_durumu": durum,
            })

    return sayfalar


def kaynakca_baslangicini_bul(sayfa_kayitlari):
    """Bağımsız kaynakça başlıklarını ham metindeki konumlarıyla değerlendirir.

    Son yarıdaki başlık ve onu izleyen en fazla 2000 karakterdeki yıl işareti
    yalnızca başlangıç adayı kanıtıdır; kaynak kayıtları veya atıflar doğrulanmaz.
    İndeksler sıfır tabanlıdır; karakter_bitis başlığın hemen sonrasıdır.
    Boş sayfa OCR gerektirebileceğinden eksik çıkarımla kesin karar verilmez.
    """
    import re

    if not sayfa_kayitlari:
        return {"durum": "degerlendirilemedi", "adaylar": [],
                "gerekce": "Sayfa kaydı yok."}

    baslik_deseni = re.compile(
        r"^[ \t]*(?P<baslik>kaynakça|references)[ \t]*\r?$",
        re.IGNORECASE | re.MULTILINE,
    )
    yil_deseni = re.compile(r"\b(?:18|19|20)\d{2}[a-z]?\b", re.IGNORECASE)
    adaylar = []
    sorunlu_sayfalar = []

    for sira, kayit in enumerate(sayfa_kayitlari):
        # Okuma hatası her yerde durdurur. Boş sayfa yalnızca belgenin ikinci yarısındaysa
        # durdurur (kaynakça orada başlar); ilk yarıdaki kapak/ara boş sayfa kaynakçayı gizleyemez.
        ikinci_yari = sira >= len(sayfa_kayitlari) // 2
        if kayit["metin_durumu"] not in ("okunabilir", "bos") or (
                ikinci_yari and (kayit["metin_durumu"] != "okunabilir" or not kayit["metin"].strip())):
            sorunlu_sayfalar.append(kayit["pdf_sayfa"])

        for eslesme in baslik_deseni.finditer(kayit["metin"]):
            # Devam eden kaynakça bir sonraki sayfada başlayabilir.
            devam = kayit["metin"][eslesme.end("baslik"):][:2000]
            if len(devam) < 2000 and sira + 1 < len(sayfa_kayitlari):
                devam += "\n" + sayfa_kayitlari[sira + 1]["metin"][:2000 - len(devam)]
            son_yarida = sira >= len(sayfa_kayitlari) // 2
            yil_var = bool(yil_deseni.search(devam))
            adaylar.append({
                "pdf_sayfa": kayit["pdf_sayfa"],
                "baslik": eslesme.group("baslik"),
                "karakter_baslangic": eslesme.start("baslik"),
                "karakter_bitis": eslesme.end("baslik"),
                "son_yarida": son_yarida,
                "devaminda_yil_var": yil_var,
            })

    if sorunlu_sayfalar:
        return {"durum": "degerlendirilemedi", "adaylar": adaylar,
                "sorunlu_pdf_sayfalari": sorunlu_sayfalar,
                "gerekce": "Boş veya çıkarılamayan sayfalar nedeniyle kapsam güvenilir değil."}
    if not adaylar:
        return {"durum": "bulunamadi", "adaylar": []}

    uygun_adaylar = [a for a in adaylar if a["son_yarida"] and a["devaminda_yil_var"]]
    if len(uygun_adaylar) != 1:
        return {"durum": "incelenmeli", "adaylar": adaylar,
                "gerekce": "Tek bir uygun kaynakça başlangıcı belirlenemedi."}

    secilen = uygun_adaylar[0]
    return {
        "durum": "bulundu",
        "pdf_sayfa": secilen["pdf_sayfa"],
        "baslik": secilen["baslik"],
        "karakter_baslangic": secilen["karakter_baslangic"],
        "karakter_bitis": secilen["karakter_bitis"],
        "adaylar": adaylar,
    }


def kaynakca_sayfalarini_ayir(sayfa_kayitlari, baslangic_bilgisi):
    """Başlık sonrasından belge sonuna kadar geçici kaynakça bölgesini döndürür.

    Sonuç, durum/gerekçe ve sayfalar listesini içerir. Bölgedeki üstbilgi, ek
    veya diğer metinler temizlenmez ve gerçek kaynakça kaydı kabul edilmez.
    Karakter aralıkları orijinal sayfaya göre sıfır tabanlı, bitiş hariçtir.
    """
    durum = baslangic_bilgisi.get("durum")
    if durum != "bulundu":
        return {
            "durum": durum if durum in {
                "incelenmeli", "bulunamadi", "degerlendirilemedi"
            } else "degerlendirilemedi",
            "gerekce": baslangic_bilgisi.get("gerekce")
                or "Kaynakça başlangıcı kesin belirlenmedi; ayırma yapılmadı.",
            "sayfalar": [],
        }

    eslesen_siralar = [
        sira for sira, kayit in enumerate(sayfa_kayitlari)
        if kayit["pdf_sayfa"] == baslangic_bilgisi.get("pdf_sayfa")
    ]
    if len(eslesen_siralar) != 1:
        return {"durum": "degerlendirilemedi", "sayfalar": [],
                "gerekce": "Başlangıç sayfası tekil olarak bulunamadı."}

    ilk_sira = eslesen_siralar[0]
    ilk_metin = sayfa_kayitlari[ilk_sira]["metin"]
    baslangic = baslangic_bilgisi.get("karakter_baslangic")
    bitis = baslangic_bilgisi.get("karakter_bitis")
    if not (
        isinstance(baslangic, int) and isinstance(bitis, int)
        and 0 <= baslangic < bitis <= len(ilk_metin)
        and ilk_metin[baslangic:bitis] == baslangic_bilgisi.get("baslik")
    ):
        return {"durum": "degerlendirilemedi", "sayfalar": [],
                "gerekce": "Başlık veya karakter aralığı orijinal sayfa metniyle uyuşmuyor."}

    sayfalar = []
    for sira in range(ilk_sira, len(sayfa_kayitlari)):
        kayit = sayfa_kayitlari[sira]
        dilim_baslangici = bitis if sira == ilk_sira else 0
        sayfalar.append({
            "pdf_sayfa": kayit["pdf_sayfa"],
            "metin": kayit["metin"][dilim_baslangici:],
            "metin_durumu": kayit["metin_durumu"],
            "orijinal_karakter_baslangic": dilim_baslangici,
            "orijinal_karakter_bitis": len(kayit["metin"]),
        })

    return {"durum": "ayrildi", "sayfalar": sayfalar,
            "gerekce": "Belge sonuna kadar geçici bölge; her metin kaynakça kaydı değildir."}


def kaynakca_satirlarini_cikar(kaynakca_bolgesi):
    """Geçici kaynakça bölgesini ham satırlara ve orijinal aralıklara böler.

    Boş satırlar ve satır sonları korunur; hiçbir satır kaynak kaydı sayılmaz.
    Geçersiz bölge veya çıkarma hatasında gerekçeli durum döndürülür.
    """
    if not isinstance(kaynakca_bolgesi, dict):
        return {"durum": "degerlendirilemedi", "satirlar": [],
                "gerekce": "Kaynakça bölgesi sözlük olmalı."}
    durum = kaynakca_bolgesi.get("durum")
    if durum != "ayrildi":
        return {
            "durum": durum if durum in {
                "incelenmeli", "bulunamadi", "degerlendirilemedi"
            } else "degerlendirilemedi",
            "satirlar": [],
            "gerekce": kaynakca_bolgesi.get("gerekce")
                or "Kaynakça bölgesi ayrılmadı; satır çıkarma yapılmadı.",
        }

    sayfalar = kaynakca_bolgesi.get("sayfalar")
    if not isinstance(sayfalar, list) or not sayfalar:
        return {"durum": "degerlendirilemedi", "satirlar": [],
                "gerekce": "Geçerli kaynakça sayfaları bulunamadı."}

    onceki_sayfa = 0
    sorunlu_sayfalar = []
    for sayfa in sayfalar:
        if not isinstance(sayfa, dict):
            return {"durum": "degerlendirilemedi", "satirlar": [],
                    "gerekce": "Geçersiz sayfa kaydı."}
        numara = sayfa.get("pdf_sayfa")
        metin = sayfa.get("metin")
        baslangic = sayfa.get("orijinal_karakter_baslangic")
        bitis = sayfa.get("orijinal_karakter_bitis")
        if not (
            type(numara) is int and numara > onceki_sayfa
            and isinstance(metin, str)
            and type(baslangic) is int and type(bitis) is int
            and 0 <= baslangic <= bitis and bitis - baslangic == len(metin)
        ):
            return {"durum": "degerlendirilemedi", "satirlar": [],
                    "gerekce": "Sayfa sırası, ham metin veya karakter aralığı geçersiz."}
        onceki_sayfa = numara
        if sayfa.get("metin_durumu") not in {"okunabilir", "bos"}:
            sorunlu_sayfalar.append({
                "pdf_sayfa": numara,
                "metin_durumu": sayfa.get("metin_durumu"),
            })

    if sorunlu_sayfalar:
        return {"durum": "degerlendirilemedi", "satirlar": [],
                "sorunlu_sayfalar": sorunlu_sayfalar,
                "gerekce": "Çıkarma hatası veya bilinmeyen metin durumu; satırlar üretilmedi."}

    satirlar = []
    for sayfa in sayfalar:
        konum = sayfa["orijinal_karakter_baslangic"]
        for metin in sayfa["metin"].splitlines(keepends=True):
            bitis = konum + len(metin)
            satirlar.append({
                "pdf_sayfa": sayfa["pdf_sayfa"],
                "metin": metin,
                "orijinal_karakter_baslangic": konum,
                "orijinal_karakter_bitis": bitis,
            })
            konum = bitis

    return {"durum": "satirlar_cikarildi", "satirlar": satirlar,
            "gerekce": "Ham satırlar korundu; kaynakça kaydı sınıflandırması yapılmadı."}


def kaynakca_baslangic_adaylarini_bul(satir_bilgileri):
    """Yazar/yıl örüntülerinden başlangıç adayları önerir; kayıt birleştirmez.

    Ham satırlar ve konumlar aynen korunur. Sonraki en fazla üç satır yalnızca
    aynı sayfada kanıt olarak incelenir; sayfa geçişinde kesin devam kararı yoktur.
    guclu_aday, bibliyografik doğrulama veya kesin kayıt sınırı anlamına gelmez.
    """
    import re

    if not isinstance(satir_bilgileri, dict):
        return {"durum": "degerlendirilemedi", "adaylar": [],
                "gerekce": "Satır bilgileri sözlük olmalı."}
    if satir_bilgileri.get("durum") != "satirlar_cikarildi":
        return {"durum": satir_bilgileri.get("durum", "degerlendirilemedi"),
                "adaylar": [], "gerekce": satir_bilgileri.get("gerekce")
                or "Güvenilir satır çıkarımı yok; aday aranmadı."}
    satirlar = satir_bilgileri.get("satirlar")
    if not isinstance(satirlar, list):
        return {"durum": "degerlendirilemedi", "adaylar": [],
                "gerekce": "Satır listesi bulunamadı."}

    harf = r"[^\W\d_]"
    kelime = rf"{harf}+(?:['’\-]{harf}+)*"
    soyad = rf"{kelime}(?:[ \t]+{kelime}){{0,3}}"
    kisi = re.compile(rf"^{soyad},\s*(?:{harf}\.|{kelime})", re.UNICODE)
    bolunmus_soyad = re.compile(rf"^{soyad},\s*$", re.UNICODE)
    yil = re.compile(r"\((?:18|19|20)\d{2}[a-z]?\)", re.IGNORECASE)
    kurum = re.compile(
        r"^(?:SAP\b|Türk Dil Kurumu\b|Sayıştay\b|E-Ticaret Bilgi Platformu\b|UİB\.)"
    )
    genel_kurum = re.compile(rf"^{soyad}\.?\s*\((?:18|19|20)\d{{2}}[a-z]?\)")
    devam = re.compile(r"^Frontiers,\s*Cilt\b", re.IGNORECASE)
    suslu_metin = re.compile(
        r"Journal of Current Researches|/\s*Journal of Yasar University|"
        r"^\d+\s+.*\(\d{4}\)|^SAP Systems\s*$|ISSN|Copyright|"
        r"Strategic Research Academy|copyright holder|^sites or posted|"
        r"^of Strategic Research|^However, users may", re.IGNORECASE
    )
    adaylar = []
    supheli_satirlar = []
    for sira, satir in enumerate(satirlar):
        ham = satir["metin"]
        # Bu görünüm yalnızca örüntü kontrolü içindir; çıktı ham metindir.
        gorunum = ham.strip()
        if not gorunum:
            continue
        kayit = {
            "pdf_sayfa": satir["pdf_sayfa"],
            "orijinal_karakter_baslangic": satir["orijinal_karakter_baslangic"],
            "orijinal_karakter_bitis": satir["orijinal_karakter_bitis"],
            "ham_satir": ham,
        }
        if devam.search(gorunum) or suslu_metin.search(gorunum) or gorunum.isdecimal():
            supheli_satirlar.append({
                **kayit, "durum": "incelenmeli",
                "gerekce": "Devam satırı/üstbilgi/sayfa numarası/telif olasılığı; başlangıç adayı yapılmadı.",
            })
            continue

        kisi_var = bool(kisi.match(gorunum))
        kurum_var = bool(kurum.match(gorunum))
        bolunmus = bool(bolunmus_soyad.match(gorunum))
        if not (kisi_var or kurum_var or bolunmus or genel_kurum.match(gorunum)):
            continue

        ayni_satirda_yil = bool(yil.search(gorunum))
        kanit = [kayit]
        sonraki_yil = False
        # Yalnızca eksik başlangıçlarda kısa bir ileri bakış; satırlar birleştirilmez.
        if not ayni_satirda_yil:
            for sonraki in satirlar[sira + 1:sira + 4]:
                if sonraki["pdf_sayfa"] != satir["pdf_sayfa"]:
                    break
                if kisi.match(sonraki["metin"].strip()):
                    break
                kanit.append({
                    "pdf_sayfa": sonraki["pdf_sayfa"],
                    "orijinal_karakter_baslangic": sonraki["orijinal_karakter_baslangic"],
                    "orijinal_karakter_bitis": sonraki["orijinal_karakter_bitis"],
                    "ham_satir": sonraki["metin"],
                })
                if yil.search(sonraki["metin"]):
                    sonraki_yil = True
                    break

        guclu = (kisi_var or kurum_var) and ayni_satirda_yil
        if bolunmus and sonraki_yil:
            # Baş harf kanıtı olmadan yalnız soyad ve sonraki yıl yeterli değildir.
            guclu = any(re.fullmatch(rf"{harf}\.", k["ham_satir"].strip()) for k in kanit[1:])
        gerekce = (
            "Kişi/kurum başlangıcı ve parantezli yıl aynı satırda."
            if ayni_satirda_yil else
            "Yıl aynı sayfadaki izleyen satırda; bölünmüş başlangıç kanıtları eklendi."
            if sonraki_yil else
            "Yazar/kurum görünümü var; yakın yıl kanıtı yok, sayfa devamı da incelenmeli."
        )
        if not (kisi_var or kurum_var or bolunmus):
            gerekce = "Olası kurum adı ve yıl; kurum kimliği doğrulanmadı."
        adaylar.append({**kayit, "durum": "guclu_aday" if guclu else "incelenmeli",
                        "gerekce": gerekce, "kanit_satirlari": kanit})

    return {"durum": "adaylar_belirlendi", "adaylar": adaylar,
            "supheli_satirlar": supheli_satirlar,
            "gerekce": "Başlangıç önerileri; kesin kayıt sınırı veya eser eşleşmesi değildir."}


def _kaynakca_sinirini_degerlendir(aday):
    """Aday gücünden bağımsız ikinci, yalnızca yapısal sınır kontrolü."""
    import re

    satir = aday["ham_satir"].strip()
    yil = re.search(r"\((?:18|19|20)\d{2}[a-z]?\)", satir, re.IGNORECASE)
    kurum = re.match(
        r"^(?:SAP\b|Türk Dil Kurumu\b|Sayıştay\b|E-Ticaret Bilgi Platformu\b|UİB\.)",
        satir,
    )
    if yil:
        onek = satir[:yil.start()]
        # Uzun/cümle niteliğindeki ön ekler veya yayın alanları sınır sayılmaz.
        yayin_alani = re.search(r"\b(?:Cilt|Sayı|Journal|Dergisi|ss)\b", onek, re.IGNORECASE)
        if (kurum or "," in onek) and len(onek) <= 180 and not yayin_alani:
            return {"sinir": True, "durum": "olusturuldu",
                    "gerekce": "Başlangıç ön eki ve aynı satırdaki yıl yapısal olarak uyumlu; eser doğrulanmadı."}

    kanit = aday.get("kanit_satirlari", [])
    # Yıl yalnızca başlangıçtan hemen sonra baş harf/kurum devamıyla gelmeli.
    parcalar = [k["ham_satir"].strip() for k in kanit[1:]]
    bas_harf = bool(parcalar and re.fullmatch(r"[^\W\d_]\.", parcalar[0]))
    bolunmus_yil = any(re.match(r"^\((?:18|19|20)\d{2}[a-z]?\)", p) for p in parcalar)
    if bolunmus_yil and (kurum or (satir.endswith(",") and bas_harf)):
        return {"sinir": True, "durum": "incelenmeli",
                "gerekce": "Bölünmüş başlangıç: baş harf/kurum ve sonraki yıl destekliyor; sınır geçici."}

    return {"sinir": False, "durum": "incelenmeli",
            "gerekce": "Aday tek başına yeni kayıt sınırı için yeterli değil; devam veya yeni başlangıç olabilir."}


def kaynakca_kayitlarini_olustur(satir_bilgileri, aday_bilgileri=None):
    """Ham satırları kayıplarsız, geçici çok satırlı kayıtlara yerleştirir.

    Kayıtlar, kayıt dışı bölgeler ve alternatif sınırlar ayrı döndürülür.
    olusturuldu yalnızca yapısal gruplamadır; bibliyografik doğruluk değildir.
    Kanıt/alternatif sınır referansları sahiplik taşımaz: karakterler yalnızca
    ham_metin_parcalari veya kayit_disi_bolgeler içinde bir kez temsil edilir.
    """
    import copy
    import re

    def hata(gerekce):
        return {"durum": "degerlendirilemedi", "kayitlar": [],
                "kayit_disi_bolgeler": [], "sinir_kararlari": [], "gerekce": gerekce}

    if not isinstance(satir_bilgileri, dict) or satir_bilgileri.get("durum") != "satirlar_cikarildi":
        sonuc = hata("Güvenilir satır çıkarımı yok; kayıt oluşturulmadı.")
        if isinstance(satir_bilgileri, dict):
            sonuc["girdi_durumu"] = satir_bilgileri.get("durum")
            sonuc["girdi_gerekcesi"] = satir_bilgileri.get("gerekce")
        return sonuc
    satirlar = satir_bilgileri.get("satirlar")
    if not isinstance(satirlar, list):
        return hata("Satır listesi bulunamadı.")

    konumlar = {}
    onceki = None
    for satir in satirlar:
        if not isinstance(satir, dict):
            return hata("Geçersiz satır kaydı.")
        sayfa = satir.get("pdf_sayfa")
        a = satir.get("orijinal_karakter_baslangic")
        b = satir.get("orijinal_karakter_bitis")
        metin = satir.get("metin")
        if not (type(sayfa) is int and sayfa > 0 and type(a) is int and type(b) is int
                and isinstance(metin, str) and 0 <= a < b and b - a == len(metin)):
            return hata("Satır metni veya karakter aralığı geçersiz.")
        if onceki and (sayfa < onceki[0] or (sayfa == onceki[0] and a != onceki[1])):
            return hata("Satır sırası bozuk veya aralıklarda boşluk/çakışma var.")
        onceki = (sayfa, b)
        konumlar[(sayfa, a, b)] = satir

    if aday_bilgileri is None:
        aday_bilgileri = kaynakca_baslangic_adaylarini_bul(satir_bilgileri)
    if not isinstance(aday_bilgileri, dict) or aday_bilgileri.get("durum") != "adaylar_belirlendi":
        return hata("Başlangıç adayları değerlendirilemedi.")
    adaylar = {}
    for aday in aday_bilgileri.get("adaylar", []):
        anahtar = (aday["pdf_sayfa"], aday["orijinal_karakter_baslangic"], aday["orijinal_karakter_bitis"])
        if anahtar not in konumlar or anahtar in adaylar or aday["ham_satir"] != konumlar[anahtar]["metin"]:
            return hata("Aday konumu tekrarlı veya ham satırla uyuşmuyor.")
        adaylar[anahtar] = aday

    kayitlar = []
    dis_bolgeler = []
    kararlar = []
    aktif = None
    telif_sayfasi = None
    ustbilgi_sayfasi = None
    for satir in satirlar:
        sayfa = satir["pdf_sayfa"]
        a = satir["orijinal_karakter_baslangic"]
        b = satir["orijinal_karakter_bitis"]
        gorunum = satir["metin"].strip()
        anahtar = (sayfa, a, b)
        aday = adaylar.get(anahtar)
        karar = _kaynakca_sinirini_degerlendir(aday) if aday else None
        parca = dict(satir)
        dis_gerekce = None
        # Üstbilgiyi yalnızca sayfanın başlangıcında değerlendirmek, kaynak
        # içindeki dergi adını ve yıl satırını yanlışlıkla çıkarmayı sınırlar.
        if a < 200 and re.search(
            r"Journal of Current Researches|/\s*Journal of Yasar University|^\d+\s+.*\(\d{4}\)",
            gorunum, re.IGNORECASE,
        ):
            ustbilgi_sayfasi = sayfa
            dis_gerekce = "Sayfa başında üstbilgi adayı."
        elif a < 200 and (gorunum.isdecimal() or
                (ustbilgi_sayfasi == sayfa and gorunum == "SAP Systems")):
            dis_gerekce = "Sayfa başında numara/üstbilgi devamı adayı."
        if re.match(r"^(?:E-ISSN|ISSN|©\s*Copyright|Strategic Research Academy\s*©)", gorunum, re.IGNORECASE):
            telif_sayfasi = sayfa
        if telif_sayfasi == sayfa:
            dis_gerekce = "ISSN/telif başlangıcından sonraki sayfa sonu bölgesi; inceleme gerekli."
        if not gorunum:
            dis_gerekce = "Boşluk/satır sonu; ham haliyle korundu."

        if dis_gerekce:
            dis_bolgeler.append({**parca, "durum": "incelenmeli", "gerekce": dis_gerekce})
            if aday:
                kararlar.append({"aday": copy.deepcopy(aday), "sinir": False,
                                 "durum": "incelenmeli", "gerekce": dis_gerekce,
                                 "alternatif": "Kayıt dışı varsayımını incele; olası başlangıç bastırılmadı."})
            continue

        if karar:
            kararlar.append({"aday": copy.deepcopy(aday), **karar,
                             "alternatif": "Yeni kayıt başlangıcı veya önceki kaydın devamı; ham konumdan yeniden bölünebilir."})
        if karar and karar["sinir"]:
            if aktif is not None and karar["durum"] == "incelenmeli":
                aktif["durum"] = "incelenmeli"
                aktif["belirsizlik_gerekceleri"].append("Son sınır, bölünmüş bir başlangıç adayına dayanıyor.")
            aktif = {
                "kayit_id": f"K{len(kayitlar) + 1:04d}",
                "durum": karar["durum"], "ham_metin_parcalari": [],
                "baslangic_kanitlari": copy.deepcopy(aday),
                "belirsizlik_gerekceleri": [karar["gerekce"]] if karar["durum"] == "incelenmeli" else [],
            }
            kayitlar.append(aktif)
        elif karar and aktif is not None:
            aktif["durum"] = "incelenmeli"
            aktif["belirsizlik_gerekceleri"].append(
                f"PDF {sayfa} [{a},{b}) alternatif başlangıç olabilir; geçici olarak devam sayıldı."
            )

        if aktif is None:
            dis_bolgeler.append({**parca, "durum": "incelenmeli",
                                "gerekce": "Henüz desteklenen başlangıç yok; atanmamış bölge."})
        else:
            if aktif["ham_metin_parcalari"] and aktif["ham_metin_parcalari"][-1]["pdf_sayfa"] != sayfa:
                aktif["durum"] = "incelenmeli"
                aktif["belirsizlik_gerekceleri"].append("Sayfalar arası devam geçici olarak korundu; ayrılma olasılığı incelenmeli.")
            aktif["ham_metin_parcalari"].append(parca)

    return {"durum": "kayitlar_olusturuldu", "kayitlar": kayitlar,
            "kayit_disi_bolgeler": dis_bolgeler, "sinir_kararlari": kararlar,
            "gerekce": "Geçici yapısal kayıtlar; eser kimliği ve atıf doğrulaması yapılmadı."}


def pdf_metni_cikar(pdf_yolu):
    """PDF dosyasındaki metni sayfa sırasıyla çıkarır."""

    pdf_yolu = Path(pdf_yolu)

    if not pdf_yolu.is_file():
        raise FileNotFoundError(f"PDF bulunamadı: {pdf_yolu}")

    metinler = []

    with pymupdf.open(pdf_yolu) as belge:
        for sayfa in belge:
            metinler.append(sayfa.get_text("text"))

    return "\n".join(metinler)
def kaynakca_metni_cikar(pdf_yolu):
    """PDF metnindeki Kaynakça veya References bölümünü ayırır."""

    import re

    metin = pdf_metni_cikar(pdf_yolu)

    eslesmeler = list(
        re.finditer(
            r"(?im)^\s*(kaynakça|references)\s*$",
            metin
        )
    )

    if not eslesmeler:
        return ""

    # Son kaynakça başlığından itibaren metni al.
    baslangic = eslesmeler[-1].end()

    return metin[baslangic:].strip()