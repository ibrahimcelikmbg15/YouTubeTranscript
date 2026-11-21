import io
import re
import zipfile
import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi

st.set_page_config(
    page_title="YouTube Transkript Çekici | Genom Okulu",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 YouTube Transkript Çekici")
st.caption("Genom Okulu & Gene-A(L)İ için YouTube videolarından temiz .txt transkript üretici")

def video_id_bul(url: str) -> str:
    eslesme = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([a-zA-Z0-9_-]{11})", url)
    return eslesme.group(1) if eslesme else url.strip()

def transkript_al(video_id: str, diller: list[str]) -> str:
    # Hem eski (0.6.x) hem yeni (1.x) kütüphane sürümleriyle uyumlu
    if hasattr(YouTubeTranscriptApi, "get_transcript"):
        parcalar = YouTubeTranscriptApi.get_transcript(video_id, languages=diller)
        metin = " ".join(p["text"] for p in parcalar)
    else:
        api = YouTubeTranscriptApi()
        parcalar = api.fetch(video_id, languages=diller)
        metin = " ".join(p.text for p in parcalar)
    return re.sub(r"\s+", " ", metin).strip()

# --- ARAYÜZ ---
mod = st.radio("Çalışma Modu", ["Tek Video", "Toplu Video (Çoklu Link)"], horizontal=True)
dil_secimi = st.multiselect("Öncelikli Altyazı Dilleri", ["tr", "en"], default=["tr", "en"])

if mod == "Tek Video":
    url = st.text_input("YouTube Video Linki", placeholder="https://www.youtube.com/watch?v=...")
    dosya_adi = st.text_input("Kaydedilecek Dosya Adı (.txt uzantısız)", placeholder="01_gmata_ssr_tasarimi")

    if st.button("Transkripti Çek", type="primary", use_container_width=True):
        if not url.strip():
            st.warning("Lütfen bir YouTube linki girin.")
        else:
            vid = video_id_bul(url)
            with st.spinner("Altyazı çekiliyor..."):
                try:
                    metin = transkript_al(vid, dil_secimi or ["tr", "en"])
                    ad = (dosya_adi.strip() or vid) + ".txt"
                    st.success(f"Transkript hazır! ({len(metin)} karakter)")
                    st.text_area("Önizleme", metin, height=250)
                    st.download_button(
                        label=f"📥 {ad} Olarak İndir",
                        data=metin.encode("utf-8"),
                        file_name=ad,
                        mime="text/plain",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Hata oluştu: {e}")

else:
    st.info("Her satıra bir link yazın. İsterseniz `dosya_adi | link` şeklinde isim de verebilirsiniz.")
    linkler_metni = st.text_area(
        "YouTube Linkleri",
        height=180,
        placeholder="01_gmata_ssr | https://www.youtube.com/watch?v=...\n02_fasta_analizi | https://youtu.be/..."
    )

    if st.button("Tümünü Çek ve ZIP Oluştur", type="primary", use_container_width=True):
        satirlar = [s.strip() for s in linkler_metni.splitlines() if s.strip()]
        if not satirlar:
            st.warning("Lütfen en az bir link girin.")
        else:
            zip_buffer = io.BytesIO()
            basarili = 0
            hatalar = []

            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                ilerleme = st.progress(0)
                for idx, satir in enumerate(satirlar):
                    if "|" in satir:
                        ad_kismi, url_kismi = [x.strip() for x in satir.split("|", 1)]
                    else:
                        ad_kismi, url_kismi = "", satir

                    vid = video_id_bul(url_kismi)
                    dosya_adi = (ad_kismi or f"{idx+1:02d}_{vid}") + ".txt"

                    try:
                        metin = transkript_al(vid, dil_secimi or ["tr", "en"])
                        zf.writestr(dosya_adi, metin.encode("utf-8"))
                        basarili += 1
                    except Exception as e:
                        hatalar.append(f"**{dosya_adi}**: {e}")

                    ilerleme.progress((idx + 1) / len(satirlar))

            if basarili > 0:
                st.success(f"{basarili} / {len(satirlar)} video başarıyla çekildi!")
                st.download_button(
                    label="📦 Tüm Transkriptleri ZIP Olarak İndir",
                    data=zip_buffer.getvalue(),
                    file_name="genom_okulu_transkriptler.zip",
                    mime="application/zip",
                    use_container_width=True
                )

            if hatalar:
                st.warning("Bazı videolar çekilemedi:")
                for h in hatalar:
                    st.markdown(f"- {h}")