import html
from datetime import date

import pandas as pd
import streamlit as st

from moduller.pdf_analiz import hedef_eser_hazirla, pdf_kontrol_et, ozet, sonuc_satirlari, kaynakca_kaydi_metni, kanit_raporunu_metinlestir
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

st.set_page_config(page_title="AtıfBul", page_icon="🔷", layout="wide", initial_sidebar_state="expanded")

# ==================================================
# TASARIM: iOS tarzı — gölgeli yuvarlak kartlar, degrade başlık, segment menü, belirgin düğmeler, ekrana uyumlu boyut
# ==================================================

st.markdown(
    """
<style>
:root { --mavi: #3B7DC4; --mavi-koyu: #1F4E8C; --mavi-acik: #E6F1FC; --yesil: #248A3D; --yesil-acik: #E4F7E9;
        --turuncu: #B25E00; --turuncu-acik: #FFF1DB; --kirmizi: #D70015; --kirmizi-acik: #FFE8EA;
        --yazi: #1C1C1E; --yazi2: #52525B; --ayrac: #E5E5EA; --golge: 0 2px 4px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.08); }
.stApp { background: #F2F2F7; color: var(--yazi);
         font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
.block-container { max-width: min(1480px, 94vw); padding: 1.4rem 0 3rem; margin: 0 auto; }
header[data-testid="stHeader"] { display: none; }
html { font-size: clamp(14px, 0.25vw + 12.6px, 18px); }

[data-testid="stCaptionContainer"] p { font-size: 0.95rem; color: var(--yazi2); }
[data-testid="stWidgetLabel"] p { font-size: 1rem; font-weight: 700; color: var(--yazi); }

/* ---------- Üst şerit ---------- */
.ust-serit { display: flex; align-items: center; gap: 1.1rem; padding: 1.1rem 1.6rem; margin-bottom: 1rem; border-radius: 28px;
             background: linear-gradient(135deg, #3B7DC4 0%, #6FA8DC 100%); box-shadow: 0 10px 28px rgba(59,125,196,0.35); }
.ust-serit .logo { width: 3.5rem; height: 3.5rem; border-radius: 18px; background: rgba(255,255,255,0.22); color: #fff; flex: none;
                   display: flex; align-items: center; justify-content: center; font: 700 2.6rem/1 Georgia, serif; padding-top: 0.6rem;
                   box-shadow: inset 0 0 0 1.5px rgba(255,255,255,0.45); }
.ust-serit .ad { font-size: 1.9rem; font-weight: 800; color: #fff; line-height: 1.1; letter-spacing: -0.02em; }
.ust-serit .slogan { font-size: 1rem; color: rgba(255,255,255,0.9); margin-top: 3px; font-weight: 500; }

/* ---------- Sayfa menüsü (iOS segment) ---------- */
.st-key-sayfa_menu [data-testid="stHorizontalBlock"] { background: #E3EAF3; border-radius: 18px; padding: 5px; gap: 5px; }
.st-key-sayfa_menu button { min-height: 52px !important; border-radius: 14px !important; border: 0 !important; white-space: nowrap !important; padding: 0 18px !important; }
.st-key-sayfa_menu button p { font-size: 1.1rem !important; font-weight: 700 !important; white-space: nowrap !important; overflow: visible !important; }
.st-key-sayfa_menu button[data-testid="stBaseButton-secondary"] { background: transparent !important; color: #3A3A3C !important; box-shadow: none !important; }
.st-key-sayfa_menu button[data-testid="stBaseButton-primary"] { background: #FFFFFF !important; color: var(--mavi) !important; box-shadow: 0 2px 10px rgba(0,0,0,0.16) !important; }
.st-key-sayfa_menu { margin-bottom: 8px; }

/* ---------- Kartlar ---------- */
[class*="st-key-kart"] { background: #FFFFFF; border-radius: 28px; padding: 28px 30px; box-shadow: var(--golge); }
.st-key-kart_eser, .st-key-kart_sonuc, .st-key-kart_pdf1, .st-key-kart_pdf2 { min-height: clamp(480px, 66vh, 780px); }
.sec { display: flex; align-items: center; gap: 14px; font-size: 1.55rem; font-weight: 800; color: var(--yazi); letter-spacing: -0.015em; }
.num { width: 38px; height: 38px; border-radius: 50%; background: var(--mavi); color: #fff; box-shadow: 0 3px 8px rgba(59,125,196,0.4);
       display: inline-flex; align-items: center; justify-content: center; font-size: 1.15rem; font-weight: 800; flex: none; }
.secalt { font-size: 0.97rem; color: var(--yazi2); margin: 4px 0 16px 52px; }

.bolum { margin: 22px 0 8px; padding-top: 16px; border-top: 1px solid var(--ayrac); }
.bolum b { display: block; font-size: 1.15rem; color: var(--yazi); font-weight: 700; }
.bolum span { display: block; font-size: 0.93rem; color: var(--yazi2); margin-top: 2px; }

/* ---------- Girdi alanları ---------- */
div[data-baseweb="input"], div[data-baseweb="select"] > div {
    border: 1.5px solid #C7C7CC !important; border-radius: 14px !important; background: #FFFFFF !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
div[data-baseweb="input"]:focus-within, div[data-baseweb="select"] > div:focus-within { border-color: var(--mavi) !important; box-shadow: 0 0 0 4px rgba(59,125,196,0.18); }
div[data-baseweb="input"] input { font-size: 1rem; }

/* ---------- Düğmeler ---------- */
button { transition: transform .12s ease, box-shadow .15s ease, background .15s ease; }
button:active { transform: scale(0.97); }
button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(180deg, #6FA8DC 0%, #3B7DC4 100%); color: #FFFFFF; border: 0; border-radius: 16px;
    min-height: 56px; font-weight: 700; box-shadow: 0 6px 16px rgba(59,125,196,0.38);
}
button[data-testid="stBaseButton-primary"]:hover { background: linear-gradient(180deg, #5B9BD5 0%, #1F4E8C 100%); box-shadow: 0 8px 20px rgba(59,125,196,0.45); }
button[data-testid="stBaseButton-primary"] p { font-size: 1.12rem; font-weight: 700; }
button[data-testid="stBaseButton-secondary"], .stDownloadButton button {
    background: var(--mavi-acik); color: var(--mavi-koyu); border: 0; border-radius: 16px;
    min-height: 50px; font-weight: 700; box-shadow: 0 3px 10px rgba(0,0,0,0.10);
}
button[data-testid="stBaseButton-secondary"]:hover, .stDownloadButton button:hover { background: #D6E6F7; color: var(--mavi-koyu); }
.stApp a { color: var(--mavi-koyu); font-weight: 700; text-decoration: none; }
.stApp a:hover { text-decoration: underline; }

/* ---------- Eser tablosu ---------- */
[data-testid="stDataFrame"], [data-testid="stDataEditor"] { border-radius: 18px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.10); }

/* ---------- Atıf sonuç tablosu ---------- */
.tablo-kap { max-height: clamp(340px, 52vh, 640px); overflow: auto; border-radius: 20px; background: #fff; box-shadow: 0 2px 10px rgba(0,0,0,0.10); }
table.tbl { border-collapse: separate; border-spacing: 0; width: 100%; font-size: 0.95rem; }
table.tbl th { position: sticky; top: 0; z-index: 1; background: #F2F2F7; color: #3A3A3C; text-align: left;
               padding: 14px 16px; border-bottom: 1px solid var(--ayrac); font-weight: 700; font-size: 0.88rem; white-space: nowrap; }
table.tbl td { padding: 14px 16px; border-bottom: 1px solid #EFEFF4; vertical-align: top; color: var(--yazi); line-height: 1.45; }
table.tbl tr:last-child td { border-bottom: 0; }
table.tbl tbody tr:hover td { background: #F4F9FE; }
table.tbl td.dar { white-space: nowrap; }
table.tbl td.ilk { font-weight: 700; }
.rozet { display: inline-flex; align-items: center; gap: 5px; padding: 5px 13px; border-radius: 999px; font-weight: 700; font-size: 0.84rem; white-space: nowrap; }
.rozet.ok { background: var(--yesil-acik); color: var(--yesil); }
.rozet.inc { background: var(--turuncu-acik); color: var(--turuncu); }
.rozet.dolu { background: var(--yesil-acik); color: var(--yesil); }
.rozet.bos { background: #EFEFF4; color: #3A3A3C; }
.rozet.acik { background: var(--mavi-acik); color: var(--mavi-koyu); }
.tik { color: #28A745; font-weight: 800; }
.tik.sari { color: #FF9500; }
.tik.kirmizi { color: #FF3B30; }

/* ---------- Özet kutuları ---------- */
.stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; margin: 8px 0 8px; }
.stat { background: #EEF5FD; border-radius: 22px; padding: 16px 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.07); }
.stat.yesil { background: var(--yesil-acik); }
.stat.yesil .d { color: var(--yesil); }
.stat.sari { background: var(--turuncu-acik); }
.stat.sari .d { color: var(--turuncu); }
.stat .e { font-size: 0.93rem; font-weight: 700; color: #3A3A3C; }
.stat .d { font-size: 2rem; font-weight: 800; color: var(--mavi-koyu); line-height: 1.2; word-break: break-word; letter-spacing: -0.02em; }
.stat .a { font-size: 0.9rem; color: var(--yazi2); margin-top: 6px; line-height: 1.4; }

/* ---------- Yıllara göre dağılım ---------- */
.yil-grafik { border-radius: 20px; padding: 0.8rem 1.1rem; background: #fff; box-shadow: 0 2px 10px rgba(0,0,0,0.10); }
.yil-satir { display: grid; grid-template-columns: 3.6rem 1fr 2.4rem; gap: 0.8rem; align-items: center; margin: 0.45rem 0; }
.yil-ad { font-weight: 700; color: var(--yazi); }
.yil-cubuk { background: #E3EDF8; height: 1rem; border-radius: 0.5rem; overflow: hidden; display: block; }
.yil-cubuk i { display: block; height: 100%; background: linear-gradient(90deg, #A9CCF0, #3B7DC4); border-radius: 0.5rem; }
.yil-say { text-align: right; font-weight: 700; color: var(--mavi-koyu); }

/* ---------- Sonuç kutusu ---------- */
.karar { border-radius: 22px; padding: 18px 22px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); }
.karar b { display: block; font-size: 1.4rem; margin-bottom: 4px; }
.karar span { font-size: 1rem; line-height: 1.45; }
.k-mavi { background: #EEF5FD; color: #12355B; }
.k-sari { background: var(--turuncu-acik); color: #5C3A00; }
.k-gri { background: #EFEFF4; color: #1C1C1E; }
.k-kirmizi { background: var(--kirmizi-acik); color: #6B0010; }

/* ---------- Kayıt kartı ve bilgi kutuları ---------- */
.kayit { border-radius: 20px; padding: 14px 18px; margin: 10px 0; background: #fff; box-shadow: 0 2px 10px rgba(0,0,0,0.10); }
.kayit .ust { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-bottom: 8px; font-weight: 700; }
.kayit .metin { font-size: 0.98rem; line-height: 1.55; color: var(--yazi); }
.atif-satir { background: #EEF5FD; border-radius: 16px; padding: 12px 16px; margin: 8px 0; font-size: 0.98rem; box-shadow: 0 2px 8px rgba(0,0,0,0.07); }
.bilgi { background: #F7F7FA; border-radius: 18px; padding: 13px 17px; font-size: 0.98rem; line-height: 1.5; color: var(--yazi); box-shadow: 0 1px 6px rgba(0,0,0,0.07); }
.bilgi b { color: var(--mavi-koyu); }
.adim { display: flex; gap: 12px; align-items: flex-start; margin: 10px 0; font-size: 1.05rem; color: var(--yazi); }
.adim .n { background: var(--mavi); color: #fff; width: 30px; height: 30px; border-radius: 50%; display: inline-flex;
           align-items: center; justify-content: center; font-weight: 800; flex: none; box-shadow: 0 3px 8px rgba(59,125,196,0.35); }


/* ---------- Yan menü (iOS kenar çubuğu) ---------- */
header[data-testid="stHeader"] { display: block !important; background: transparent !important; }
[data-testid="stSidebar"] { background: #FFFFFF; box-shadow: 4px 0 28px rgba(0,0,0,0.08); border: 0; }
[data-testid="stSidebar"] > div:first-child { padding-top: 0.5rem; }
[data-testid="stSidebarContent"] { padding: 0.6rem 0.5rem; }
.marka { display: flex; align-items: center; gap: 0.8rem; padding: 1rem 1.1rem; border-radius: 24px; margin-bottom: 1.2rem;
         background: linear-gradient(135deg, #3B7DC4 0%, #6FA8DC 100%); box-shadow: 0 10px 24px rgba(59,125,196,0.35); }
.marka .logo { width: 2.8rem; height: 2.8rem; border-radius: 15px; background: rgba(255,255,255,0.22); color: #fff; flex: none;
               display: flex; align-items: center; justify-content: center; font: 700 2.1rem/1 Georgia, serif; padding-top: 0.5rem;
               box-shadow: inset 0 0 0 1.5px rgba(255,255,255,0.45); }
.marka .ad { font-size: 1.5rem; font-weight: 800; color: #fff; line-height: 1.1; letter-spacing: -0.02em; }
.marka .slogan { font-size: 0.82rem; color: rgba(255,255,255,0.92); margin-top: 2px; font-weight: 500; }
.menu-etiket { font-size: 0.8rem; font-weight: 700; color: #8E8E93; letter-spacing: 0.06em; margin: 0.4rem 0.4rem 0.5rem; }
.yan-not { font-size: 0.86rem; color: var(--yazi2); background: #F2F2F7; border-radius: 18px; padding: 12px 14px; margin-top: 1.4rem; line-height: 1.5; }
.st-key-sayfa_menu { margin-bottom: 8px; }
.st-key-sayfa_menu [data-testid="stVerticalBlock"] { gap: 0.6rem; }
.st-key-sayfa_menu button { min-height: 58px !important; border-radius: 18px !important; border: 0 !important; justify-content: flex-start !important; padding: 0 20px !important; }
.st-key-sayfa_menu button p { font-size: 1.12rem !important; font-weight: 700 !important; white-space: nowrap !important; }
.st-key-sayfa_menu button[data-testid="stBaseButton-secondary"] { background: #FFFFFF !important; color: #3F3A52 !important; box-shadow: 0 2px 8px rgba(20,40,80,0.10) !important; }
.st-key-sayfa_menu button[data-testid="stBaseButton-secondary"]:hover { background: #EEF5FD !important; color: #1F4E8C !important; }
.st-key-sayfa_menu button[data-testid="stBaseButton-primary"] { background: #E6F1FC !important; color: #1F4E8C !important; box-shadow: inset 6px 0 0 #3B7DC4, 0 2px 8px rgba(20,40,80,0.10) !important; }

/* ---------- Büyük sayfa başlığı ---------- */
.buyuk { margin: 0.2rem 0 1.4rem; }
.buyuk h1 { font-size: clamp(2rem, 2.4vw + 1rem, 3rem); font-weight: 800; letter-spacing: -0.03em; color: #1C1C1E; margin: 0; padding: 0; line-height: 1.1; }
.buyuk p { font-size: 1.1rem; color: #52525B; margin: 0.4rem 0 0; }
.adim-seridi { display: flex; flex-wrap: wrap; gap: 10px; margin: 0.6rem 0 0; }
.adim-seridi span { background: #fff; border-radius: 999px; padding: 6px 14px; font-weight: 700; font-size: 0.9rem; color: #1C1C1E; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.adim-seridi b { color: #3B7DC4; margin-right: 4px; }
[class*="st-key-kart"] { min-height: 0 !important; }
.st-key-kart_pdf1 .bolum { margin-top: 0; padding-top: 0; border-top: 0; }
.st-key-kart_pdf2 { background: transparent !important; box-shadow: none !important; padding: 0 !important; }
.st-key-sonuc_kutu, .st-key-ozet_kutu, .st-key-atif_kutu, .st-key-kayit_kutu, .st-key-ayrinti_kutu { background: #FFFFFF; border-radius: 26px; padding: 22px 24px; box-shadow: var(--golge); height: 100%; }
.st-key-sonuc_kutu .bolum, .st-key-ozet_kutu .bolum, .st-key-atif_kutu .bolum, .st-key-kayit_kutu .bolum, .st-key-ayrinti_kutu .bolum { margin-top: 0; padding-top: 0; border-top: 0; }

/* ---------- PASTEL TEMA (Apple tarzı renkli kartlar) ---------- */
:root { --mavi: #3B7DC4; --mavi-koyu: #1F4E8C; --mavi-acik: #E6F1FC; --yazi: #1D1D1F; --yazi2: #3B3B40;
        --golge: 0 2px 6px rgba(0,0,0,0.05), 0 10px 28px rgba(0,0,0,0.10); }
.stApp { background: #F5F5F7; }
[data-testid="stSidebar"] { background: #FFFFFF; }
[class*="st-key-kart"], .st-key-sonuc_kutu, .st-key-ozet_kutu, .st-key-atif_kutu, .st-key-kayit_kutu, .st-key-ayrinti_kutu { border-radius: 32px !important; box-shadow: var(--golge) !important; }
.st-key-kart_kisi { background: #BFD9F2 !important; }
.st-key-kart_eser { background: #BFD9F2 !important; }
.st-key-kart_sonuc { background: #BFD9F2 !important; }
.st-key-kart_pdf1 { background: #BFD9F2 !important; }
.st-key-kart_pdf_bos { background: #BFD9F2 !important; }
.st-key-sonuc_kutu { background: #BFD9F2 !important; }
.st-key-ozet_kutu { background: #BFD9F2 !important; }
.st-key-atif_kutu { background: #FCE9A8 !important; }
.st-key-kayit_kutu { background: #BFD9F2 !important; }
.st-key-ayrinti_kutu { background: #CFE8D5 !important; }
.sec { color: #1D1D1F; }
.secalt, .bolum span, [data-testid="stCaptionContainer"] p { color: #3B3B40; }
.bolum { border-top: 1.5px solid rgba(0,0,0,0.12); }
.num, .adim .n { background: #1D1D1F; color: #fff; box-shadow: none; }
.stat, .bilgi, .atif-satir { background: rgba(255,255,255,0.78); box-shadow: none; }
.stat.yesil { background: rgba(228,247,233,0.95); }
.stat.sari { background: rgba(255,241,219,0.95); }
.stat .d { color: #1F4E8C; }
.karar { box-shadow: none; }
.k-mavi { background: rgba(255,255,255,0.8); color: #1D1D1F; }
.kayit, .yil-grafik, .tablo-kap { background: #FFFFFF; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
table.tbl th { background: #F5F5F7; }
.yil-cubuk { background: #DDEBF9; }
.yil-cubuk i { background: linear-gradient(90deg, #A9CCF0, #3B7DC4); }
.yil-say { color: #1F4E8C; }
.stApp a { color: #1F4E8C; }
/* Düğmeler */
button[data-testid="stBaseButton-primary"] { background: #3B7DC4; color: #fff; border-radius: 999px; box-shadow: 0 6px 16px rgba(59,125,196,0.35); }
button[data-testid="stBaseButton-primary"]:hover { background: #1F4E8C; }
button[data-testid="stBaseButton-secondary"], .stDownloadButton button { background: #FFFFFF; color: #1D1D1F; border-radius: 999px; box-shadow: 0 3px 10px rgba(0,0,0,0.14); }
button[data-testid="stBaseButton-secondary"]:hover, .stDownloadButton button:hover { background: #EEF5FD; color: #1F4E8C; }
div[data-baseweb="input"]:focus-within, div[data-baseweb="select"] > div:focus-within { border-color: #3B7DC4 !important; box-shadow: 0 0 0 4px rgba(59,125,196,0.18); }
/* Marka ve menü */
.marka { background: linear-gradient(135deg, #BFD9F2 0%, #BFD9F2 100%); box-shadow: 0 8px 22px rgba(0,0,0,0.12); }
.marka .logo { background: #1D1D1F; color: #fff; box-shadow: none; }
.marka .ad { color: #1D1D1F; }
.marka .slogan { color: #3B3B40; }
.menu-etiket { color: #6E6E73; }
.yan-not { background: #F5F5F7; }
.st-key-sayfa_menu button[data-testid="stBaseButton-secondary"] { background: #FFFFFF !important; color: #1D1D1F !important; border-radius: 999px !important; }
.st-key-sayfa_menu button[data-testid="stBaseButton-secondary"]:hover { background: #F5F5F7 !important; color: #1F4E8C !important; }
.st-key-sayfa_menu button[data-testid="stBaseButton-primary"] { background: #BFD9F2 !important; color: #1D1D1F !important; border-radius: 999px !important; box-shadow: 0 4px 12px rgba(0,0,0,0.14) !important; }
.st-key-sayfa_menu button { border-radius: 999px !important; }
/* Büyük başlık */
.buyuk h1 { color: #3B7DC4; }
.buyuk p { color: #6E6E73; font-size: 1.2rem; font-weight: 500; }
.adim-seridi span { box-shadow: none; color: #1D1D1F; }
.adim-seridi span:nth-child(1) { background: #BFD9F2; }
.adim-seridi span:nth-child(2) { background: #BFD9F2; }
.adim-seridi span:nth-child(3) { background: #FCE9A8; }
.adim-seridi b { color: #1D1D1F; }

/* ---------- TEK PASTEL RENK: soft pembe, kartlar beyaz ---------- */
.st-key-kart_kisi, .st-key-kart_eser, .st-key-kart_sonuc, .st-key-kart_pdf1, .st-key-kart_pdf_bos,
.st-key-sonuc_kutu, .st-key-ozet_kutu, .st-key-atif_kutu, .st-key-kayit_kutu, .st-key-ayrinti_kutu { background: #FFFFFF !important; }
.num, .adim .n { background: #3B7DC4; color: #fff; }
.bolum { border-top: 1.5px solid #D6E6F7; }
.stat, .bilgi, .atif-satir, .k-mavi { background: #EEF5FD; }
.stat.yesil { background: #E8F7EC; }
.stat.sari { background: #FFF4DD; }
.marka { background: #CFE3F7; box-shadow: 0 6px 18px rgba(59,125,196,0.15); }
.st-key-sayfa_menu button[data-testid="stBaseButton-primary"] { background: #CFE3F7 !important; color: #1F4E8C !important; }
.adim-seridi span:nth-child(n) { background: #CFE3F7; }
.yan-not { background: #EEF5FD; }
table.tbl th { background: #EEF5FD; }
.yil-cubuk { background: #DDEBF9; }
.yil-cubuk i { background: #3B7DC4; }
.rozet.acik { background: #CFE3F7; color: #1F4E8C; }

/* ---------- PASTEL MAVİ DÜĞMELER ---------- */
button[data-testid="stBaseButton-primary"] { background: #A9CCF0 !important; color: #0F2E52 !important; border-radius: 999px; box-shadow: 0 6px 16px rgba(59,125,196,0.30); }
button[data-testid="stBaseButton-primary"]:hover { background: #8FBDEB !important; }
button[data-testid="stBaseButton-primary"] p { color: #0F2E52 !important; }
.st-key-sayfa_menu button[data-testid="stBaseButton-primary"] { background: #CFE3F7 !important; color: #1F4E8C !important; }
.marka { background: #CFE3F7; }
.buyuk h1 { color: #1F4E8C; }

/* ---------- Küçük ekranlar ---------- */
@media (max-width: 900px) {
  .block-container { max-width: 96vw; padding-top: 0.8rem; }
  [class*="st-key-kart"] { padding: 18px 16px; border-radius: 22px; min-height: 0 !important; }
  .ust-serit { padding: 0.8rem 1rem; border-radius: 22px; }
  .ust-serit .ad { font-size: 1.5rem; }
  .ust-serit .slogan { font-size: 0.88rem; }
  .sec { font-size: 1.3rem; }
  .secalt { margin-left: 0; }
}
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
        rozet = (f'<span class="rozet ok">✔ {e(a["durum"])}</span>' if dogrulandi
                 else f'<span class="rozet inc">● {e(a["durum"])}</span>')
        yil = yil_int(a["yil"])
        satirlar.append(
            "<tr>"
            f'<td class="ilk">{e(a["atif_yapan_eser"])}</td>'
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


def yil_dagilimi_html(kayitlar):
    """Atıf yapan eserlerin yayın yılına göre atıf sayısını yatay çubuklarla gösterir."""
    sayac = {}
    for a in kayitlar:
        y = yil_int(a["yil"])
        sayac[y] = sayac.get(y, 0) + 1
    if not sayac:
        return ""
    enb = max(sayac.values())
    satirlar = []
    for y in sorted(k for k in sayac if k is not None):
        genislik = max(6, round(100 * sayac[y] / enb))
        satirlar.append(
            f'<div class="yil-satir"><span class="yil-ad">{y}</span>'
            f'<span class="yil-cubuk"><i style="width:{genislik}%"></i></span><span class="yil-say">{sayac[y]}</span></div>'
        )
    if None in sayac:
        genislik = max(6, round(100 * sayac[None] / enb))
        satirlar.append(
            f'<div class="yil-satir"><span class="yil-ad">Yıl yok</span>'
            f'<span class="yil-cubuk"><i style="width:{genislik}%"></i></span><span class="yil-say">{sayac[None]}</span></div>'
        )
    return f'<div class="yil-grafik">{"".join(satirlar)}</div>'


def stat_kutulari(liste):
    """liste: [(etiket, değer, açıklama)] — metin kesilmez, gerekirse alt satıra iner."""
    kutular = "".join(
        f'<div class="stat {e(k[0]) if k else ""}"><div class="e">{e(et)}</div><div class="d">{e(d)}</div>'
        + (f'<div class="a">{e(a)}</div>' if a else "")
        + "</div>"
        for et, d, a, *k in liste
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

if "sayfa" not in st.session_state:
    st.session_state.sayfa = "Atıf Analizi"

with st.sidebar:
    st.markdown(
        '<div class="marka"><div class="logo">&ldquo;</div>'
        '<div><div class="ad">AtıfBul</div><div class="slogan">Atıfları kanıtıyla bulun</div></div></div>'
        '<div class="menu-etiket">SAYFALAR</div>',
        unsafe_allow_html=True,
    )
    with st.container(key="sayfa_menu"):
        if st.button("Atıf Analizi", type="primary" if st.session_state.sayfa == "Atıf Analizi" else "secondary", width="stretch", key="menu_atif"):
            st.session_state.sayfa = "Atıf Analizi"
            st.rerun()
        if st.button("PDF Analizi", type="primary" if st.session_state.sayfa == "PDF Analizi" else "secondary", width="stretch", key="menu_pdf"):
            st.session_state.sayfa = "PDF Analizi"
            st.rerun()
    st.markdown(
        '<div class="yan-not"><b>Atıf Analizi:</b> bir akademisyenin eserlerine yapılan atıfları listeler.<br><br>'
        '<b>PDF Analizi:</b> yüklediğiniz belgede hedef eserin kaynakçada ve metinde geçip geçmediğine bakar.</div>',
        unsafe_allow_html=True,
    )

sayfa = st.session_state.sayfa
if sayfa == "Atıf Analizi":
    st.markdown(
        '<div class="buyuk"><h1>Atıf Analizi</h1><p>Akademisyeni bulun, eserleri seçin, atıfları kanıtlarıyla görün.</p>'
        '<div class="adim-seridi"><span><b>1</b>Akademisyen</span><span><b>2</b>Eser ve yıl</span><span><b>3</b>Atıflar</span></div></div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '<div class="buyuk"><h1>PDF Analizi</h1><p>Bir belgede hedef eserin kaynakçada ve metin içinde geçip geçmediğini kontrol edin.</p>'
        '<div class="adim-seridi"><span><b>1</b>Hedef eser</span><span><b>2</b>PDF yükle</span><span><b>3</b>Sonuç</span></div></div>',
        unsafe_allow_html=True,
    )

# Sayfa değişince ekranda olmayan kutuların değerleri Streamlit tarafından silinir.
# Değerleri her çalıştırmada kendilerine yeniden yazarak korunmalarını sağlıyoruz.
_KORUNAN = ("ad_kutu", "kurum_kutu", "kisi_secimi", "tur_", "tumunu_sec", "ybas_", "ybit_", "oz_gizle", "hedef_secim", "yazar_")
for _anahtar in list(st.session_state.keys()):
    if str(_anahtar).startswith(_KORUNAN):
        st.session_state[_anahtar] = st.session_state[_anahtar]

# ==================================================
# SEKME 1: ATIF ANALİZİ
# ==================================================

if sayfa == "Atıf Analizi":

    # ---------- 1) Akademisyen (tam genişlik) ----------
    with st.container(key="kart_kisi"):
        baslik(1, "Akademisyeni bulun", "Adı ve kurumu yazın, ardından 'Akademisyeni ara' düğmesine basın.")

        k1, k2, k3 = st.columns([4, 4, 2], vertical_alignment="bottom")
        st.session_state.setdefault("ad_kutu", "Remzi Başar")
        ad = k1.text_input("Akademisyen adı", placeholder="Örn. Remzi Başar", key="ad_kutu")
        kurum = k2.selectbox("Kurum", ["Tüm kurumlar", "Düzce Üniversitesi"], key="kurum_kutu")
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
            if st.session_state.get("kisi_secimi", 0) >= len(adaylar):
                st.session_state.kisi_secimi = 0
            secim = st.radio(
                "Doğru kişiyi seçin",
                key="kisi_secimi",
                options=list(range(len(adaylar))),
                format_func=lambda i: f"{adaylar[i]['ad']} · {adaylar[i]['kurum']} · {len(yayinlar)} yayın",
                horizontal=True,
            )
            secilen_kisi = adaylar[secim]

    st.write("")
    sol, sag = st.container(), st.container()

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
                for t in TUR_GRUPLARI:
                    st.session_state.setdefault(f"tur_{t}", t != "Diğer")
                secili_turler = [
                    t for t, k in zip(TUR_GRUPLARI, kutular)
                    if k.checkbox(t, key=f"tur_{t}")
                ]
                liste = [y for y in yayinlar if tur_grubu(y["tur"]) in secili_turler]

                if not liste:
                    st.info("Seçilen türlerde eser yok. Bir tür daha işaretleyin.")
                else:
                    bolum("Eser listesi", f"{len(liste)} eser listelendi. Atıflarını görmek istediklerinizin 'Seç' kutusunu işaretleyin.")
                    st.session_state.setdefault("tumunu_sec", False)
                    st.session_state.setdefault("secili_eserler", set())
                    tumu = st.checkbox("Tümünü seç", key="tumunu_sec")
                    kayit = st.session_state.secili_eserler
                    liste_idleri = {y["id"] for y in liste}
                    if tumu != st.session_state.get("tumu_onceki", False):
                        st.session_state.tumu_onceki = tumu
                        kayit = (kayit | liste_idleri) if tumu else (kayit - liste_idleri)
                        st.session_state.secili_eserler = kayit
                        st.session_state.tablo_surum = st.session_state.get("tablo_surum", 0) + 1

                    tablo = pd.DataFrame([
                        {"Seç": y["id"] in kayit, "Başlık": y["baslik"], "Tür": y["tur"], "Yıl": yil_int(y["yil"])}
                        for y in liste
                    ])
                    duzenlenen = guvenli_tablo(
                        st.data_editor,
                        tablo,
                        hide_index=True,
                        disabled=["Başlık", "Tür", "Yıl"],
                        height=430,
                        row_height=42,
                        key=f"eser_tablosu_{st.session_state.get('tablo_surum', 0)}_{'-'.join(secili_turler)}",
                        column_config={
                            "Seç": st.column_config.CheckboxColumn("Seç", width="small"),
                            "Başlık": st.column_config.TextColumn("Başlık", width="large"),
                            "Tür": st.column_config.TextColumn("Tür", width="small"),
                            "Yıl": st.column_config.NumberColumn("Yıl", format="%d", width="small"),
                        },
                    )
                    secili_idler = {liste[i]["id"] for i in duzenlenen.index[duzenlenen["Seç"]]}
                    st.session_state.secili_eserler = (kayit - liste_idleri) | secili_idler
                    st.markdown(f"**Seçili eser:** {len(secili_idler)} / {len(liste)}")

                    bolum("Atıf yılı aralığı", "Atıf yapan eserlerin yayın yılı. Varsayılan yıllar seçtiğiniz eserlere göre gelir, istediğiniz yılı yazabilirsiniz.")
                    adaylar_atif = [a for a in atiflar if a["atif_alan_yayin_id"] in secili_idler]
                    ymin, ymax = yil_araligi(adaylar_atif) if adaylar_atif else (None, None)
                    if not secili_idler:
                        st.caption("Önce yukarıdaki tablodan en az bir eser işaretleyin.")
                    elif not adaylar_atif:
                        st.caption("Seçilen eserlere yapılmış atıf yok.")
                    elif ymin is None:
                        st.caption("Atıfların yılı bilinmiyor; yıl filtresi uygulanmayacak.")

                    y1, y2, y3 = st.columns([2, 2, 3], vertical_alignment="bottom")
                    if ymin is None:
                        y1.number_input("Başlangıç yılı", value=None, placeholder="—", disabled=True, key="ybas_bos")
                        y2.number_input("Bitiş yılı", value=None, placeholder="—", disabled=True, key="ybit_bos")
                    else:
                        st.session_state.setdefault(f"ybas_{ymin}_{ymax}", ymin)
                        st.session_state.setdefault(f"ybit_{ymin}_{ymax}", ymax)
                        bas_yil = y1.number_input(
                            "Başlangıç yılı", min_value=1950, max_value=date.today().year,
                            step=1, format="%d", key=f"ybas_{ymin}_{ymax}",
                        )
                        bit_yil = y2.number_input(
                            "Bitiş yılı", min_value=1950, max_value=date.today().year,
                            step=1, format="%d", key=f"ybit_{ymin}_{ymax}",
                        )
                        if bit_yil < bas_yil:
                            st.warning("Bitiş yılı, başlangıç yılından küçük olamaz.")
                    st.session_state.setdefault("oz_gizle", False)
                    oz_gizle = y3.checkbox("Öz-atıfları gizle", help="Hocanın kendi eserine yaptığı atıflar", key="oz_gizle")

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
                    ("Doğrulandı", sum(a["durum"] == "Doğrulandı" for a in gosterilen), "Kaynakça kanıtıyla kontrol edildi", "yesil"),
                    ("İncelenmeli", sum(a["durum"] == "İncelenmeli" for a in gosterilen), "Yalnızca OpenAlex ilişkisi var", "sari"),
                ])

                if gosterilen:
                    bolum("Yıllara göre dağılım", "Atıf yapan eserlerin yayın yılına göre atıf sayısı.")
                    st.markdown(yil_dagilimi_html(gosterilen), unsafe_allow_html=True)

                bolum("Atıf tablosu", "Satırlar sarılır, yazılar kesilmez. DOI ve Kanıt sütunlarındaki bağlantılar yeni sekmede açılır.")
                if not gosterilen:
                    st.info(f"Seçtiğiniz yıl aralığında ({yil_metni}) atıf yok. Yıl aralığını değiştirip tekrar deneyin ya da başka eser seçin." if arama["bit"] != 9999 else "Bu seçimde atıf yok. Başka eser seçin.")
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

TIK_HTML = '<span class="tik">✔</span> '
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

    # ---------- Girdiler: üç sütun, yan yana ----------
    with st.container(key="kart_pdf1"):
        cA, cB, cC = st.columns([4, 3, 4], gap="large")

        with cA:
            bolum("A. Hedef eser", "Hocanın hangi yayınına atıf arandığını seçin.")
            indeks = next(
                (i for i, y in enumerate(yayinlar)
                 if "KURUMSAL KAYNAK PLANLAMASI" in y["baslik"].upper() and "VIKOR" in y["baslik"].upper()), 0)
            st.session_state.setdefault("hedef_secim", indeks)
            sec = st.selectbox(
                "Hedef eser", options=list(range(len(yayinlar))), key="hedef_secim",
                format_func=lambda i: f"{yayinlar[i]['baslik'][:70]} ({yil_int(yayinlar[i]['yil']) or '?'})",
                label_visibility="collapsed",
            )
            hedef_y = yayinlar[sec]
            st.markdown(
                f'<div class="bilgi"><b>Seçilen eser:</b> {e(hedef_y["baslik"])} ({e(yil_int(hedef_y["yil"]) or "yıl bilinmiyor")})</div>',
                unsafe_allow_html=True,
            )

        with cB:
            bolum("B. Yazarlar", "Metin içi atıf araması için tam 2 yazar gerekir.")
            st.session_state.setdefault(f"yazar_{sec}", ", ".join(hedef_y["yazarlar"]))
            yazar_metni = st.text_input(
                "Yazarlar (virgülle ayırın)", key=f"yazar_{sec}", label_visibility="collapsed",
            )
            yazarlar = [a.strip() for a in yazar_metni.split(",") if a.strip()]
            if len(yazarlar) != 2:
                st.info("Bu eserde 2 yazar yok. Kaynakça eşleşmesi yapılır, metin içi atıf araması yapılamaz.")

        with cC:
            bolum("C. PDF dosyası", "Metni seçilebilen (taranmamış) bir PDF olmalı.")
            yuklenen = st.file_uploader("PDF dosyası", type=["pdf"], label_visibility="collapsed")
            dosya = st.session_state.get("pdf_dosya")
            if yuklenen is not None and (dosya is None or dosya["ad"] != yuklenen.name or dosya["boyut"] != yuklenen.size):
                dosya = {"ad": yuklenen.name, "boyut": yuklenen.size, "bayt": yuklenen.getvalue()}
                st.session_state.pdf_dosya = dosya
            if dosya is not None:
                st.markdown(
                    f'<div class="bilgi"><b>Yüklenen dosya:</b> {e(dosya["ad"])} ({dosya["boyut"] / 1_000_000:.1f} MB)</div>',
                    unsafe_allow_html=True,
                )

        st.write("")
        calistir = st.button("PDF'i analiz et", type="primary", width="stretch", disabled=dosya is None)

        if calistir and dosya is not None:
            hedef = hedef_eser_hazirla(hedef_y["baslik"], yazarlar, yil_int(hedef_y["yil"]), hedef_y["doi"])
            try:
                with st.spinner("PDF okunuyor, büyük tezlerde bir iki dakika sürebilir..."):
                    st.session_state.pdf_rapor = pdf_kontrol_et(dosya["bayt"], hedef)
                    st.session_state.pdf_ad = dosya["ad"]
            except ModuleNotFoundError:
                st.session_state.pdf_rapor = None
                st.error("PDF okuyucu kurulu değil. Terminalde şunu çalıştırın: python -m pip install pymupdf")
            except Exception as hata:
                st.session_state.pdf_rapor = None
                st.error(f"PDF işlenemedi: {hata}")

    st.write("")

    # ---------- Sonuçlar: kartlar ızgarada ----------
    rapor = st.session_state.get("pdf_rapor")

    if not rapor:
        with st.container(key="kart_pdf_bos"):
            baslik(3, "Sonuç ve kanıt", "Analiz bittiğinde sonuçlar kartlar halinde burada görünür.")
            adimlar([
                "Yukarıdan <b>hedef eseri</b> seçin ve yazarları kontrol edin.",
                "<b>PDF dosyasını</b> yükleyin.",
                "<b>PDF'i analiz et</b> düğmesine basın.",
            ])
            st.markdown(
                '<div class="bilgi"><b>Sonuç şu kartlardan oluşur:</b> Sonuç, Özet (kaynakçada ve metin içinde bulundu mu), '
                "Metin içi atıf, Kaynakça kaydı ve Ayrıntılı rapor.</div>",
                unsafe_allow_html=True,
            )
    else:
        tur, ana, aciklama = ozet(rapor)
        st.markdown(f'<div class="bilgi"><b>İncelenen belge:</b> {e(st.session_state.get("pdf_ad", ""))}</div>', unsafe_allow_html=True)
        st.write("")

        r1, r2 = st.columns([5, 6], gap="large")
        with r1:
            with st.container(key="sonuc_kutu"):
                bolum("Sonuç", "Belgede neyin bulunduğu, sırayla.")
                if tur == "hata":
                    st.markdown(f'<div class="karar {KARAR_SINIFI[tur]}"><b>{e(ana)}</b><span>{e(aciklama)}</span></div>', unsafe_allow_html=True)
                else:
                    simgeler = {
                        "var": '<span class="tik">✔</span>', "olasi": '<span class="tik sari">●</span>',
                        "yok": '<span class="tik kirmizi">✖</span>', "bilgi": "•",
                    }
                    st.markdown(
                        '<div class="karar k-mavi" style="padding:14px 22px">'
                        + "".join(
                            f'<div style="font-size:1.05rem;line-height:1.7"><b style="display:inline;font-size:1.05rem">{simgeler[ik]} {e(et)}:</b> {e(me)}</div>'
                            for ik, et, me in sonuc_satirlari(rapor)
                        ) + '</div>',
                        unsafe_allow_html=True,
                    )

        with r2:
            with st.container(key="ozet_kutu"):
                bolum("Özet", "Hedef eser belgenin neresinde bulundu?")
                kay = KAYNAKCA_METNI.get(rapor["hedef_eser_kimligi_sonucu"]["durum"], ("Belirsiz", "Kaynakça güvenilir biçimde okunamadı."))
                met = METIN_ICI_METNI.get(rapor["hedef_metin_ici_atif_sonucu"]["durum"], ("Belirsiz", "Metin içi atıf araması yapılamadı (örneğin hedefin 2 yazarı yoktur)."))

                def _tikli(d):
                    return f"✔ {d}" if d == "Var" else d

                stat_kutulari([
                    ("Kaynakçada", _tikli(kay[0]), kay[1], "yesil" if kay[0] == "Var" else ""),
                    ("Metin içinde", _tikli(met[0]), met[1], "yesil" if met[0] == "Var" else ""),
                    ("Sayfa sayısı", rapor["pdf_sayfa_sayisi"] or "-", "İncelenen belgenin toplam PDF sayfası."),
                ])

        st.write("")
        r3, r4 = st.columns(2, gap="large")
        with r3:
            with st.container(key="atif_kutu"):
                bolum("Metin içi atıf", "Ana metinde hedef esere yapılan atıf. Sayfa numarası PDF sırasına göredir.")
                gorulen, atif_satirlari = set(), []
                for ad_ in rapor["hedef_metin_ici_atif_sonucu"].get("adaylar", []) + [
                        b for b in rapor["hedef_baglanti_sonucu"].get("baglantilar", [])]:
                    metin_ = ad_.get("ham_atif_metni")
                    sayfa_ = ad_.get("pdf_sayfa")
                    if metin_ and (sayfa_, metin_) not in gorulen:
                        gorulen.add((sayfa_, metin_))
                        atif_satirlari.append(f'<div class="atif-satir"><b><span class="tik">✔</span> PDF sayfa {e(sayfa_)}:</b> {e(metin_)}</div>')
                if atif_satirlari:
                    st.markdown("".join(atif_satirlari), unsafe_allow_html=True)
                else:
                    st.markdown('<div class="bilgi">Metin içinde hedef esere ait atıf bulunamadı.</div>', unsafe_allow_html=True)

        with r4:
            with st.container(key="kayit_kutu"):
                bolum("Kaynakça kaydı", "Kaynakçadaki aday kayıtlar. En güçlü eşleşme en üstte.")
                kayitlar = kaynakca_kaydi_metni(rapor)
                if kayitlar:
                    st.markdown(
                        "".join(
                            f'<div class="kayit"><div class="ust"><span>{TIK_HTML if etiket.split()[0] == "Güçlü" else ""}Kayıt {e(kid)} · PDF sayfa {e(sayfa)}</span>'
                            f'<span class="rozet {ETIKET_SINIFI.get(etiket.split()[0], "bos")}">{e(etiket.split(":")[0])}</span></div>'
                            f'<div class="metin">{e(metin)}</div>'
                            f'<div style="margin-top:6px;font-size:14px;color:#52525B">{e(etiket.split(":", 1)[1].strip() if ":" in etiket else "")}</div></div>'
                            for kid, sayfa, metin, etiket in kayitlar
                        ),
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown('<div class="bilgi">Kaynakçada hedef esere benzeyen bir kayıt bulunamadı.</div>', unsafe_allow_html=True)

        if rapor["bibliyografik_farkliliklar"]:
            st.info(f"Künye farkı: {len(rapor['bibliyografik_farkliliklar'])} noktada fark var (ayrıntılı raporda).")

        st.write("")
        with st.container(key="ayrinti_kutu"):
            bolum("Ayrıntılı rapor", "Aşamalar, boş sayfalar ve elle incelenecek noktalar. Raporlama ve hata arama için.")
            with st.expander("Ayrıntılı raporu göster"):
                st.text_area(
                    "Rapor", value=kanit_raporunu_metinlestir(rapor), height=360,
                    disabled=True, label_visibility="collapsed",
                )
            st.caption("PDF sayfa numarası, belgenin üzerindeki basılı sayfa numarasından farklı olabilir.")