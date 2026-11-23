import html

import pandas as pd
import streamlit as st

from moduller.pdf_analiz import hedef_eser_hazirla, pdf_kontrol_et, ozet, kaynakca_kaydi_metni, kanit_raporunu_metinlestir
from moduller.filtre import (
    TUR_GRUPLARI,
    akademisyen_bul,
    atiflari_filtrele,
    doi_link,
    tur_grubu,
    yil_araligi,
    yil_int,
)
from moduller.veri_yukle import atiflari_yukle, yayinlari_yukle

st.set_page_config(page_title="AtıfBul", page_icon="🔷", layout="wide")

# ==================================================
# TASARIM: açık gri zemin, beyaz yuvarlak kartlar, mavi-beyaz, belirgin çizgiler
# ==================================================

st.markdown(
    """
<style>
.stApp { background: #EEF0F5; }
.block-container { max-width: 1760px; padding: 1.2rem 3rem 3rem; }
header[data-testid="stHeader"] { display: none; }
html, body, .stApp { font-size: 16px; }

h1 { color: #111827; font-weight: 800; font-size: 2.6rem; margin-bottom: 0; }
[data-testid="stCaptionContainer"] p { font-size: 15px; color: #4B5563; }
[data-testid="stWidgetLabel"] p { font-size: 16px; font-weight: 700; color: #111827; }

/* ---------- Üstteki sayfa düğmeleri (Atıf Analizi / PDF Analizi) ---------- */
.st-key-sayfa_menu button { min-height: 62px !important; border-radius: 18px !important; box-shadow: 0 3px 12px rgba(10,96,214,0.25); }
.st-key-sayfa_menu button p { font-size: 20px !important; font-weight: 800 !important; }
.st-key-sayfa_menu button[data-testid="stBaseButton-secondary"] { border: 3px solid #0A60D6 !important; background: #FFFFFF !important; }
.st-key-sayfa_menu { margin-bottom: 8px; }

/* ---------- Kartlar ---------- */
[class*="st-key-kart"] {
    background: #FFFFFF; border: 3px solid #C3C9D4; border-radius: 24px;
    padding: 28px 30px; box-shadow: 0 3px 16px rgba(17,24,39,0.08);
}
.st-key-kart_eser, .st-key-kart_sonuc, .st-key-kart_pdf1, .st-key-kart_pdf2 { min-height: 760px; }
.sec { display: flex; align-items: center; gap: 14px; font-size: 25px; font-weight: 800; color: #111827; }
.num { width: 38px; height: 38px; border-radius: 50%; background: #0A60D6; color: #fff;
       display: inline-flex; align-items: center; justify-content: center; font-size: 19px; flex: none; }
.secalt { font-size: 15px; color: #4B5563; margin: 4px 0 16px 52px; }

/* ---------- Bölüm başlıkları (kart içi) ---------- */
.bolum { margin: 22px 0 8px; padding-top: 16px; border-top: 3px solid #E3E7EE; }
.bolum b { display: block; font-size: 18px; color: #111827; }
.bolum span { display: block; font-size: 14.5px; color: #4B5563; margin-top: 2px; }

/* ---------- Girdi alanları ---------- */
div[data-baseweb="input"], div[data-baseweb="select"] > div {
    border: 2px solid #6B7280 !important; border-radius: 12px !important; background: #FFFFFF !important;
}
div[data-baseweb="input"] input { font-size: 16px; }

/* ---------- Düğmeler ---------- */
button[data-testid="stBaseButton-primary"] {
    background: #0A60D6; color: #FFFFFF; border: 0; border-radius: 999px;
    min-height: 56px; font-size: 18px; font-weight: 800; box-shadow: 0 4px 12px rgba(10,96,214,0.35);
}
button[data-testid="stBaseButton-primary"] p { font-size: 18px; font-weight: 800; }
button[data-testid="stBaseButton-secondary"], .stDownloadButton button {
    background: #FFFFFF; color: #0A60D6; border: 3px solid #0A60D6; border-radius: 999px;
    min-height: 50px; font-weight: 800;
}
.stApp a { color: #0A60D6; font-weight: 700; }

/* ---------- Etkileşimli eser tablosu ---------- */
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {
    border: 3px solid #4B5563; border-radius: 14px; overflow: hidden;
}

/* ---------- Atıf sonuç tablosu (HTML) ---------- */
.tablo-kap { max-height: 600px; overflow: auto; border: 3px solid #4B5563; border-radius: 14px; background: #fff; }
table.tbl { border-collapse: collapse; width: 100%; font-size: 15px; }
table.tbl th { position: sticky; top: 0; z-index: 1; background: #0A60D6; color: #fff; text-align: left;
               padding: 13px 14px; border: 1px solid #084FAF; font-weight: 800; white-space: nowrap; }
table.tbl td { padding: 12px 14px; border: 1px solid #8D96A5; vertical-align: top; color: #111827; line-height: 1.4; }
table.tbl tr:nth-child(even) td { background: #F0F5FF; }
table.tbl td.dar { white-space: nowrap; }
.rozet { display: inline-block; padding: 4px 13px; border-radius: 999px; font-weight: 800; font-size: 13.5px; white-space: nowrap; }
.rozet.dolu { background: #0A60D6; color: #fff; }
.rozet.bos { background: #fff; color: #374151; border: 2px solid #6B7280; }
.rozet.acik { background: #E8F1FF; color: #0A4FAD; border: 2px solid #0A60D6; }

/* ---------- Özet kutuları ---------- */
.stat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin: 8px 0 8px; }
.stat { background: #EAF2FF; border: 3px solid #B9D1F7; border-radius: 18px; padding: 16px 20px; }
.stat .e { font-size: 15px; font-weight: 800; color: #374151; }
.stat .d { font-size: 32px; font-weight: 800; color: #0A60D6; line-height: 1.2; word-break: break-word; }
.stat .a { font-size: 14px; color: #374151; margin-top: 6px; line-height: 1.4; }

/* ---------- Karar kutusu ---------- */
.karar { border-radius: 16px; padding: 18px 22px; border: 3px solid; border-left-width: 12px; }
.karar b { display: block; font-size: 24px; margin-bottom: 4px; }
.karar span { font-size: 16px; line-height: 1.45; }
.k-mavi { background: #E8F1FF; border-color: #0A60D6; color: #0B3A7A; }
.k-sari { background: #FFF4DD; border-color: #D98A00; color: #5C3A00; }
.k-gri { background: #F1F2F4; border-color: #6B7280; color: #1F2937; }
.k-kirmizi { background: #FDECEC; border-color: #C62828; color: #701313; }

/* ---------- Kaynakça kaydı kartı ve bilgi kutuları ---------- */
.kayit { border: 3px solid #8D96A5; border-radius: 14px; padding: 14px 18px; margin: 10px 0; background: #fff; }
.kayit .ust { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-bottom: 8px; font-weight: 800; }
.kayit .metin { font-size: 15.5px; line-height: 1.55; color: #111827; }
.atif-satir { border-left: 8px solid #0A60D6; background: #F0F5FF; border-radius: 10px; padding: 10px 16px; margin: 8px 0; font-size: 15.5px; }
.bilgi { border: 3px solid #C3C9D4; background: #F7F8FB; border-radius: 14px; padding: 12px 16px; font-size: 15.5px; line-height: 1.5; color: #111827; }
.bilgi b { color: #0A60D6; }
.adim { display: flex; gap: 12px; align-items: flex-start; margin: 10px 0; font-size: 16.5px; color: #111827; }
.adim .n { background: #0A60D6; color: #fff; width: 30px; height: 30px; border-radius: 50%; display: inline-flex;
           align-items: center; justify-content: center; font-weight: 800; flex: none; }
</style>
""",
    unsafe_allow_html=True,
)


def baslik(numara, metin, aciklama=""):
    st.markdown(f'<div class="sec"><span class="num">{numara}</span>{metin}</div>', unsafe_allow_html=True)
    if aciklama:
        st.markdown(f'<div class="secalt">{aciklama}</div>', unsafe_allow_html=True)


def bolum(ad, aciklama=""):
    alt = f"<span>{aciklama}</span>" if aciklama else ""
    st.markdown(f'<div class="bolum"><b>{ad}</b>{alt}</div>', unsafe_allow_html=True)


def adimlar(liste):
    st.markdown(
        "".join(f'<div class="adim"><span class="n">{i}</span><span>{m}</span></div>' for i, m in enumerate(liste, 1)),
        unsafe_allow_html=True,
    )


def e(metin):
    return html.escape(str(metin if metin is not None else ""))


def guvenli_url(url):
    return url if isinstance(url, str) and url.startswith(("http://", "https://")) else ""


def guvenli_tablo(fonksiyon, *args, **kwargs):
    """row_height gibi yeni parametreleri bilmeyen eski Streamlit sürümlerinde de çalışsın."""
    try:
        return fonksiyon(*args, **kwargs)
    except TypeError:
        kwargs.pop("row_height", None)
        return fonksiyon(*args, **kwargs)


def atif_tablosu_html(kayitlar):
    """Atıf sonuçlarını belirgin çizgili, satır sarmalı, tıklanabilir bağlantılı tablo olarak çizer."""
    satirlar = []
    for a in kayitlar:
        doi = guvenli_url(doi_link(a["doi"]))
        doi_hucre = f'<a href="{e(doi)}" target="_blank" rel="noopener">{e(doi.replace("https://doi.org/", ""))}</a>' if doi else "—"
        kanit = guvenli_url(a["kanit_url"])
        kanit_hucre = f'<a href="{e(kanit)}" target="_blank" rel="noopener">Kaynağı aç</a>' if kanit else "—"
        dogrulandi = a["durum"] == "Doğrulandı"
        rozet = f'<span class="rozet {"dolu" if dogrulandi else "bos"}">{e(a["durum"])}</span>'
        yil = yil_int(a["yil"])
        satirlar.append(
            "<tr>"
            f'<td>{e(a["atif_yapan_eser"])}</td>'
            f'<td class="dar">{e(yil) if yil else "—"}</td>'
            f'<td class="dar">{e(a["atif_yapan_tur"])}</td>'
            f'<td class="dar">{doi_hucre}</td>'
            f'<td class="dar">{kanit_hucre}</td>'
            f'<td class="dar">{rozet}</td>'
            f'<td>{e(a["atif_alan_yayin"])}</td>'
            f'<td class="dar">{e(a["oz_atif"])}</td>'
            "</tr>"
        )
    baslik_satiri = "".join(
        f"<th>{h}</th>" for h in ("Atıf yapan eser", "Yıl", "Tür", "DOI", "Kanıt", "Durum", "Atıf alan eser", "Öz-atıf")
    )
    return f'<div class="tablo-kap"><table class="tbl"><thead><tr>{baslik_satiri}</tr></thead><tbody>{"".join(satirlar)}</tbody></table></div>'


def stat_kutulari(liste):
    """liste: [(etiket, değer, açıklama)] — metin kesilmez, gerekirse alt satıra iner."""
    kutular = "".join(
        f'<div class="stat"><div class="e">{e(et)}</div><div class="d">{e(d)}</div>'
        + (f'<div class="a">{e(a)}</div>' if a else "")
        + "</div>"
        for et, d, a in liste
    )
    st.markdown(f'<div class="stat-grid">{kutular}</div>', unsafe_allow_html=True)


# ==================================================
# VERİ
# ==================================================

try:
    yayinlar = yayinlari_yukle()
    atiflar = atiflari_yukle()
except FileNotFoundError:
    st.error("Veri dosyası bulunamadı: veri/arayuz_verisi.json. Dosyanın 'veri' klasöründe olduğundan emin olun.")
    st.stop()
except ValueError:
    st.error("veri/arayuz_verisi.json okunamadı (dosya bozuk veya eksik). Emine'den güncel dosyayı isteyin.")
    st.stop()
except Exception as hata:
    st.error(f"Veri yüklenirken beklenmeyen bir hata oluştu: {hata}")
    st.stop()

if not yayinlar:
    st.warning("Veri dosyasında yayın bulunamadı.")
    st.stop()

st.title("AtıfBul")
st.caption("Akademik atıfları kanıtıyla birlikte bulun")

if "sayfa" not in st.session_state:
    st.session_state.sayfa = "Atıf Analizi"

with st.container(key="sayfa_menu"):
    m1, m2, m3 = st.columns([2, 2, 6])
    if m1.button("Atıf Analizi", type="primary" if st.session_state.sayfa == "Atıf Analizi" else "secondary", width="stretch", key="menu_atif"):
        st.session_state.sayfa = "Atıf Analizi"
        st.rerun()
    if m2.button("PDF Analizi", type="primary" if st.session_state.sayfa == "PDF Analizi" else "secondary", width="stretch", key="menu_pdf"):
        st.session_state.sayfa = "PDF Analizi"
        st.rerun()

sayfa = st.session_state.sayfa
st.write("")

# ==================================================
# SEKME 1: ATIF ANALİZİ
# ==================================================

if sayfa == "Atıf Analizi":

    # ---------- 1) Akademisyen (tam genişlik) ----------
    with st.container(key="kart_kisi"):
        baslik(1, "Akademisyeni bulun", "Adı ve kurumu yazın, ardından 'Akademisyeni ara' düğmesine basın.")

        k1, k2, k3 = st.columns([4, 4, 2], vertical_alignment="bottom")
        ad = k1.text_input("Akademisyen adı", value="Remzi Başar", placeholder="Örn. Remzi Başar")
        kurum = k2.selectbox("Kurum", ["Tüm kurumlar", "Düzce Üniversitesi"])
        if k3.button("Akademisyeni ara", type="primary", width="stretch"):
            st.session_state.adaylar = akademisyen_bul(ad, kurum)
            st.session_state.pop("arama", None)

        adaylar = st.session_state.get("adaylar")
        secilen_kisi = None

        if adaylar is None:
            st.caption("Henüz arama yapılmadı.")
        elif not adaylar:
            st.warning("Bu sürümde veri yalnızca Remzi Başar için hazır. Adı veya kurumu değiştirin.")
        else:
            secim = st.radio(
                "Doğru kişiyi seçin",
                options=list(range(len(adaylar))),
                format_func=lambda i: f"{adaylar[i]['ad']} · {adaylar[i]['kurum']} · {len(yayinlar)} yayın",
                horizontal=True,
            )
            secilen_kisi = adaylar[secim]

    st.write("")
    sol, sag = st.columns([5, 6], gap="large")

    # ---------- 2) Tür, eser ve yıl seçimi ----------
    secili_idler = set()
    adaylar_atif, ymin, ymax = [], None, None
    bas_yil, bit_yil, oz_gizle = 0, 9999, False
    bul = False

    with sol:
        with st.container(key="kart_eser"):
            baslik(2, "Eseri ve yılı seçin", "Eser türünü seçin, tablodan eser işaretleyin, yıl aralığını belirleyin.")

            if not secilen_kisi:
                st.markdown('<div class="bilgi">Önce yukarıdan akademisyeni arayıp seçin. Eser listesi burada görünecek.</div>', unsafe_allow_html=True)
            else:
                bolum("Eser türü", "İstediğiniz türleri işaretleyin; liste buna göre daralır.")
                kutular = st.columns(4)
                secili_turler = [
                    t for t, k in zip(TUR_GRUPLARI, kutular)
                    if k.checkbox(t, value=(t != "Diğer"), key=f"tur_{t}")
                ]
                liste = [y for y in yayinlar if tur_grubu(y["tur"]) in secili_turler]

                if not liste:
                    st.info("Seçilen türlerde eser yok. Bir tür daha işaretleyin.")
                else:
                    bolum("Eser listesi", f"{len(liste)} eser listelendi. Atıflarını görmek istediklerinizin 'Seç' kutusunu işaretleyin.")
                    tumu = st.checkbox("Tümünü seç")

                    tablo = pd.DataFrame([
                        {"Seç": tumu, "Başlık": y["baslik"], "Tür": y["tur"], "Yıl": yil_int(y["yil"])}
                        for y in liste
                    ])
                    duzenlenen = guvenli_tablo(
                        st.data_editor,
                        tablo,
                        hide_index=True,
                        disabled=["Başlık", "Tür", "Yıl"],
                        height=430,
                        row_height=42,
                        key=f"eser_tablosu_{tumu}_{'-'.join(secili_turler)}",
                        column_config={
                            "Seç": st.column_config.CheckboxColumn("Seç", width="small"),
                            "Başlık": st.column_config.TextColumn("Başlık", width="large"),
                            "Tür": st.column_config.TextColumn("Tür", width="small"),
                            "Yıl": st.column_config.NumberColumn("Yıl", format="%d", width="small"),
                        },
                    )
                    secili_idler = {liste[i]["id"] for i in duzenlenen.index[duzenlenen["Seç"]]}
                    st.markdown(f"**Seçili eser:** {len(secili_idler)} / {len(liste)}")

                    bolum("Atıf yılı aralığı", "Atıf yapan eserlerin yayın yılı. Seçtiğiniz eserlere göre otomatik belirlenir.")
                    if not secili_idler:
                        st.caption("Önce yukarıdaki tablodan en az bir eser işaretleyin.")
                    else:
                        adaylar_atif = [a for a in atiflar if a["atif_alan_yayin_id"] in secili_idler]
                        ymin, ymax = yil_araligi(adaylar_atif)
                        if not adaylar_atif:
                            st.caption("Seçilen eserlere yapılmış atıf yok.")
                        elif ymin is None:
                            st.caption("Atıfların yılı bilinmiyor; yıl filtresi uygulanmayacak.")
                        else:
                            y1, y2 = st.columns(2)
                            bas_yil = y1.number_input(
                                "Başlangıç yılı", min_value=ymin, max_value=ymax, value=ymin,
                                step=1, format="%d", key=f"ybas_{ymin}_{ymax}",
                            )
                            bit_yil = y2.number_input(
                                "Bitiş yılı", min_value=ymin, max_value=ymax, value=ymax,
                                step=1, format="%d", key=f"ybit_{ymin}_{ymax}",
                            )
                            if bit_yil < bas_yil:
                                st.warning("Bitiş yılı, başlangıç yılından küçük olamaz.")
                        oz_gizle = st.checkbox("Öz-atıfları gizle", help="Hocanın kendi eserine yaptığı atıflar")

                    st.write("")
                    bul = st.button(
                        "Atıfları bul", type="primary", width="stretch",
                        disabled=(not secili_idler) or (ymin is not None and bit_yil < bas_yil),
                    )
                    if bul:
                        st.session_state.arama = {
                            "idler": sorted(secili_idler),
                            "bas": int(bas_yil), "bit": int(bit_yil), "oz": bool(oz_gizle),
                        }

    # ---------- 3) Atıflar ----------
    with sag:
        with st.container(key="kart_sonuc"):
            baslik(3, "Atıflar", "Soldaki seçimlere göre bulunan atıflar burada listelenir.")
            arama = st.session_state.get("arama")

            if not secilen_kisi or arama is None:
                st.markdown('<div class="bolum"><b>Nasıl kullanılır?</b></div>', unsafe_allow_html=True)
                adimlar([
                    "Akademisyenin adını yazıp <b>Akademisyeni ara</b>'ya basın.",
                    "Eser türünü seçin ve tablodan bir ya da birkaç <b>eser işaretleyin</b>.",
                    "İsterseniz <b>atıf yılı aralığını</b> ve öz-atıf seçeneğini ayarlayın.",
                    "<b>Atıfları bul</b> düğmesine basın. Sonuçlar bu alanda görünür.",
                ])
                st.markdown(
                    '<div class="bilgi"><b>İpucu:</b> Sonuç tablosundaki DOI ve "Kaynağı aç" bağlantılarına tıklayarak '
                    "atıfın kaynağını doğrudan açabilirsiniz.</div>",
                    unsafe_allow_html=True,
                )
            else:
                guncel = {"idler": sorted(secili_idler), "bas": int(bas_yil), "bit": int(bit_yil), "oz": bool(oz_gizle)}
                if secili_idler and guncel != arama:
                    st.warning("Seçimi veya yılları değiştirdiniz. Güncel sonuç için soldaki **Atıfları bul** düğmesine tekrar basın.")

                idler = set(arama["idler"])
                gosterilen = atiflari_filtrele(atiflar, idler, arama["bas"], arama["bit"], arama["oz"])
                yil_metni = "tüm yıllar" if arama["bit"] == 9999 else f"{arama['bas']}–{arama['bit']}"
                bolum("Özet", f"{len(idler)} eser · {yil_metni}" + (" · öz-atıflar gizli" if arama["oz"] else ""))
                stat_kutulari([
                    ("Bulunan atıf", len(gosterilen), "Seçime uyan toplam atıf"),
                    ("Doğrulandı", sum(a["durum"] == "Doğrulandı" for a in gosterilen), "Kaynakça kanıtıyla kontrol edildi"),
                    ("İncelenmeli", sum(a["durum"] == "İncelenmeli" for a in gosterilen), "Yalnızca OpenAlex ilişkisi var"),
                ])

                bolum("Atıf tablosu", "Satırlar sarılır, yazılar kesilmez. DOI ve Kanıt sütunlarındaki bağlantılar yeni sekmede açılır.")
                if not gosterilen:
                    st.info("Bu seçimde atıf yok. Yıl aralığını genişletin ya da başka eser seçin.")
                else:
                    st.markdown(atif_tablosu_html(gosterilen), unsafe_allow_html=True)

                    sonuc = pd.DataFrame([
                        {
                            "Atıf yapan eser": a["atif_yapan_eser"], "Tür": a["atif_yapan_tur"],
                            "Yıl": yil_int(a["yil"]), "Atıf alan eser": a["atif_alan_yayin"],
                            "DOI": doi_link(a["doi"]), "Kanıt": a["kanit_url"] or "",
                            "Durum": a["durum"], "Öz-atıf": a["oz_atif"],
                        }
                        for a in gosterilen
                    ])
                    st.write("")
                    st.download_button(
                        "CSV indir", sonuc.to_csv(index=False).encode("utf-8-sig"),
                        file_name="atifbul_sonuclari.csv", mime="text/csv",
                    )

# ==================================================
# SEKME 2: PDF ANALİZİ
# ==================================================

ETIKET_SINIFI = {"Güçlü": "dolu", "Olası": "acik"}
KARAR_SINIFI = {"basari": "k-mavi", "uyari": "k-sari", "bilgi": "k-gri", "hata": "k-kirmizi"}

KAYNAKCA_METNI = {
    "eslesti": ("Var", "Hedef eser, belgenin kaynakça bölümünde tek bir kayıtla eşleşti."),
    "incelenmeli": ("İncele", "Olası bir kayıt ya da birden fazla aday var. Aşağıdaki kayıtları elle kontrol edin."),
    "eslesmedi": ("Yok", "Kaynakça kayıtlarında hedef eser bulunamadı."),
}
METIN_ICI_METNI = {
    "bulundu": ("Var", "Metnin içinde hedef esere ait bir atıf (Yazar, Yıl) bulundu."),
    "incelenmeli": ("İncele", "Metinde olası bir atıf var ama kesin değil."),
    "bulunamadi": ("Yok", "Metin içinde hedef esere atıf bulunamadı."),
}

if sayfa == "PDF Analizi":
    sol2, sag2 = st.columns([4, 6], gap="large")

    # ---------- 1) Hedef eser ve PDF ----------
    with sol2:
        with st.container(key="kart_pdf1"):
            baslik(1, "Hedef eseri ve PDF'i seçin", "Önce atıf aranacak eseri, sonra o eseri anan belgeyi seçin.")

            bolum("A. Hedef eser", "Hocanın hangi yayınına atıf arandığını seçin.")
            indeks = next(
                (i for i, y in enumerate(yayinlar)
                 if "KURUMSAL KAYNAK PLANLAMASI" in y["baslik"].upper() and "VIKOR" in y["baslik"].upper()), 0)
            sec = st.selectbox(
                "Hedef eser", options=list(range(len(yayinlar))), index=indeks,
                format_func=lambda i: f"{yayinlar[i]['baslik'][:70]} ({yil_int(yayinlar[i]['yil']) or '?'})",
                label_visibility="collapsed",
            )
            hedef_y = yayinlar[sec]
            st.markdown(
                f'<div class="bilgi"><b>Seçilen eser:</b> {e(hedef_y["baslik"])} ({e(yil_int(hedef_y["yil"]) or "yıl bilinmiyor")})</div>',
                unsafe_allow_html=True,
            )

            bolum("B. Yazarlar", "Kaynakçadaki yazarlarla karşılaştırılır. Metin içi atıf araması için tam 2 yazar gerekir.")
            yazar_metni = st.text_input(
                "Yazarlar (virgülle ayırın)", value=", ".join(hedef_y["yazarlar"]),
                key=f"yazar_{sec}", label_visibility="collapsed",
            )
            yazarlar = [a.strip() for a in yazar_metni.split(",") if a.strip()]
            if len(yazarlar) != 2:
                st.info("Bu eserde 2 yazar yok. Kaynakça eşleşmesi yapılır, metin içi atıf araması yapılamaz.")

            bolum("C. PDF dosyası", "Makale, tez veya bildiri PDF'i. Metni seçilebilen (taranmamış) bir PDF olmalı.")
            yuklenen = st.file_uploader("PDF dosyası", type=["pdf"], label_visibility="collapsed")
            if yuklenen is not None:
                st.markdown(
                    f'<div class="bilgi"><b>Yüklenen dosya:</b> {e(yuklenen.name)} ({yuklenen.size / 1_000_000:.1f} MB)</div>',
                    unsafe_allow_html=True,
                )

            st.write("")
            calistir = st.button("PDF'i analiz et", type="primary", width="stretch", disabled=yuklenen is None)

            if calistir and yuklenen is not None:
                hedef = hedef_eser_hazirla(hedef_y["baslik"], yazarlar, yil_int(hedef_y["yil"]), hedef_y["doi"])
                try:
                    with st.spinner("PDF okunuyor, büyük tezlerde bir iki dakika sürebilir..."):
                        st.session_state.pdf_rapor = pdf_kontrol_et(yuklenen.getvalue(), hedef)
                        st.session_state.pdf_ad = yuklenen.name
                except ModuleNotFoundError:
                    st.session_state.pdf_rapor = None
                    st.error("PDF okuyucu kurulu değil. Terminalde şunu çalıştırın: python -m pip install pymupdf")
                except Exception as hata:
                    st.session_state.pdf_rapor = None
                    st.error(f"PDF işlenemedi: {hata}")

    # ---------- 2) Sonuç ve kanıt ----------
    with sag2:
        with st.container(key="kart_pdf2"):
            baslik(2, "Sonuç ve kanıt", "Analiz bittiğinde karar, özet ve kanıtlar bölüm bölüm burada görünür.")
            rapor = st.session_state.get("pdf_rapor")

            if not rapor:
                st.markdown('<div class="bolum"><b>Nasıl kullanılır?</b></div>', unsafe_allow_html=True)
                adimlar([
                    "Soldan <b>hedef eseri</b> seçin ve yazarları kontrol edin.",
                    "<b>PDF dosyasını</b> yükleyin.",
                    "<b>PDF'i analiz et</b> düğmesine basın.",
                ])
                st.markdown(
                    '<div class="bilgi"><b>Sonuç şu bölümlerden oluşur:</b> Karar, Özet (kaynakçada ve metin içinde bulundu mu), '
                    "Metin içi atıf, Kaynakça kaydı ve Ayrıntılı rapor.</div>",
                    unsafe_allow_html=True,
                )
            else:
                tur, ana, aciklama = ozet(rapor)
                st.markdown(f'<div class="bilgi"><b>İncelenen belge:</b> {e(st.session_state.get("pdf_ad", ""))}</div>', unsafe_allow_html=True)

                bolum("1. Karar", "Sistemin bu belge için verdiği genel sonuç.")
                st.markdown(f'<div class="karar {KARAR_SINIFI[tur]}"><b>{e(ana)}</b><span>{e(aciklama)}</span></div>', unsafe_allow_html=True)

                bolum("2. Özet", "Hedef eser belgenin neresinde bulundu?")
                kay = KAYNAKCA_METNI.get(rapor["hedef_eser_kimligi_sonucu"]["durum"], ("Belirsiz", "Kaynakça güvenilir biçimde okunamadı."))
                met = METIN_ICI_METNI.get(rapor["hedef_metin_ici_atif_sonucu"]["durum"], ("Belirsiz", "Metin içi atıf araması yapılamadı (örneğin hedefin 2 yazarı yoktur)."))
                stat_kutulari([
                    ("Kaynakçada", kay[0], kay[1]),
                    ("Metin içinde", met[0], met[1]),
                    ("Sayfa sayısı", rapor["pdf_sayfa_sayisi"] or "-", "İncelenen belgenin toplam PDF sayfası."),
                ])

                bolum("3. Metin içi atıf", "Belgenin ana metninde hedef esere yapılan atıf. Sayfa numarası PDF sırasına göredir.")
                gorulen, atif_satirlari = set(), []
                for ad_ in rapor["hedef_metin_ici_atif_sonucu"].get("adaylar", []) + [
                        b for b in rapor["hedef_baglanti_sonucu"].get("baglantilar", [])]:
                    metin_ = ad_.get("ham_atif_metni")
                    sayfa_ = ad_.get("pdf_sayfa")
                    if metin_ and (sayfa_, metin_) not in gorulen:
                        gorulen.add((sayfa_, metin_))
                        atif_satirlari.append(f'<div class="atif-satir"><b>PDF sayfa {e(sayfa_)}:</b> {e(metin_)}</div>')
                if atif_satirlari:
                    st.markdown("".join(atif_satirlari), unsafe_allow_html=True)
                else:
                    st.markdown('<div class="bilgi">Metin içinde hedef esere ait atıf bulunamadı.</div>', unsafe_allow_html=True)

                bolum("4. Kaynakça kaydı", "Belgenin kaynakça bölümünde bulunan aday kayıtlar. En güçlü eşleşme en üstte.")
                kayitlar = kaynakca_kaydi_metni(rapor)
                if kayitlar:
                    st.markdown(
                        "".join(
                            f'<div class="kayit"><div class="ust"><span>Kayıt {e(kid)} · PDF sayfa {e(sayfa)}</span>'
                            f'<span class="rozet {ETIKET_SINIFI.get(etiket.split()[0], "bos")}">{e(etiket.split(":")[0])}</span></div>'
                            f'<div class="metin">{e(metin)}</div>'
                            f'<div style="margin-top:6px;font-size:14px;color:#4B5563">{e(etiket.split(":", 1)[1].strip() if ":" in etiket else "")}</div></div>'
                            for kid, sayfa, metin, etiket in kayitlar
                        ),
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown('<div class="bilgi">Kaynakçada hedef esere benzeyen bir kayıt bulunamadı.</div>', unsafe_allow_html=True)

                if rapor["bibliyografik_farkliliklar"]:
                    st.info(f"Künye farkı: {len(rapor['bibliyografik_farkliliklar'])} noktada fark var (ayrıntılı raporda).")

                bolum("5. Ayrıntılı rapor", "Aşamalar, boş sayfalar ve elle incelenecek noktalar. Raporlama ve hata arama için.")
                with st.expander("Ayrıntılı raporu göster"):
                    st.text_area(
                        "Rapor", value=kanit_raporunu_metinlestir(rapor), height=360,
                        disabled=True, label_visibility="collapsed",
                    )
                st.caption("PDF sayfa numarası, belgenin üzerindeki basılı sayfa numarasından farklı olabilir.")